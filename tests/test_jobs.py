import pytest

from nomadpy import QueryOptions, UnexpectedResponseError, WriteOptions
from nomadpy.deployments import DEPLOYMENT_STATUS_SUCCESSFUL
from nomadpy.evaluations import EVAL_STATUS_COMPLETE

from jobspecs import batch_job, register_and_wait, service_job, wait_for_eval, wait_for_deployment


def test_parse_hcl(client):
    job = client.jobs.parse_hcl(service_job("nomadpy-parse"))
    assert job["ID"] == "nomadpy-parse"
    assert job["TaskGroups"][0]["Tasks"][0]["Driver"] == "raw_exec"
    assert job["Namespace"] is None
    canonical = client.jobs.parse_hcl(service_job("nomadpy-parse"), canonicalize=True)
    assert canonical["Namespace"] == "default"


def test_parse_hcl_variables(client):
    hcl = 'variable "n" { type = number }\n' + service_job("nomadpy-vars", count="var.n")
    job = client.jobs.parse_hcl(hcl, variables="n = 3")
    assert job["TaskGroups"][0]["Count"] == 3


def test_validate(client):
    job = client.jobs.parse_hcl(service_job("nomadpy-validate"))
    resp, wm = client.jobs.validate(job)
    assert resp.error == ""
    assert resp.validation_errors is None
    job["TaskGroups"][0]["Tasks"][0]["Driver"] = ""
    resp, _ = client.jobs.validate(job)
    assert resp.validation_errors


def test_register_deploy_inspect_deregister(client):
    job_id = "nomadpy-svc"
    dep = register_and_wait(client, job_id)
    assert dep.status == DEPLOYMENT_STATUS_SUCCESSFUL
    assert dep.task_groups["g"].healthy_allocs == 1

    summary, qm = client.jobs.summary(job_id)
    assert summary.job_id == job_id
    assert summary.summary["g"].running == 1
    assert qm.last_index > 0

    info, _ = client.jobs.info(job_id)
    assert info["Status"] == "running"
    assert info["Version"] == 0

    jobs, _ = client.jobs.list()
    assert [j.id for j in jobs if j.id == job_id] == [job_id]
    stub = next(j for j in jobs if j.id == job_id)
    assert stub.type == "service"
    assert stub.job_summary.summary["g"].running == 1
    jobs, _ = client.jobs.prefix_list("nomadpy-sv")
    assert [j.id for j in jobs] == [job_id]
    jobs, _ = client.jobs.prefix_list("no-such-prefix")
    assert jobs == []

    allocs, _ = client.jobs.allocations(job_id)
    assert len(allocs) == 1 and allocs[0]["ClientStatus"] == "running"
    evals, _ = client.jobs.evaluations(job_id)
    assert evals and evals[0].status == EVAL_STATUS_COMPLETE
    deployments, _ = client.jobs.deployments(job_id)
    assert [d.id for d in deployments] == [dep.id]

    eval_id, wm = client.jobs.deregister(job_id, purge=True)
    assert eval_id and wm.last_index > 0
    with pytest.raises(UnexpectedResponseError) as e:
        client.jobs.info(job_id)
    assert e.value.status_code == 404


def test_scale_and_scale_status(client):
    job_id = "nomadpy-scale"
    register_and_wait(client, job_id)
    resp, _ = client.jobs.scale(job_id, "g", 2, message="nomadpy test")
    assert wait_for_eval(client, resp.eval_id).status == EVAL_STATUS_COMPLETE
    dep, _ = client.jobs.latest_deployment(job_id)
    assert wait_for_deployment(client, dep.id).task_groups["g"].desired_total == 2
    status, _ = client.jobs.scale_status(job_id)
    assert status.task_groups["g"].desired == 2
    client.jobs.deregister(job_id, purge=True)


def test_versions_revert_stable_tags(client):
    job_id = "nomadpy-versions"
    hcl = service_job(job_id)
    resp, _ = client.jobs.register(client.jobs.parse_hcl(hcl), submission={"Source": hcl, "Format": "hcl2"})
    assert wait_for_eval(client, resp.eval_id).status == EVAL_STATUS_COMPLETE
    dep, _ = client.jobs.latest_deployment(job_id)
    assert wait_for_deployment(client, dep.id).status == DEPLOYMENT_STATUS_SUCCESSFUL
    register_and_wait(client, job_id, sleep=601)
    versions, diffs, _ = client.jobs.versions(job_id, diffs=True)
    assert [v["Version"] for v in versions] == [1, 0]
    assert diffs[0]["Type"] == "Edited"

    client.jobs.tag_version(job_id, "golden", version=0, description="first")
    tagged, _ = client.jobs.version_by_tag(job_id, "golden")
    assert tagged["Version"] == 0
    client.jobs.untag_version(job_id, "golden")
    with pytest.raises(LookupError):
        client.jobs.version_by_tag(job_id, "golden")

    _, wm = client.jobs.stable(job_id, 1, True)
    assert wm.last_index > 0
    info, _ = client.jobs.info(job_id)
    assert info["Stable"] is True

    resp, _ = client.jobs.revert(job_id, 0)
    assert wait_for_eval(client, resp.eval_id).status == EVAL_STATUS_COMPLETE
    info, _ = client.jobs.info(job_id)
    assert info["Version"] == 2
    assert info["TaskGroups"][0]["Tasks"][0]["Config"]["args"][-1] == "sleep 600"

    sub, _ = client.jobs.submission(job_id, 0)
    assert sub["Format"] == "hcl2" and sub["Source"] == hcl
    client.jobs.deregister(job_id, purge=True)


def test_plan(client):
    job_id = "nomadpy-plan"
    register_and_wait(client, job_id)
    job = client.jobs.parse_hcl(service_job(job_id, count=3))
    plan, wm = client.jobs.plan(job, diff=True)
    assert plan.diff["Type"] == "Edited"
    assert plan.annotations["DesiredTGUpdates"]["g"]["Place"] == 2
    assert plan.job_modify_index > 0
    with pytest.raises(ValueError):
        client.jobs.plan({"Name": "no-id"})
    client.jobs.deregister(job_id, purge=True)


def test_force_evaluate_and_periodic_force(client):
    job_id = "nomadpy-periodic"
    job = client.jobs.parse_hcl(batch_job(job_id, periodic=True))
    client.jobs.register(job)
    eval_id, _ = client.jobs.periodic_force(job_id)
    assert wait_for_eval(client, eval_id).status == EVAL_STATUS_COMPLETE
    children, _ = client.jobs.prefix_list(job_id + "/periodic-")
    assert len(children) == 1

    eval_id, _ = client.jobs.force_evaluate(children[0].id, force_reschedule=True)
    assert wait_for_eval(client, eval_id).status == EVAL_STATUS_COMPLETE
    client.jobs.deregister(job_id, purge=True)


def test_dispatch(client):
    job_id = "nomadpy-param"
    job = client.jobs.parse_hcl(batch_job(job_id, parameterized=True))
    client.jobs.register(job)
    resp, wm = client.jobs.dispatch(job_id, meta={"key": "v"}, payload=b"\x00hello", id_prefix_template="pfx")
    assert resp.dispatched_job_id.startswith(job_id + "/dispatch-pfx-")
    assert wait_for_eval(client, resp.eval_id).status == EVAL_STATUS_COMPLETE
    child, _ = client.jobs.info(resp.dispatched_job_id)
    assert child["Meta"] == {"key": "v"}
    assert child["Payload"] == "AGhlbGxv"
    client.jobs.deregister(job_id, purge=True)


def test_namespace_scoping(client):
    client.put("/v1/namespace/nomadpy-jobs-ns", {"Name": "nomadpy-jobs-ns"})
    job = client.jobs.parse_hcl(service_job("nomadpy-ns"))
    job["Namespace"] = "nomadpy-jobs-ns"
    resp, _ = client.jobs.register(job, WriteOptions(namespace="nomadpy-jobs-ns"))
    assert wait_for_eval(client, resp.eval_id).status == EVAL_STATUS_COMPLETE
    with pytest.raises(UnexpectedResponseError):
        client.jobs.info("nomadpy-ns")
    info, _ = client.jobs.info("nomadpy-ns", QueryOptions(namespace="nomadpy-jobs-ns"))
    assert info["Namespace"] == "nomadpy-jobs-ns"
    jobs, _ = client.jobs.list(QueryOptions(namespace="*"))
    assert any(j.id == "nomadpy-ns" and j.namespace == "nomadpy-jobs-ns" for j in jobs)
    client.jobs.deregister("nomadpy-ns", purge=True, w=WriteOptions(namespace="nomadpy-jobs-ns"))
    client.delete("/v1/namespace/nomadpy-jobs-ns")


def test_services_empty(client):
    job_id = "nomadpy-services"
    register_and_wait(client, job_id)
    services, _ = client.jobs.services(job_id)
    assert services == []
    client.jobs.deregister(job_id, purge=True)
