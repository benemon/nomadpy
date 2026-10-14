import time

import pytest
from jobspecs import DEADLINE, WAIT, batch_job, register_and_wait, wait_for_eval

from nomadpy import DrainSpec, QueryOptions, UnexpectedResponseError
from nomadpy.evaluations import EVAL_STATUS_COMPLETE
from nomadpy.nodes import DRAIN_STATUS_CANCELED, DRAIN_STATUS_DRAINING, NODE_SCHEDULING_ELIGIBLE, NODE_SCHEDULING_INELIGIBLE, NODE_STATUS_READY


def _node(client):
    nodes, _ = client.nodes.list()
    assert len(nodes) == 1
    return nodes[0]


def test_list_and_info(client):
    node = _node(client)
    assert node.status == NODE_STATUS_READY
    assert node.scheduling_eligibility == NODE_SCHEDULING_ELIGIBLE
    assert node.drivers["raw_exec"].healthy is True
    assert node.node_resources is None
    assert node.last_drain is None
    assert node.node_pool == "default"

    # The list endpoint only includes resources on request.
    (with_resources,), _ = client.nodes.list(QueryOptions(params={"resources": "true"}))
    assert with_resources.node_resources.cpu.total_cpu_cores > 0
    assert with_resources.node_resources.memory.memory_mb > 0
    assert with_resources.reserved_resources.cpu.cpu_shares >= 0

    by_prefix, qm = client.nodes.prefix_list(node.id[:8], QueryOptions(allow_stale=True))
    assert [n.id for n in by_prefix] == [node.id] and qm.last_index > 0
    info, _ = client.nodes.info(node.id)
    assert info.id == node.id and info.drivers["raw_exec"].detected is True


def test_drain_and_eligibility(client):
    node = _node(client)
    # A running allocation with nowhere to migrate keeps the drain in progress until it is cancelled.
    register_and_wait(client, "nomadpy-node-drain")
    try:
        resp, wm = client.nodes.update_drain(node.id, DrainSpec(deadline=60_000_000_000, ignore_system_jobs=True), meta={"reason": "nomadpy"})
        assert resp.node_modify_index > 0 and wm.last_index > 0
        info, _ = client.nodes.info(node.id)
        assert info.drain_strategy.ignore_system_jobs is True
        assert info.last_drain.status == DRAIN_STATUS_DRAINING
        assert info.last_drain.meta == {"reason": "nomadpy"}
        assert info.scheduling_eligibility == NODE_SCHEDULING_INELIGIBLE

        resp, _ = client.nodes.update_drain(node.id, None, mark_eligible=True)
        assert resp.node_modify_index > 0
        after = _node(client)
        assert after.drain is False
        assert after.last_drain.status == DRAIN_STATUS_CANCELED
        assert after.scheduling_eligibility == NODE_SCHEDULING_ELIGIBLE

        _, wm = client.nodes.toggle_eligibility(node.id, False)
        assert wm.last_index > 0
        assert _node(client).scheduling_eligibility == NODE_SCHEDULING_INELIGIBLE
    finally:
        client.nodes.update_drain(node.id, None, mark_eligible=True)
        client.nodes.toggle_eligibility(node.id, True)
        client.jobs.deregister("nomadpy-node-drain", purge=True)
    assert _node(client).scheduling_eligibility == NODE_SCHEDULING_ELIGIBLE


def test_allocations_evaluate_stats_gc(client):
    node = _node(client)
    register_and_wait(client, "nomadpy-node-alloc")
    try:
        allocs, qm = client.nodes.allocations(node.id)
        assert "nomadpy-node-alloc" in [a.job_id for a in allocs] and qm.last_index > 0
        assert client.nodes.csi_volumes(node.id) == []

        eval_id, wm = client.nodes.force_evaluate(node.id)
        assert isinstance(eval_id, str) and wm.last_index > 0

        stats = client.nodes.stats(node.id)
        assert stats.uptime > 0 and stats.cpu and stats.memory.total > 0
        client.nodes.gc(node.id)
    finally:
        client.jobs.deregister("nomadpy-node-alloc", purge=True)


def test_gc_alloc(client):
    resp, _ = client.jobs.register(client.jobs.parse_hcl(batch_job("nomadpy-node-gc")))
    assert wait_for_eval(client, resp.eval_id).status == EVAL_STATUS_COMPLETE
    allocs, _ = client.jobs.allocations("nomadpy-node-gc")
    assert len(allocs) == 1
    index, deadline = 0, time.monotonic() + DEADLINE
    while time.monotonic() < deadline:
        allocs, qm = client.jobs.allocations("nomadpy-node-gc", q=QueryOptions(wait_index=index, wait_time=WAIT))
        if allocs[0].client_status == "complete":
            break
        index = qm.last_index
    try:
        assert allocs[0].client_status == "complete"
        client.nodes.gc_alloc(allocs[0].id)
    finally:
        client.jobs.deregister("nomadpy-node-gc", purge=True)


def test_purge_unknown_node(client):
    with pytest.raises(UnexpectedResponseError) as e:
        client.nodes.purge("00000000-0000-0000-0000-000000000000")
    assert e.value.status_code == 500


def test_meta(client):
    node = _node(client)
    before = client.nodes.meta.read(node.id)
    assert isinstance(before.static, dict) and "nomadpy" not in before.meta
    applied = client.nodes.meta.apply(node.id, {"nomadpy": "x"})
    assert applied.dynamic["nomadpy"] == "x" and applied.meta["nomadpy"] == "x"
    assert client.nodes.meta.read(node.id).meta["nomadpy"] == "x"
    cleared = client.nodes.meta.apply(node.id, {"nomadpy": None})
    assert "nomadpy" not in cleared.meta
    assert client.nodes.meta.read().meta == cleared.meta


def test_identity(client):
    node = _node(client)
    identity = client.nodes.identity.get(node.id)
    assert identity.claims["nomad_node_id"] == node.id
    client.nodes.identity.renew(node.id)
