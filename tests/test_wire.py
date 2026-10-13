"""Replays the Go client's recorded requests through nomadpy and asserts the wire form matches.

oracle/fixtures/wire.json holds one request per op, as the Go client sent it
against a recorder with the same config this test uses. Each op here makes
the same call with the same arguments. Query strings, paths and headers must
match exactly. Bodies match after the zero-value rule: Go serialises every
struct field, so a key Go sent with a zero value (null, "", 0, false, empty
list or object) may be absent from the Python body, but anything Python
sends must exist in the Go body with the same value. Go's zero time.Time
serialises as "0001-01-01T00:00:00Z" and counts as a zero value.
"""

import json
from datetime import timedelta
from pathlib import Path

import pytest

from nomadpy import (
    ACLAuthMethod,
    ACLAuthMethodConfig,
    ACLBindingRule,
    ACLPolicy,
    ACLRole,
    ACLRolePolicyLink,
    ACLToken,
    ACLTokenRoleLink,
    Client,
    Config,
    JobACL,
    Namespace,
    NamespaceCapabilities,
    NamespaceConsulConfiguration,
    NamespaceNodePoolConfiguration,
    NamespaceVaultConfiguration,
    OIDCClientAssertion,
    OIDCClientAssertionKey,
    QueryOptions,
    WriteOptions,
)

MILLISECOND = 1_000_000
SECOND = 1_000 * MILLISECOND
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
GO_ZERO_TIME = "0001-01-01T00:00:00Z"

WIRE = json.loads((Path(__file__).resolve().parent.parent / "oracle/fixtures/wire.json").read_text())

QUERY_OPTS = QueryOptions(region="r1", namespace="ns1", allow_stale=True, wait_index=12, wait_time=timedelta(milliseconds=1500),
                          prefix="p", filter="f == 1", per_page=5, next_token="nt", reverse=True,
                          params={"x": "y"}, headers={"H": "v"}, auth_token="tok1")
WRITE_OPTS = WriteOptions(region="r1", namespace="ns1", auth_token="tok1", idempotency_token="idem", headers={"H": "v"})
JOB = {"ID": "j1", "Name": "j1"}

OPS = {
    "status.leader": lambda c: c.status.leader(),
    "status.region_leader": lambda c: c.status.region_leader("eu"),
    "status.peers": lambda c: c.status.peers(),
    "regions.list": lambda c: c.regions.list(),

    "jobs.parse_hcl": lambda c: c.jobs.parse_hcl("job {}", canonicalize=True, variables="n = 3"),
    "jobs.validate": lambda c: c.jobs.validate(JOB, WRITE_OPTS),
    "jobs.register": lambda c: c.jobs.register(JOB),
    "jobs.register_opts": lambda c: c.jobs.register(
        JOB, WRITE_OPTS, enforce_index=True, modify_index=7, policy_override=True, preserve_counts=True,
        preserve_resources=True, eval_priority=50, submission={"Source": "job {}", "Format": "hcl2"}),
    "jobs.list": lambda c: c.jobs.list(),
    "jobs.list_query_opts": lambda c: c.jobs.list(QUERY_OPTS),
    "jobs.list_meta": lambda c: c.jobs.list(meta=True),
    "jobs.prefix_list": lambda c: c.jobs.prefix_list("pre"),
    "jobs.info": lambda c: c.jobs.info("j 1/x"),
    "jobs.scale": lambda c: c.jobs.scale("j1", "g", 2, "msg", True, {"k": "v"}, WRITE_OPTS),
    "jobs.scale_status": lambda c: c.jobs.scale_status("j1"),
    "jobs.versions": lambda c: c.jobs.versions("j1", diffs=True),
    "jobs.versions_opts": lambda c: c.jobs.versions("j1", diffs=False, diff_tag="t", diff_version=3),
    "jobs.submission": lambda c: c.jobs.submission("j1", 2),
    "jobs.allocations": lambda c: c.jobs.allocations("j1", all_allocs=True),
    "jobs.deployments": lambda c: c.jobs.deployments("j1", all=True),
    "jobs.latest_deployment": lambda c: c.jobs.latest_deployment("j1"),
    "jobs.evaluations": lambda c: c.jobs.evaluations("j1"),
    "jobs.deregister": lambda c: c.jobs.deregister("j1", purge=True, w=WRITE_OPTS, global_=True, eval_priority=9, no_shutdown_delay=True),
    "jobs.force_evaluate": lambda c: c.jobs.force_evaluate("j1", force_reschedule=True),
    "jobs.periodic_force": lambda c: c.jobs.periodic_force("j1"),
    "jobs.plan": lambda c: c.jobs.plan(JOB, diff=True, policy_override=True),
    "jobs.summary": lambda c: c.jobs.summary("j1"),
    "jobs.dispatch": lambda c: c.jobs.dispatch("j1", {"k": "v"}, b"\x00hello", "pfx", priority=3),
    "jobs.revert": lambda c: c.jobs.revert("j1", 4, 5),
    "jobs.stable": lambda c: c.jobs.stable("j1", 4, True),
    "jobs.services": lambda c: c.jobs.services("j1"),
    "jobs.tag_version": lambda c: c.jobs.tag_version("j1", "golden", 4, "d", latest=True),
    "jobs.untag_version": lambda c: c.jobs.untag_version("j1", "golden"),

    "acl_policies.list": lambda c: c.acl_policies.list(),
    "acl_policies.upsert": lambda c: c.acl_policies.upsert(ACLPolicy(
        name="p1", description="d", rules='namespace "default" { policy = "read" }', job_acl=JobACL(namespace="ns", job_id="j")), WRITE_OPTS),
    "acl_policies.delete": lambda c: c.acl_policies.delete("p1"),
    "acl_policies.info": lambda c: c.acl_policies.info("p1"),
    "acl_policies.self": lambda c: c.acl_policies.self(),
    "acl_tokens.bootstrap": lambda c: c.acl_tokens.bootstrap(),
    "acl_tokens.bootstrap_opts": lambda c: c.acl_tokens.bootstrap(WRITE_OPTS, bootstrap_secret="secret"),
    "acl_tokens.list": lambda c: c.acl_tokens.list(),
    "acl_tokens.create": lambda c: c.acl_tokens.create(ACLToken(
        name="t", type="client", policies=["p1"], roles=[ACLTokenRoleLink(id="r1")], global_=True, expiration_ttl=90 * MINUTE)),
    "acl_tokens.upload": lambda c: c.acl_tokens.upload(ACLToken(accessor_id="acc", secret_id="sec", name="t", type="client", policies=["p1"])),
    "acl_tokens.update": lambda c: c.acl_tokens.update(ACLToken(accessor_id="acc", name="t2")),
    "acl_tokens.delete": lambda c: c.acl_tokens.delete("acc"),
    "acl_tokens.info": lambda c: c.acl_tokens.info("acc"),
    "acl_tokens.self": lambda c: c.acl_tokens.self(),
    "acl_tokens.upsert_one_time_token": lambda c: c.acl_tokens.upsert_one_time_token(),
    "acl_tokens.exchange_one_time_token": lambda c: c.acl_tokens.exchange_one_time_token("ott"),
    "acl_roles.list": lambda c: c.acl_roles.list(),
    "acl_roles.create": lambda c: c.acl_roles.create(ACLRole(name="r", description="d", policies=[ACLRolePolicyLink(name="p1")])),
    "acl_roles.update": lambda c: c.acl_roles.update(ACLRole(id="rid", name="r2")),
    "acl_roles.delete": lambda c: c.acl_roles.delete("rid"),
    "acl_roles.get": lambda c: c.acl_roles.get("rid"),
    "acl_roles.get_by_name": lambda c: c.acl_roles.get_by_name("r"),
    "acl_auth_methods.list": lambda c: c.acl_auth_methods.list(),
    "acl_auth_methods.create": lambda c: c.acl_auth_methods.create(ACLAuthMethod(
        name="m", type="JWT", token_locality="global", token_name_format="${auth_method_type}-${value.sub}", max_token_ttl=HOUR, default=True,
        config=ACLAuthMethodConfig(
            jwks_url="https://idp.example/jwks", bound_audiences=["nomad"], claim_mappings={"sub": "user"},
            expiration_leeway=90 * SECOND, clock_skew_leeway=1500 * MILLISECOND,
            oidc_client_assertion=OIDCClientAssertion(audience=["a"], key_source="nomad", private_key=OIDCClientAssertionKey(key_id_header="kid", key_id="k"))))),
    "acl_auth_methods.update": lambda c: c.acl_auth_methods.update(ACLAuthMethod(name="m", type="JWT")),
    "acl_auth_methods.delete": lambda c: c.acl_auth_methods.delete("m"),
    "acl_auth_methods.get": lambda c: c.acl_auth_methods.get("m"),
    "acl_binding_rules.list": lambda c: c.acl_binding_rules.list(),
    "acl_binding_rules.create": lambda c: c.acl_binding_rules.create(ACLBindingRule(
        description="d", auth_method="m", selector='value.user == "a"', bind_type="policy", bind_name="p1")),
    "acl_binding_rules.update": lambda c: c.acl_binding_rules.update(ACLBindingRule(id="bid", auth_method="m", bind_type="role", bind_name="r")),
    "acl_binding_rules.delete": lambda c: c.acl_binding_rules.delete("bid"),
    "acl_binding_rules.get": lambda c: c.acl_binding_rules.get("bid"),
    "acl_auth.get_auth_url": lambda c: c.acl_auth.get_auth_url("m", "http://127.0.0.1/cb", "n"),
    "acl_auth.complete_auth": lambda c: c.acl_auth.complete_auth("m", "n", "s", "c", "i", "http://127.0.0.1/cb"),
    "acl_auth.login": lambda c: c.acl_auth.login("m", "jwt"),
    "acl_identity.create_client_introduction_token": lambda c: c.acl_identity.create_client_introduction_token(5 * MINUTE, "n", "p", WRITE_OPTS),

    "namespaces.list": lambda c: c.namespaces.list(),
    "namespaces.prefix_list": lambda c: c.namespaces.prefix_list("pre", QueryOptions(**QUERY_OPTS.__dict__)),
    "namespaces.info": lambda c: c.namespaces.info("n1"),
    "namespaces.register": lambda c: c.namespaces.register(Namespace(
        name="n1", description="d", quota="q", meta={"k": "v"},
        capabilities=NamespaceCapabilities(enabled_task_drivers=["raw_exec"], disabled_network_modes=["host"]),
        node_pool_configuration=NamespaceNodePoolConfiguration(default="p", allowed=["a"], denied=["b"]),
        vault_configuration=NamespaceVaultConfiguration(default="v"),
        consul_configuration=NamespaceConsulConfiguration(default="c"),
        required_extra_claims={"r": "1"}, optional_extra_claims={"o": "2"}), WRITE_OPTS),
    "namespaces.delete": lambda c: c.namespaces.delete("n1", WRITE_OPTS),

    "evaluations.list": lambda c: c.evaluations.list(),
    "evaluations.prefix_list": lambda c: c.evaluations.prefix_list("pre"),
    "evaluations.count": lambda c: c.evaluations.count(),
    "evaluations.info": lambda c: c.evaluations.info("e1"),
    "evaluations.delete": lambda c: c.evaluations.delete(["e1", "e2"], WRITE_OPTS, filter="f"),
    "evaluations.allocations": lambda c: c.evaluations.allocations("e1"),

    "deployments.list": lambda c: c.deployments.list(),
    "deployments.prefix_list": lambda c: c.deployments.prefix_list("pre"),
    "deployments.info": lambda c: c.deployments.info("d1"),
    "deployments.allocations": lambda c: c.deployments.allocations("d1"),
    "deployments.fail": lambda c: c.deployments.fail("d1"),
    "deployments.pause": lambda c: c.deployments.pause("d1", True),
    "deployments.promote_all": lambda c: c.deployments.promote_all("d1"),
    "deployments.promote_groups": lambda c: c.deployments.promote_groups("d1", ["g1", "g2"]),
    "deployments.unblock": lambda c: c.deployments.unblock("d1"),
    "deployments.set_alloc_health": lambda c: c.deployments.set_alloc_health("d1", ["a1"], ["a2"], WRITE_OPTS),
}

# The recorder answers what Go's did, except where the Python method flattens a response field.
RESPONSES = {
    "acl_tokens.upsert_one_time_token": {"OneTimeToken": {}},
    "acl_tokens.exchange_one_time_token": {"Token": {}},
    "evaluations.count": {"Count": 0},
    "evaluations.delete": {"Count": 0},
    "jobs.deregister": {"EvalID": ""},
    "jobs.force_evaluate": {"EvalID": ""},
    "jobs.periodic_force": {"EvalID": ""},
    "jobs.versions": {"Versions": []},
    "jobs.versions_opts": {"Versions": []},
}


def is_zero(value) -> bool:
    return value is None or value in ("", GO_ZERO_TIME, 0, False, [], {})


def body_problems(go, py, path="body"):
    if isinstance(go, dict) and isinstance(py, dict):
        problems = []
        for key, value in go.items():
            if key in py:
                problems += body_problems(value, py[key], f"{path}.{key}")
            elif not is_zero(value):
                problems.append(f"{path}.{key}: Go sent {value!r}, Python omitted it")
        for key in py.keys() - go.keys():
            problems.append(f"{path}.{key}: Python sent {py[key]!r}, Go has no such key")
        return problems
    if go != py:
        return [f"{path}: Go sent {go!r}, Python sent {py!r}"]
    return []


def test_every_recorded_op_is_replayed():
    assert {r["op"] for r in WIRE["requests"]} == set(OPS)


@pytest.mark.parametrize("expected", WIRE["requests"], ids=lambda r: r["op"])
def test_wire(recorder, expected):
    recorder.response = RESPONSES.get(expected["op"], json.loads(expected["response"]))
    client = Client(Config(address=recorder.address, region="r0", namespace="ns0", secret_id="tok0", headers={"X-Custom": "1"}))
    OPS[expected["op"]](client)
    got = recorder.last
    assert got["method"] == expected["method"]
    assert got["path"] == expected["path"]
    assert got["query"] == expected["query"]
    headers = {k: v for k, v in got["headers"].items() if k.startswith("X-") or k == "Authorization"}
    assert headers == expected["headers"]
    if expected["body"] is None:
        assert got["body"] is None
    else:
        problems = body_problems(expected["body"], got["body"])
        assert not problems, "\n".join(problems)
