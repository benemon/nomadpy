import pytest

from nomadpy import SchedulerWorkerPoolArgs, UnexpectedResponseError


def test_self_and_cached_identity(client):
    info = client.agent.self()
    assert info.config["Region"] == "global" and info.config["Datacenter"] == "dc1"
    assert info.member.name == client.agent.node_name()
    assert info.member.tags["role"] == "nomad"
    assert info.stats["nomad"]["server"] == "true"
    assert client.agent.datacenter() == "dc1"
    assert client.agent.region() == "global"


def test_members_servers_join_leave(client):
    members = client.agent.members()
    assert members.server_region == "global" and members.server_dc == "dc1"
    assert len(members.members) == 1 and members.members[0].status == "alive"

    servers = client.agent.servers()
    assert len(servers) == 1 and servers[0].startswith("127.0.0.1:")
    client.agent.set_servers(servers)
    assert client.agent.servers() == servers

    serf = f"{members.members[0].addr}:{members.members[0].port}"
    joined, warning = client.agent.join(serf)
    assert joined == 1 and warning == ""
    with pytest.raises(RuntimeError):
        client.agent.join("127.0.0.1:1")
    client.agent.force_leave("no-such-node")
    client.agent.force_leave("no-such-node", prune=True)


def test_keyring_without_encryption(client):
    with pytest.raises(UnexpectedResponseError) as e:
        client.agent.list_keys()
    assert e.value.status_code == 500


def test_health_host_reload(client):
    health = client.agent.health()
    assert health.server.ok is True and health.client.ok is True
    # Without a target the server answers with bare host data, which Go decodes to an empty response too.
    assert client.agent.host().agent_id == ""
    host = client.agent.host(server_id="leader")
    assert host.agent_id == client.agent.node_name() and host.host_data.os
    assert host.host_data.disk
    client.agent.reload()


def test_scheduler_workers(client):
    config = client.agent.get_scheduler_worker_config()
    assert config.num_schedulers >= 1 and "service" in config.enabled_schedulers
    # The server rejects a list without the internal _core scheduler.
    updated = client.agent.set_scheduler_worker_config(SchedulerWorkerPoolArgs(config.num_schedulers, ["service", "batch", "_core"]))
    assert {"service", "batch", "_core"} <= set(updated.enabled_schedulers)
    client.agent.set_scheduler_worker_config(config)
    info = client.agent.get_scheduler_workers_info()
    assert info.server_id and len(info.schedulers) == config.num_schedulers
    assert info.schedulers[0].status
