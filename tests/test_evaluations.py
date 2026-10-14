import pytest

from nomadpy import UnexpectedResponseError
from nomadpy.evaluations import EVAL_STATUS_COMPLETE

from jobspecs import register_and_wait


def test_list_info_count_allocations(client):
    job_id = "nomadpy-evals"
    register_and_wait(client, job_id)
    evals, qm = client.evaluations.list()
    mine = [e for e in evals if e.job_id == job_id]
    assert mine and qm.last_index > 0
    assert [e.create_index for e in evals] == sorted((e.create_index for e in evals), reverse=True)

    ev, _ = client.evaluations.info(mine[-1].id)
    assert ev.status == EVAL_STATUS_COMPLETE
    assert ev.triggered_by == "job-register"
    assert ev.type == "service"
    assert ev.deployment_id

    allocs, _ = client.evaluations.allocations(ev.id)
    assert len(allocs) == 1 and allocs[0].job_id == job_id

    by_prefix, _ = client.evaluations.prefix_list(ev.id[:8])
    assert [e.id for e in by_prefix] == [ev.id]

    count, _ = client.evaluations.count()
    assert count >= len(evals)
    client.jobs.deregister(job_id, purge=True)


def test_delete_requires_paused_broker(client):
    job_id = "nomadpy-evals-delete"
    register_and_wait(client, job_id)
    client.jobs.deregister(job_id, purge=True)
    evals, _ = client.evaluations.list()
    ids = [e.id for e in evals if e.job_id == job_id]
    assert ids

    with pytest.raises(UnexpectedResponseError) as e:
        client.evaluations.delete(ids)
    assert e.value.status_code == 500

    config, _ = client.query("/v1/operator/scheduler/configuration")
    sc = config["SchedulerConfig"]
    sc["PauseEvalBroker"] = True
    client.put("/v1/operator/scheduler/configuration", sc)
    try:
        count, wm = client.evaluations.delete(ids)
        assert count == len(ids) and wm.last_index > 0
        count, _ = client.evaluations.delete(filter=f'JobID == "{job_id}"')
        assert count == 0
    finally:
        sc["PauseEvalBroker"] = False
        client.put("/v1/operator/scheduler/configuration", sc)
