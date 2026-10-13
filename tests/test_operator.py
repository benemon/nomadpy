import os

import pytest

from nomadpy import QueryOptions, UnexpectedResponseError
from nomadpy.operator import SCHEDULER_ALGORITHM_BINPACK

ENT_ONLY = "Nomad Enterprise only endpoint"


def test_raft(client):
    config = client.operator.raft_get_configuration()
    assert len(config.servers) == 1 and config.index >= 0
    server = config.servers[0]
    assert server.leader and server.voter and server.id and server.address
    with pytest.raises(UnexpectedResponseError):
        client.operator.raft_remove_peer_by_id("00000000-0000-0000-0000-000000000000")
    with pytest.raises(UnexpectedResponseError):
        client.operator.raft_remove_peer_by_address("127.0.0.1:1")
    with pytest.raises(UnexpectedResponseError):
        client.operator.raft_transfer_leadership_by_id("00000000-0000-0000-0000-000000000000")
    with pytest.raises(UnexpectedResponseError):
        client.operator.raft_transfer_leadership_by_address("127.0.0.1:1")


def test_scheduler_configuration(client):
    resp, qm = client.operator.scheduler_get_configuration()
    conf = resp.scheduler_config
    assert conf.scheduler_algorithm == SCHEDULER_ALGORITHM_BINPACK and qm.last_index > 0
    assert conf.pause_eval_broker is False and conf.preemption_config.system_scheduler_enabled is True

    conf.memory_oversubscription_enabled = True
    set_resp, wm = client.operator.scheduler_set_configuration(conf)
    assert set_resp.updated is True and wm.last_index > 0
    again, _ = client.operator.scheduler_get_configuration()
    assert again.scheduler_config.memory_oversubscription_enabled is True

    stale = again.scheduler_config
    stale.modify_index = conf.modify_index
    cas, _ = client.operator.scheduler_cas_configuration(stale)
    assert cas.updated is False
    fresh = client.operator.scheduler_get_configuration()[0].scheduler_config
    fresh.memory_oversubscription_enabled = False
    cas, _ = client.operator.scheduler_cas_configuration(fresh)
    assert cas.updated is True


def test_license_on_community(client):
    reply, qm = client.operator.license_get()
    assert reply is None and qm.request_time.total_seconds() >= 0
    with pytest.raises(UnexpectedResponseError) as e:
        client.operator.apply_license("not-a-licence")
    assert e.value.status_code == 501 and e.value.body == ENT_ONLY


def test_license_on_enterprise(ent_client):
    reply, qm = ent_client.operator.license_get()
    assert reply.license.product == "nomad" and qm.last_index >= 0
    assert "Namespaces" in reply.license.features
    assert reply.license.expiration_time > "2026"
    # Licences are configured on the server; the Go client still carries ApplyLicense but 2.0.5+ent answers 405.
    with open(os.environ["NOMAD_LICENSE_PATH"]) as f:
        licence = f.read().strip()
    with pytest.raises(UnexpectedResponseError) as e:
        ent_client.operator.apply_license(licence, force=True)
    assert e.value.status_code == 405 and e.value.body == "Invalid method"


def test_upgrade_check(client):
    check, qm = client.operator.upgrade_check_vault_workload_identity()
    assert check.ready() and qm.last_index >= 0


def test_utilization_on_community(client):
    with pytest.raises(UnexpectedResponseError) as e:
        client.operator.utilization(today_only=True)
    assert e.value.status_code == 501 and e.value.body == ENT_ONLY


def test_utilization_on_enterprise(ent_client):
    resp, wm = ent_client.operator.utilization(today_only=True)
    assert resp.bundle and wm.last_index >= 0


def test_autopilot(client):
    conf, qm = client.operator.autopilot_get_configuration()
    assert conf.cleanup_dead_servers is True and qm.last_index >= 0
    assert conf.last_contact_threshold == 200_000_000
    assert conf.server_stabilization_time == 10_000_000_000

    conf.max_trailing_logs = 300
    wm = client.operator.autopilot_set_configuration(conf)
    assert wm.last_index >= 0
    again, _ = client.operator.autopilot_get_configuration()
    assert again.max_trailing_logs == 300

    stale = again
    stale.modify_index = conf.modify_index
    updated, _ = client.operator.autopilot_cas_configuration(stale)
    assert updated is False
    fresh, _ = client.operator.autopilot_get_configuration()
    fresh.max_trailing_logs = 250
    updated, _ = client.operator.autopilot_cas_configuration(fresh)
    assert updated is True

    health, _ = client.operator.autopilot_server_health()
    assert health.healthy is True and health.leader
    assert health.servers[0].leader is True and health.servers[0].healthy is True
    assert health.servers[0].stable_since


def test_metrics(client):
    summary, qm = client.operator.metrics_summary()
    assert summary.timestamp and any(g.name.startswith("nomad.") for g in summary.gauges)
    assert qm.request_time.total_seconds() >= 0
    raw = client.operator.metrics(QueryOptions(params={"format": "prometheus"}))
    assert b"nomad_" in raw
