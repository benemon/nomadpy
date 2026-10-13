"""Quota and Sentinel tests: the Community lane asserts the server's refusal, the Enterprise lane exercises the surface."""

import pytest

from nomadpy import (
    Namespace,
    QuotaLimit,
    QuotaResources,
    QuotaSpec,
    QuotaStorageResources,
    SentinelPolicy,
    UnexpectedResponseError,
)
from nomadpy.sentinel import SENTINEL_SCOPE_SUBMIT_JOB

ENT_ONLY = "Nomad Enterprise only endpoint"


def _require_governance(client):
    lic, _ = client.query("/v1/operator/license")
    modules = lic["License"]["Modules"] or []
    if not any("governance" in m for m in modules):
        pytest.skip(f"licence modules {modules} lack governance-policy")
    return client


@pytest.fixture
def governance_client(ent_client):
    """The Enterprise client, when its licence carries the Governance & Policy module."""
    return _require_governance(ent_client)


@pytest.fixture
def governance_acl_client(ent_acl_client):
    """The management-token Enterprise client, for Sentinel, which needs ACLs enabled."""
    return _require_governance(ent_acl_client)


def test_quotas_on_community(client):
    for call in (lambda: client.quotas.list(), lambda: client.quotas.info("x"), lambda: client.quotas.list_usage(),
                 lambda: client.quotas.register(QuotaSpec(name="x")), lambda: client.quotas.delete("x")):
        with pytest.raises(UnexpectedResponseError) as e:
            call()
        assert e.value.status_code == 501 and e.value.body == ENT_ONLY


def test_sentinel_on_community(client):
    for call in (lambda: client.sentinel_policies.list(), lambda: client.sentinel_policies.info("x"),
                 lambda: client.sentinel_policies.upsert(SentinelPolicy(name="x", policy="main = rule { true }")),
                 lambda: client.sentinel_policies.delete("x")):
        with pytest.raises(UnexpectedResponseError) as e:
            call()
        assert e.value.status_code == 501 and e.value.body == ENT_ONLY
    with pytest.raises(ValueError):
        client.sentinel_policies.upsert(SentinelPolicy(policy="main = rule { true }"))


def test_quotas(governance_client):
    c = governance_client
    spec = QuotaSpec(name="nomadpy-quota", description="d", limits=[QuotaLimit(
        region="global",
        region_limit=QuotaResources(cpu=1000, memory_mb=1024, storage=QuotaStorageResources(variables_mb=10, host_volumes_mb=20)))])
    wm = c.quotas.register(spec)
    assert wm.last_index > 0
    try:
        got, qm = c.quotas.info("nomadpy-quota")
        assert got.description == "d" and got.limits[0].region == "global"
        assert got.limits[0].region_limit.cpu == 1000 and got.limits[0].region_limit.memory_mb == 1024
        assert got.limits[0].region_limit.storage.variables_mb == 10
        assert got.limits[0].region_limit.storage.host_volumes_mb == 20
        assert got.limits[0].variables_limit == 0 and got.limits[0].hash
        specs, _ = c.quotas.list()
        assert "nomadpy-quota" in [s.name for s in specs]
        by_prefix, _ = c.quotas.prefix_list("nomadpy-q")
        assert [s.name for s in by_prefix] == ["nomadpy-quota"]

        c.namespaces.register(Namespace(name="nomadpy-quota-ns", quota="nomadpy-quota"))
        try:
            ns, _ = c.namespaces.info("nomadpy-quota-ns")
            assert ns.quota == "nomadpy-quota"
            usage, _ = c.quotas.usage("nomadpy-quota")
            # Usage is keyed by the limit's hash, not its region.
            assert usage.name == "nomadpy-quota" and [u.region for u in usage.used.values()] == ["global"]
            usages, _ = c.quotas.list_usage()
            assert "nomadpy-quota" in [u.name for u in usages]
            by_prefix, _ = c.quotas.prefix_list_usage("nomadpy-q")
            assert [u.name for u in by_prefix] == ["nomadpy-quota"]
            # Neither a namespace with a quota nor a referenced quota can be deleted.
            with pytest.raises(UnexpectedResponseError):
                c.quotas.delete("nomadpy-quota")
        finally:
            c.namespaces.register(Namespace(name="nomadpy-quota-ns"))
            c.namespaces.delete("nomadpy-quota-ns")
    finally:
        c.quotas.delete("nomadpy-quota")
    with pytest.raises(UnexpectedResponseError) as e:
        c.quotas.info("nomadpy-quota")
    assert e.value.status_code == 404


def test_sentinel_policies(governance_acl_client):
    c = governance_acl_client
    policy = SentinelPolicy(name="nomadpy-sentinel", description="d", scope=SENTINEL_SCOPE_SUBMIT_JOB,
                            enforcement_level="advisory", policy="main = rule { true }")
    wm = c.sentinel_policies.upsert(policy)
    assert wm.last_index > 0
    try:
        got, _ = c.sentinel_policies.info("nomadpy-sentinel")
        assert got.policy == "main = rule { true }" and got.enforcement_level == "advisory"
        stubs, _ = c.sentinel_policies.list()
        assert [s.scope for s in stubs if s.name == "nomadpy-sentinel"] == [SENTINEL_SCOPE_SUBMIT_JOB]
    finally:
        c.sentinel_policies.delete("nomadpy-sentinel")
    with pytest.raises(UnexpectedResponseError) as e:
        c.sentinel_policies.info("nomadpy-sentinel")
    assert e.value.status_code == 404
