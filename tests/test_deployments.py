import pytest

from nomadpy import UnexpectedResponseError
from nomadpy.deployments import (
    DEPLOYMENT_STATUS_FAILED,
    DEPLOYMENT_STATUS_PAUSED,
    DEPLOYMENT_STATUS_RUNNING,
    DEPLOYMENT_STATUS_SUCCESSFUL,
)
from nomadpy.evaluations import EVAL_STATUS_COMPLETE

from jobspecs import register_and_wait, service_job, wait_for_deployment, wait_for_eval


def _second_version(client, job_id, **spec):
    """Registers a new version of a running job and returns its deployment while it is still running."""
    job = client.jobs.parse_hcl(service_job(job_id, **spec))
    resp, _ = client.jobs.register(job)
    assert wait_for_eval(client, resp.eval_id).status == EVAL_STATUS_COMPLETE
    dep, _ = client.jobs.latest_deployment(job_id)
    assert dep.job_version == 1
    return dep


def test_list_info_allocations(client):
    job_id = "nomadpy-deploy"
    dep = register_and_wait(client, job_id)
    deployments, qm = client.deployments.list()
    assert dep.id in [d.id for d in deployments]
    assert [d.create_index for d in deployments] == sorted((d.create_index for d in deployments), reverse=True)
    by_prefix, _ = client.deployments.prefix_list(dep.id[:8])
    assert [d.id for d in by_prefix] == [dep.id]

    info, _ = client.deployments.info(dep.id)
    assert info.job_id == job_id and info.status == DEPLOYMENT_STATUS_SUCCESSFUL
    assert info.task_groups["g"].desired_total == 1
    allocs, _ = client.deployments.allocations(dep.id)
    assert len(allocs) == 1 and allocs[0].job_id == job_id
    assert allocs[0].deployment_status.healthy is True
    client.jobs.deregister(job_id, purge=True)


def test_pause_and_resume(client):
    job_id = "nomadpy-deploy-pause"
    register_and_wait(client, job_id)
    dep = _second_version(client, job_id, sleep=601)
    resp, wm = client.deployments.pause(dep.id, True)
    assert resp.deployment_modify_index > 0 and wm.last_index > 0
    assert wait_for_deployment(client, dep.id, until=DEPLOYMENT_STATUS_PAUSED).status == DEPLOYMENT_STATUS_PAUSED
    client.deployments.pause(dep.id, False)
    assert wait_for_deployment(client, dep.id).status == DEPLOYMENT_STATUS_SUCCESSFUL
    client.jobs.deregister(job_id, purge=True)


def test_promote_canary(client):
    job_id = "nomadpy-deploy-canary"
    register_and_wait(client, job_id)
    dep = _second_version(client, job_id, canary=1, sleep=601)
    running = wait_for_deployment(client, dep.id, until=DEPLOYMENT_STATUS_RUNNING)
    assert running.task_groups["g"].desired_canaries == 1
    deadline_dep = _wait_for_healthy_canary(client, dep.id)
    assert deadline_dep.task_groups["g"].promoted is False
    resp, _ = client.deployments.promote_all(dep.id)
    assert resp.eval_id
    promoted = wait_for_deployment(client, dep.id)
    assert promoted.status == DEPLOYMENT_STATUS_SUCCESSFUL
    assert promoted.task_groups["g"].promoted is True
    client.jobs.deregister(job_id, purge=True)


def _wait_for_healthy_canary(client, deployment_id):
    import time

    from nomadpy import QueryOptions
    from jobspecs import WAIT, DEADLINE

    index = 0
    deadline = time.monotonic() + DEADLINE
    while time.monotonic() < deadline:
        dep, qm = client.deployments.info(deployment_id, QueryOptions(wait_index=index, wait_time=WAIT))
        if dep.task_groups["g"].healthy_allocs >= 1:
            return dep
        index = qm.last_index
    raise AssertionError("canary never became healthy")


def test_fail(client):
    job_id = "nomadpy-deploy-fail"
    register_and_wait(client, job_id)
    dep = _second_version(client, job_id, sleep=601)
    resp, _ = client.deployments.fail(dep.id)
    assert resp.eval_id
    assert wait_for_deployment(client, dep.id).status == DEPLOYMENT_STATUS_FAILED
    client.jobs.deregister(job_id, purge=True)


def test_set_alloc_health(client):
    job_id = "nomadpy-deploy-health"
    register_and_wait(client, job_id)
    dep = _second_version(client, job_id, sleep=601)
    allocs, _ = client.deployments.allocations(dep.id)
    resp, _ = client.deployments.set_alloc_health(dep.id, [], [a.id for a in allocs])
    assert resp.deployment_modify_index > 0
    assert wait_for_deployment(client, dep.id).status == DEPLOYMENT_STATUS_FAILED
    client.jobs.deregister(job_id, purge=True)


def test_unblock_rejected_for_single_region(client):
    job_id = "nomadpy-deploy-unblock"
    dep = register_and_wait(client, job_id)
    with pytest.raises(UnexpectedResponseError) as e:
        client.deployments.unblock(dep.id)
    assert e.value.status_code == 500
    client.jobs.deregister(job_id, purge=True)
