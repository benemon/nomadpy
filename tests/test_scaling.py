import pytest
from jobspecs import register_and_wait, wait_for_deployment, wait_for_eval

from nomadpy import Recommendation, ScalingPolicy, ScalingRequest, UnexpectedResponseError
from nomadpy.evaluations import EVAL_STATUS_COMPLETE
from nomadpy.scaling import SCALING_POLICY_TYPE_HORIZONTAL

ENT_ONLY = "Nomad Enterprise only endpoint"


def test_policies_and_scale_status(client):
    register_and_wait(client, "nomadpy-scaling", scaling=True)
    try:
        stubs, qm = client.scaling.list_policies()
        mine = [s for s in stubs if s.target.get("Job") == "nomadpy-scaling"]
        assert len(mine) == 1 and qm.last_index > 0
        assert mine[0].enabled is True and mine[0].type == SCALING_POLICY_TYPE_HORIZONTAL
        policy, _ = client.scaling.get_policy(mine[0].id)
        assert policy.min == 1 and policy.max == 3 and policy.policy == {"cooldown": "1m"}
        assert policy.target["Group"] == "g" and policy.target["Namespace"] == "default"

        resp, _ = client.jobs.scale_with_request("nomadpy-scaling", ScalingRequest(count=2, target={"Job": "nomadpy-scaling", "Group": "g"}, message="up"))
        assert wait_for_eval(client, resp.eval_id).status == EVAL_STATUS_COMPLETE
        dep, _ = client.jobs.latest_deployment("nomadpy-scaling")
        wait_for_deployment(client, dep.id)
        status, _ = client.jobs.scale_status("nomadpy-scaling")
        assert status.job_id == "nomadpy-scaling" and status.task_groups["g"].desired == 2
        events = status.task_groups["g"].events
        assert events[0].count == 2 and events[0].previous_count == 1 and events[0].message == "up"
    finally:
        client.jobs.deregister("nomadpy-scaling", purge=True)


def test_canonicalize():
    policy = ScalingPolicy()
    policy.canonicalize(4)
    assert policy == ScalingPolicy(min=4, enabled=True, type=SCALING_POLICY_TYPE_HORIZONTAL)


def test_recommendations_on_community(client):
    for call in (lambda: client.recommendations.list(), lambda: client.recommendations.info("x"),
                 lambda: client.recommendations.upsert(Recommendation(job_id="j")), lambda: client.recommendations.delete(["x"]),
                 lambda: client.recommendations.apply(["x"])):
        with pytest.raises(UnexpectedResponseError) as e:
            call()
        assert e.value.status_code == 501 and e.value.body == ENT_ONLY


def test_recommendations_on_enterprise(ent_client):
    c = ent_client
    register_and_wait(c, "nomadpy-recs")
    try:
        rec, wm = c.recommendations.upsert(Recommendation(job_id="nomadpy-recs", group="g", task="t", resource="CPU", value=20, meta={"src": "nomadpy"}))
        assert rec.id and rec.current == 10 and wm.last_index > 0
        got, _ = c.recommendations.info(rec.id)
        assert got.value == 20 and got.meta == {"src": "nomadpy"}
        listed, _ = c.recommendations.list()
        assert rec.id in [r.id for r in listed]

        c.recommendations.delete([rec.id])
        assert [r.id for r in c.recommendations.list()[0] if r.id == rec.id] == []

        rec, _ = c.recommendations.upsert(Recommendation(job_id="nomadpy-recs", group="g", task="t", resource="CPU", value=20))
        applied, _ = c.recommendations.apply([rec.id])
        assert applied.errors == [] and applied.updated_jobs[0].job_id == "nomadpy-recs"
        assert applied.updated_jobs[0].recommendations == [rec.id]
        job, _ = c.jobs.info("nomadpy-recs")
        assert job.task_groups[0].tasks[0].resources.cpu == 20
    finally:
        c.jobs.deregister("nomadpy-recs", purge=True)
