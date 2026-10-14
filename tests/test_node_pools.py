import pytest

from nomadpy import NodePool, NodePoolSchedulerConfiguration, UnexpectedResponseError
from nomadpy.node_pools import NODE_POOL_ALL, NODE_POOL_DEFAULT

from jobspecs import register_and_wait

HOUR = 3_600_000_000_000


def test_builtin_pools(client):
    pools, qm = client.node_pools.list()
    assert {p.name for p in pools} >= {NODE_POOL_ALL, NODE_POOL_DEFAULT} and qm.last_index >= 0
    default, _ = client.node_pools.info(NODE_POOL_DEFAULT)
    assert default.description and default.scheduler_configuration is None
    nodes, _ = client.node_pools.list_nodes(NODE_POOL_DEFAULT)
    assert len(nodes) == 1 and nodes[0].node_pool == NODE_POOL_DEFAULT
    # Built-in pools cannot be deleted.
    for builtin in (NODE_POOL_ALL, NODE_POOL_DEFAULT):
        with pytest.raises(UnexpectedResponseError) as e:
            client.node_pools.delete(builtin)
        assert e.value.status_code == 500


def test_register_info_jobs_delete(client):
    wm = client.node_pools.register(NodePool(name="nomadpy-pool", description="d", meta={"team": "a"}, node_identity_ttl=HOUR))
    assert wm.last_index > 0
    try:
        got, _ = client.node_pools.info("nomadpy-pool")
        assert got.description == "d" and got.meta == {"team": "a"}
        assert got.node_identity_ttl == HOUR and got.create_index > 0
        by_prefix, _ = client.node_pools.prefix_list("nomadpy-p")
        assert [p.name for p in by_prefix] == ["nomadpy-pool"]

        register_and_wait(client, "nomadpy-pool-job")
        try:
            jobs, _ = client.node_pools.list_jobs(NODE_POOL_DEFAULT)
            assert "nomadpy-pool-job" in [j.id for j in jobs]
            jobs, _ = client.node_pools.list_jobs("nomadpy-pool")
            assert jobs == []
        finally:
            client.jobs.deregister("nomadpy-pool-job", purge=True)
        assert client.node_pools.list_nodes("nomadpy-pool")[0] == []
    finally:
        client.node_pools.delete("nomadpy-pool")
    with pytest.raises(UnexpectedResponseError) as e:
        client.node_pools.info("nomadpy-pool")
    assert e.value.status_code == 404
    with pytest.raises(ValueError):
        client.node_pools.register(NodePool())
    with pytest.raises(ValueError):
        client.node_pools.info("")


def test_scheduler_configuration_on_community(client):
    with pytest.raises(UnexpectedResponseError) as e:
        client.node_pools.register(NodePool(name="nomadpy-pool-sched", scheduler_configuration=NodePoolSchedulerConfiguration(scheduler_algorithm="spread")))
    assert e.value.status_code == 500 and "unlicensed" in e.value.body


def test_scheduler_configuration_on_enterprise(ent_client):
    pool = NodePool(name="nomadpy-pool-sched", scheduler_configuration=NodePoolSchedulerConfiguration(scheduler_algorithm="spread", memory_oversubscription_enabled=True))
    ent_client.node_pools.register(pool)
    try:
        got, _ = ent_client.node_pools.info("nomadpy-pool-sched")
        assert got.scheduler_configuration.scheduler_algorithm == "spread"
        assert got.scheduler_configuration.memory_oversubscription_enabled is True
    finally:
        ent_client.node_pools.delete("nomadpy-pool-sched")
