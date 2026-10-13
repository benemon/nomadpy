import time

import pytest

from nomadpy import QueryOptions, UnexpectedResponseError
from nomadpy.allocations import ALLOC_CLIENT_STATUS_COMPLETE, ALLOC_CLIENT_STATUS_RUNNING, ALLOC_DESIRED_STATUS_STOP
from nomadpy.evaluations import EVAL_STATUS_COMPLETE

from jobspecs import DEADLINE, WAIT, register_and_wait, wait_for_eval


def _wait_for_alloc(client, alloc_id, predicate):
    index, deadline = 0, time.monotonic() + DEADLINE
    while time.monotonic() < deadline:
        alloc, qm = client.allocations.info(alloc_id, QueryOptions(wait_index=index, wait_time=WAIT))
        if predicate(alloc):
            return alloc
        index = qm.last_index
    raise AssertionError(f"allocation {alloc_id} never satisfied the predicate")


def test_list_info_stats_checks_services(client):
    register_and_wait(client, "nomadpy-allocs")
    try:
        stubs, qm = client.allocations.list()
        mine = [a for a in stubs if a.job_id == "nomadpy-allocs"]
        assert len(mine) == 1 and qm.last_index > 0
        stub = mine[0]
        assert stub.client_status == ALLOC_CLIENT_STATUS_RUNNING and stub.task_group == "g"
        assert stub.deployment_status.healthy is True
        assert stub.task_states["t"]["State"] == "running"
        assert stub.allocated_resources is None
        assert [a.create_index for a in stubs] == sorted((a.create_index for a in stubs), reverse=True)

        (with_resources,), _ = client.allocations.prefix_list(stub.id[:8])
        assert with_resources.id == stub.id

        alloc, _ = client.allocations.info(stub.id)
        assert alloc["ID"] == stub.id and alloc["Job"]["ID"] == "nomadpy-allocs"
        stats = client.allocations.stats(stub.id)
        assert "ResourceUsage" in stats and "Tasks" in stats
        assert client.allocations.checks(stub.id) == {}
        services, _ = client.allocations.services(stub.id)
        assert services == []
    finally:
        client.jobs.deregister("nomadpy-allocs", purge=True)


def test_restart_signal_pause_stop(client):
    register_and_wait(client, "nomadpy-alloc-ops")
    try:
        (stub,), _ = client.allocations.list(QueryOptions(filter='JobID == "nomadpy-alloc-ops"'))
        started = stub.task_states["t"]["StartedAt"]
        client.allocations.restart(stub.id, "t")
        restarted = _wait_for_alloc(client, stub.id, lambda a: a["TaskStates"]["t"]["Restarts"] == 1)
        assert restarted["TaskStates"]["t"]["StartedAt"] != started
        client.allocations.restart_all_tasks(stub.id)
        _wait_for_alloc(client, stub.id, lambda a: a["TaskStates"]["t"]["Restarts"] == 2)

        client.allocations.signal(stub.id, "t", "SIGUSR1")
        _wait_for_alloc(client, stub.id, lambda a: any(e["Type"] == "Signaling" for e in a["TaskStates"]["t"]["Events"]))

        # Task pause is Enterprise; Community answers 500.
        with pytest.raises(UnexpectedResponseError) as e:
            client.allocations.get_pause_state(stub.id, "t")
        assert e.value.status_code == 500 and e.value.body == "Enterprise only"
        with pytest.raises(UnexpectedResponseError) as e:
            client.allocations.set_pause_state(stub.id, "t", "pause")
        assert e.value.status_code == 500 and e.value.body == "Enterprise only"

        resp, qm = client.allocations.stop(stub.id)
        assert resp.eval_id and qm.last_index > 0
        assert wait_for_eval(client, resp.eval_id).status == EVAL_STATUS_COMPLETE
        stopped = _wait_for_alloc(client, stub.id, lambda a: a["ClientStatus"] == ALLOC_CLIENT_STATUS_COMPLETE)
        assert stopped["DesiredStatus"] == ALLOC_DESIRED_STATUS_STOP
        client.allocations.gc(stub.id)
    finally:
        client.jobs.deregister("nomadpy-alloc-ops", purge=True)


def test_unknown_allocation(client):
    with pytest.raises(UnexpectedResponseError) as e:
        client.allocations.info("00000000-0000-0000-0000-000000000000")
    assert e.value.status_code == 404


def test_pause_state_on_enterprise(ent_client):
    register_and_wait(ent_client, "nomadpy-alloc-pause")
    try:
        (stub,), _ = ent_client.allocations.list(QueryOptions(filter='JobID == "nomadpy-alloc-pause"'))
        state, _ = ent_client.allocations.get_pause_state(stub.id, "t")
        assert state in ("", "run")
        # The server reports an operator-set state as forced.
        ent_client.allocations.set_pause_state(stub.id, "t", "pause")
        assert ent_client.allocations.get_pause_state(stub.id, "t")[0] == "force_pause"
        ent_client.allocations.set_pause_state(stub.id, "t", "run")
        assert ent_client.allocations.get_pause_state(stub.id, "t")[0] in ("run", "force_run")
    finally:
        ent_client.jobs.deregister("nomadpy-alloc-pause", purge=True)
