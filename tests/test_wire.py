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
import urllib.parse
from datetime import timedelta
from pathlib import Path

import pytest

from nomadpy.models import GO_ZERO_TIME
from nomadpy import (
    ACLAuthMethod,
    ACLAuthMethodConfig,
    ACLBindingRule,
    ACLPolicy,
    ACLRole,
    ACLRolePolicyLink,
    ACLToken,
    ACLTokenRoleLink,
    AutopilotConfiguration,
    Client,
    CSISnapshot,
    CSIVolume,
    CSIVolumeCapability,
    Config,
    DrainSpec,
    HostVolume,
    HostVolumeCapability,
    Job,
    JobACL,
    Namespace,
    NamespaceCapabilities,
    NamespaceConsulConfiguration,
    NamespaceNodePoolConfiguration,
    NamespaceVaultConfiguration,
    NodePool,
    NodePoolLimit,
    NodePoolSchedulerConfiguration,
    OIDCClientAssertion,
    OIDCClientAssertionKey,
    PreemptionConfig,
    QueryOptions,
    QuotaLimit,
    QuotaResources,
    QuotaSpec,
    QuotaStorageResources,
    Recommendation,
    ScalingRequest,
    SchedulerConfiguration,
    SchedulerWorkerPoolArgs,
    SentinelPolicy,
    Variable,
    VariableLock,
    WriteOptions,
)

MILLISECOND = 1_000_000
SECOND = 1_000 * MILLISECOND
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
# Every credential the op table sends; none may appear in a request line.
CREDENTIALS = ("tok0", "tok1", "sec", "ott", "secret", "jwt", "02MV4UU43BK5", "csisecretvalue", "oidcstate", "oidccode", "gossipkey1")

WIRE = json.loads((Path(__file__).resolve().parent.parent / "oracle/fixtures/wire.json").read_text())

QUERY_OPTS = QueryOptions(region="r1", namespace="ns1", allow_stale=True, wait_index=12, wait_time=timedelta(milliseconds=1500),
                          prefix="p", filter="f == 1", per_page=5, next_token="nt", reverse=True,
                          params={"x": "y"}, headers={"H": "v"}, auth_token="tok1")
WRITE_OPTS = WriteOptions(region="r1", namespace="ns1", auth_token="tok1", idempotency_token="idem", headers={"H": "v"})
JOB = Job(id="j1", name="j1")


def qopts():
    """A fresh copy, as the Go op table makes: methods that add headers or a prefix must not leak into later ops."""
    return QueryOptions(**{**QUERY_OPTS.__dict__, "params": dict(QUERY_OPTS.params), "headers": dict(QUERY_OPTS.headers)})

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
    "acl_auth.complete_auth": lambda c: c.acl_auth.complete_auth("m", "n", "oidcstate", "oidccode", "i", "http://127.0.0.1/cb"),
    "acl_auth.login": lambda c: c.acl_auth.login("m", "jwt"),
    "acl_identity.create_client_introduction_token": lambda c: c.acl_identity.create_client_introduction_token(5 * MINUTE, "n", "p", WRITE_OPTS),

    "allocations.list": lambda c: c.allocations.list(),
    "allocations.prefix_list": lambda c: c.allocations.prefix_list("pre"),
    "allocations.info": lambda c: c.allocations.info("a1"),
    "allocations.stats": lambda c: c.allocations.stats("a1", qopts()),
    "allocations.checks": lambda c: c.allocations.checks("a1"),
    "allocations.gc": lambda c: c.allocations.gc("a1", qopts()),
    "allocations.restart": lambda c: c.allocations.restart("a1", "t"),
    "allocations.restart_all_tasks": lambda c: c.allocations.restart_all_tasks("a1"),
    "allocations.stop": lambda c: c.allocations.stop("a1", qopts()),
    "allocations.signal": lambda c: c.allocations.signal("a1", "t", "SIGHUP"),
    "allocations.set_pause_state": lambda c: c.allocations.set_pause_state("a1", "t", "pause"),
    "allocations.get_pause_state": lambda c: c.allocations.get_pause_state("a1", "t"),
    "allocations.services": lambda c: c.allocations.services("a1"),

    "node_pools.list": lambda c: c.node_pools.list(),
    "node_pools.prefix_list": lambda c: c.node_pools.prefix_list("pre", qopts()),
    "node_pools.info": lambda c: c.node_pools.info("p 1"),
    "node_pools.register": lambda c: c.node_pools.register(NodePool(
        name="p1", description="d", meta={"k": "v"}, node_identity_ttl=HOUR,
        scheduler_configuration=NodePoolSchedulerConfiguration(scheduler_algorithm="spread", memory_oversubscription_enabled=True)), WRITE_OPTS),
    "node_pools.register_minimal": lambda c: c.node_pools.register(NodePool(name="p2")),
    "node_pools.delete": lambda c: c.node_pools.delete("p1", WRITE_OPTS),
    "node_pools.list_jobs": lambda c: c.node_pools.list_jobs("p1"),
    "node_pools.list_nodes": lambda c: c.node_pools.list_nodes("p1", qopts()),

    "nodes.list": lambda c: c.nodes.list(),
    "nodes.prefix_list": lambda c: c.nodes.prefix_list("pre", qopts()),
    "nodes.info": lambda c: c.nodes.info("n1"),
    "nodes.update_drain": lambda c: c.nodes.update_drain("n1", DrainSpec(deadline=HOUR, ignore_system_jobs=True), True, WRITE_OPTS, meta={"k": "v"}),
    "nodes.update_drain_stop": lambda c: c.nodes.update_drain("n1", None, True),
    "nodes.toggle_eligibility": lambda c: c.nodes.toggle_eligibility("n1", False),
    "nodes.allocations": lambda c: c.nodes.allocations("n1"),
    "nodes.csi_volumes": lambda c: c.nodes.csi_volumes("n1"),
    "nodes.force_evaluate": lambda c: c.nodes.force_evaluate("n1"),
    "nodes.stats": lambda c: c.nodes.stats("n1"),
    "nodes.gc": lambda c: c.nodes.gc("n1"),
    "nodes.gc_alloc": lambda c: c.nodes.gc_alloc("a1"),
    "nodes.purge": lambda c: c.nodes.purge("n1"),
    "node_meta.apply": lambda c: c.nodes.meta.apply("n1", {"k": "v", "gone": None}),
    "node_meta.read": lambda c: c.nodes.meta.read("n1"),
    "node_identity.get": lambda c: c.nodes.identity.get("n1"),
    "node_identity.renew": lambda c: c.nodes.identity.renew("n1"),

    "variables.create": lambda c: c.variables.create(Variable(path="/nomadpy/v1/", namespace="ns1", items={"k": "v"}), WRITE_OPTS),
    "variables.checked_create": lambda c: c.variables.checked_create(Variable(path="nomadpy/v1", items={"k": "v"})),
    "variables.read": lambda c: c.variables.read(" nomadpy/v1 ", qopts()),
    "variables.peek": lambda c: c.variables.peek("nomadpy/v1"),
    "variables.update": lambda c: c.variables.update(Variable(path="nomadpy/v1", modify_index=9, items={"k": "v2"}, lock=VariableLock(id="lid"))),
    "variables.checked_update": lambda c: c.variables.checked_update(Variable(path="nomadpy/v1", modify_index=9, items={"k": "v2"})),
    "variables.delete": lambda c: c.variables.delete("nomadpy/v1", WRITE_OPTS),
    "variables.checked_delete": lambda c: c.variables.checked_delete("nomadpy/v1", 9),
    "variables.list": lambda c: c.variables.list(),
    "variables.prefix_list": lambda c: c.variables.prefix_list("nomadpy/"),
    "variables.get_items": lambda c: c.variables.get_items("nomadpy/v1"),
    "variables.renew_lock": lambda c: c.variables.renew_lock(Variable(path="nomadpy/v1", lock=VariableLock(id="lid"))),
    "variables.release_lock": lambda c: c.variables.release_lock(Variable(path="nomadpy/v1", lock=VariableLock(id="lid"))),
    "variables.acquire_lock": lambda c: c.variables.acquire_lock(Variable(path="nomadpy/v1", items={"k": "v"}, lock=VariableLock(ttl="15s", lock_delay="5s"))),

    "agent.self": lambda c: c.agent.self(),
    "agent.join": lambda c: c.agent.join("10.0.0.1:4648", "10.0.0.2:4648"),
    "agent.members": lambda c: c.agent.members(qopts()),
    "agent.force_leave": lambda c: c.agent.force_leave("n1", prune=True),
    "agent.servers": lambda c: c.agent.servers(),
    "agent.set_servers": lambda c: c.agent.set_servers(["10.0.0.1:4647", "10.0.0.2:4647"]),
    "agent.list_keys": lambda c: c.agent.list_keys(),
    "agent.reload": lambda c: c.agent.reload(WRITE_OPTS),
    "agent.install_key": lambda c: c.agent.install_key("gossipkey1"),
    "agent.use_key": lambda c: c.agent.use_key("gossipkey1"),
    "agent.remove_key": lambda c: c.agent.remove_key("gossipkey1"),
    "agent.health": lambda c: c.agent.health(),
    "agent.host": lambda c: c.agent.host("s1", "n1"),
    "agent.get_scheduler_worker_config": lambda c: c.agent.get_scheduler_worker_config(),
    "agent.set_scheduler_worker_config": lambda c: c.agent.set_scheduler_worker_config(SchedulerWorkerPoolArgs(2, ["service", "batch"]), WRITE_OPTS),
    "agent.get_scheduler_workers_info": lambda c: c.agent.get_scheduler_workers_info(),
    "operator.raft_get_configuration": lambda c: c.operator.raft_get_configuration(qopts()),
    "operator.raft_remove_peer_by_address": lambda c: c.operator.raft_remove_peer_by_address("10.0.0.1:4647", WRITE_OPTS),
    "operator.raft_remove_peer_by_id": lambda c: c.operator.raft_remove_peer_by_id("id1"),
    "operator.raft_transfer_leadership_by_address": lambda c: c.operator.raft_transfer_leadership_by_address("10.0.0.1:4647"),
    "operator.raft_transfer_leadership_by_id": lambda c: c.operator.raft_transfer_leadership_by_id("id1", WRITE_OPTS),
    "operator.scheduler_get_configuration": lambda c: c.operator.scheduler_get_configuration(),
    "operator.scheduler_set_configuration": lambda c: c.operator.scheduler_set_configuration(SchedulerConfiguration(
        scheduler_algorithm="spread", preemption_config=PreemptionConfig(service_scheduler_enabled=True), pause_eval_broker=True, modify_index=3)),
    "operator.scheduler_cas_configuration": lambda c: c.operator.scheduler_cas_configuration(SchedulerConfiguration(scheduler_algorithm="binpack", modify_index=3), WRITE_OPTS),
    "operator.apply_license": lambda c: c.operator.apply_license("02MV4UU43BK5", WRITE_OPTS, force=True),
    "operator.license_get": lambda c: c.operator.license_get(qopts()),
    "operator.upgrade_check_vault_workload_identity": lambda c: c.operator.upgrade_check_vault_workload_identity(),
    "operator.utilization": lambda c: c.operator.utilization(WRITE_OPTS, today_only=True),
    "operator.autopilot_get_configuration": lambda c: c.operator.autopilot_get_configuration(),
    "operator.autopilot_set_configuration": lambda c: c.operator.autopilot_set_configuration(AutopilotConfiguration(
        cleanup_dead_servers=True, last_contact_threshold=200 * MILLISECOND, max_trailing_logs=250, min_quorum=3,
        server_stabilization_time=10 * SECOND, enable_redundancy_zones=True, modify_index=4)),
    "operator.autopilot_cas_configuration": lambda c: c.operator.autopilot_cas_configuration(AutopilotConfiguration(cleanup_dead_servers=True, modify_index=4), WRITE_OPTS),
    "operator.autopilot_server_health": lambda c: c.operator.autopilot_server_health(),
    "operator.metrics": lambda c: c.operator.metrics(QueryOptions(**{**QUERY_OPTS.__dict__, "params": {"x": "y", "format": "prometheus"}})),
    "operator.metrics_summary": lambda c: c.operator.metrics_summary(),

    "services.list": lambda c: c.services.list(qopts()),
    "services.get": lambda c: c.services.get("web app"),
    "services.delete": lambda c: c.services.delete("web", "id/1", WRITE_OPTS),
    "search.prefix_search": lambda c: c.search.prefix_search("nom", "jobs", qopts()),
    "search.fuzzy_search": lambda c: c.search.fuzzy_search("nomad", "all"),
    "system.garbage_collect": lambda c: c.system.garbage_collect(),
    "system.reconcile_summaries": lambda c: c.system.reconcile_summaries(),

    "jobs.scale_with_request": lambda c: c.jobs.scale_with_request("j1", ScalingRequest(count=3, target={"Job": "j1", "Group": "g"}, message="m", policy_override=True, job_modify_index=7), WRITE_OPTS),
    "scaling.list_policies": lambda c: c.scaling.list_policies(qopts()),
    "scaling.get_policy": lambda c: c.scaling.get_policy("sp1"),
    "recommendations.list": lambda c: c.recommendations.list(qopts()),
    "recommendations.info": lambda c: c.recommendations.info("r1"),
    "recommendations.upsert": lambda c: c.recommendations.upsert(Recommendation(
        job_id="j1", group="g", task="t", resource="CPU", value=200, meta={"k": "v"}, stats={"mean": 1.5}, enforce_version=True), WRITE_OPTS),
    "recommendations.delete": lambda c: c.recommendations.delete(["r1", "r2"], WRITE_OPTS),
    "recommendations.apply": lambda c: c.recommendations.apply(["r1"], True),

    "keyring.list": lambda c: c.keyring.list(qopts()),
    "keyring.delete": lambda c: c.keyring.delete("k 1", WRITE_OPTS, force=True),
    "keyring.rotate": lambda c: c.keyring.rotate(WRITE_OPTS, full=True, algorithm="aes256-gcm", publish_time=1700000000000000000),
    "keyring.rotate_default": lambda c: c.keyring.rotate(),

    "quotas.list": lambda c: c.quotas.list(),
    "quotas.prefix_list": lambda c: c.quotas.prefix_list("pre"),
    "quotas.list_usage": lambda c: c.quotas.list_usage(),
    "quotas.prefix_list_usage": lambda c: c.quotas.prefix_list_usage("pre", qopts()),
    "quotas.info": lambda c: c.quotas.info("q1"),
    "quotas.usage": lambda c: c.quotas.usage("q1"),
    "quotas.register": lambda c: c.quotas.register(QuotaSpec(name="q1", description="d", limits=[QuotaLimit(
        region="global", variables_limit=5,
        region_limit=QuotaResources(cpu=1000, memory_mb=1024, storage=QuotaStorageResources(variables_mb=10, host_volumes_mb=20),
                                    node_pools=[NodePoolLimit(node_pool="default", cores=2)]))]), WRITE_OPTS),
    "quotas.delete": lambda c: c.quotas.delete("q1"),
    "sentinel_policies.list": lambda c: c.sentinel_policies.list(),
    "sentinel_policies.upsert": lambda c: c.sentinel_policies.upsert(SentinelPolicy(
        name="s1", description="d", scope="submit-job", enforcement_level="advisory", policy="main = rule { true }"), WRITE_OPTS),
    "sentinel_policies.delete": lambda c: c.sentinel_policies.delete("s1"),
    "sentinel_policies.info": lambda c: c.sentinel_policies.info("s1"),

    "csi_volumes.list": lambda c: c.csi_volumes.list(qopts()),
    "csi_volumes.list_external": lambda c: c.csi_volumes.list_external("plug", qopts()),
    "csi_volumes.plugin_list": lambda c: c.csi_volumes.plugin_list("plug"),
    "csi_volumes.info": lambda c: c.csi_volumes.info("v1"),
    "csi_volumes.register": lambda c: c.csi_volumes.register(CSIVolume(
        id="v1", name="vol", external_id="ext", plugin_id="plug",
        requested_capabilities=[CSIVolumeCapability(access_mode="single-node-writer", attachment_mode="file-system")], secrets={"k": "csisecretvalue"}), WRITE_OPTS),
    "csi_volumes.deregister": lambda c: c.csi_volumes.deregister("v 1", True, WRITE_OPTS),
    "csi_volumes.create": lambda c: c.csi_volumes.create(CSIVolume(id="v1", name="vol", plugin_id="plug", requested_capacity_min=1024)),
    "csi_volumes.delete": lambda c: c.csi_volumes.delete("ext 1", WRITE_OPTS, secrets={"k": "csisecretvalue"}),
    "csi_volumes.detach": lambda c: c.csi_volumes.detach("v1", "n1"),
    "csi_volumes.create_snapshot": lambda c: c.csi_volumes.create_snapshot(CSISnapshot(name="snap", plugin_id="plug", source_volume_id="v1", secrets={"k": "csisecretvalue"})),
    "csi_volumes.delete_snapshot": lambda c: c.csi_volumes.delete_snapshot(CSISnapshot(id="s1", plugin_id="plug", secrets={"k": "csisecretvalue"}), WRITE_OPTS),
    "csi_volumes.list_snapshots": lambda c: c.csi_volumes.list_snapshots("plug", qopts()),
    "csi_volumes.list_snapshots_opts": lambda c: c.csi_volumes.list_snapshots("plug", qopts(), secrets={"k": "csisecretvalue"}),
    "csi_plugins.list": lambda c: c.csi_plugins.list(),
    "csi_plugins.info": lambda c: c.csi_plugins.info("plug", qopts()),
    "host_volumes.create": lambda c: c.host_volumes.create(HostVolume(
        name="hv", plugin_id="mkdir", node_pool="default", parameters={"mode": "0700"},
        requested_capabilities=[HostVolumeCapability(attachment_mode="file-system", access_mode="single-node-writer")]), WRITE_OPTS, policy_override=True),
    "host_volumes.register": lambda c: c.host_volumes.register(HostVolume(name="hv", node_id="n1", host_path="/tmp/hv", capacity_bytes=2048)),
    "host_volumes.get": lambda c: c.host_volumes.get("hv 1", qopts()),
    "host_volumes.list": lambda c: c.host_volumes.list(node_id="n1", node_pool="default"),
    "host_volumes.list_all": lambda c: c.host_volumes.list(),
    "host_volumes.delete": lambda c: c.host_volumes.delete("hv 1", WRITE_OPTS, force=True),
    "task_group_host_volume_claims.list": lambda c: c.task_group_host_volume_claims.list(qopts(), job_id="j1", task_group="g", volume_name="hv"),
    "task_group_host_volume_claims.delete": lambda c: c.task_group_host_volume_claims.delete("c 1", WRITE_OPTS),

    "event_stream.stream": lambda c: list(c.event_stream.stream({"Job": ["j1", "j2"], "Node": []}, 7, qopts())),
    "alloc_fs.list": lambda c: c.alloc_fs.list("a1", "/alloc"),
    "alloc_fs.stat": lambda c: c.alloc_fs.stat("a1", "alloc/logs", qopts()),
    "alloc_fs.read_at": lambda c: c.alloc_fs.read_at("a1", "alloc/logs/t.stdout.0", 10, 20),
    "alloc_fs.cat": lambda c: c.alloc_fs.cat("a1", "alloc/logs/t.stdout.0"),
    "alloc_fs.stream": lambda c: list(c.alloc_fs.stream("a1", "alloc/logs/t.stdout.0", "start", 5)),
    "alloc_fs.logs": lambda c: list(c.alloc_fs.logs("a1", True, "t", "stderr", "end", 0)),

    "namespaces.list": lambda c: c.namespaces.list(),
    "namespaces.prefix_list": lambda c: c.namespaces.prefix_list("pre", qopts()),
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
    "nodes.force_evaluate": {"EvalID": ""},
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
    recorder.response = RESPONSES.get(expected["op"], json.loads(expected["response"]) if expected["response"] else None)
    client = Client(Config(address=recorder.address, region="r0", namespace="ns0", secret_id="tok0", headers={"X-Custom": "1"}))
    OPS[expected["op"]](client)
    got = recorder.last
    # Credentials travel in headers or bodies only; the recorder sees the full request line.
    for secret in CREDENTIALS:
        assert secret not in got["path"], f"{secret!r} in path"
        assert secret not in urllib.parse.urlencode(got["query"], doseq=True), f"{secret!r} in query"
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
