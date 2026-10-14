from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from . import allocations as _allocations
from . import constraint as _constraint
from . import tasks as _tasks
from .deployments import Deployment, _deployments
from .evaluations import Evaluation
from .models import Model
from .scaling import JobScaleStatusResponse, ScalingRequest
from .services import ServiceRegistration

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions


JOB_TYPE_SERVICE = "service"
JOB_TYPE_BATCH = "batch"
JOB_TYPE_SYSTEM = "system"
JOB_TYPE_SYSBATCH = "sysbatch"
JOB_DEFAULT_PRIORITY = 50
PERIODIC_SPEC_CRON = "cron"
DEFAULT_NAMESPACE = "default"
GLOBAL_REGION = "global"
JOB_PERIODIC_LAUNCH_SUFFIX = "/periodic-"
JOB_DISPATCH_LAUNCH_SUFFIX = "/dispatch-"


@dataclass
class DesiredUpdates(Model):
    ignore: int = 0
    place: int = 0
    migrate: int = 0
    stop: int = 0
    in_place_update: int = 0
    destructive_update: int = 0
    canary: int = 0
    preemptions: int = 0
    disconnect: int = 0
    reconnect: int = 0
    reschedule_now: int = 0
    reschedule_later: int = 0


@dataclass
class FieldDiff(Model):
    type: str = ""
    name: str = ""
    old: str = ""
    new: str = ""
    annotations: list[str] | None = None


@dataclass
class Job(Model):
    region: str | None = None
    namespace: str | None = None
    id: str | None = field(default=None, metadata={'json': 'ID'})
    name: str | None = None
    type: str | None = None
    priority: int | None = None
    all_at_once: bool | None = None
    datacenters: list[str] | None = None
    node_pool: str | None = None
    constraints: list[_constraint.Constraint] | None = None
    affinities: list[_tasks.Affinity] | None = None
    task_groups: list[_tasks.TaskGroup] | None = None
    update: UpdateStrategy | None = None
    multiregion: Multiregion | None = None
    spreads: list[_tasks.Spread] | None = None
    periodic: PeriodicConfig | None = None
    parameterized_job: ParameterizedJobConfig | None = None
    reschedule: _tasks.ReschedulePolicy | None = None
    migrate: _tasks.MigrateStrategy | None = None
    meta: dict[str, str] | None = None
    ui: JobUIConfig | None = field(default=None, metadata={'json': 'UI'})
    stop: bool | None = None
    parent_id: str | None = field(default=None, metadata={'json': 'ParentID'})
    dispatched: bool = False
    dispatch_idempotency_token: str | None = None
    payload: str | None = None
    consul_namespace: str | None = None
    vault_namespace: str | None = None
    nomad_token_id: str | None = field(default=None, metadata={'json': 'NomadTokenID'})
    status: str | None = None
    status_description: str | None = None
    stable: bool | None = None
    version: int | None = None
    submit_time: int | None = None
    create_index: int | None = None
    modify_index: int | None = None
    job_modify_index: int | None = None
    version_tag: JobVersionTag | None = None


@dataclass
class JobDiff(Model):
    type: str = ""
    id: str = field(default="", metadata={'json': 'ID'})
    fields: list[FieldDiff] | None = None
    objects: list[ObjectDiff] | None = None
    task_groups: list[TaskGroupDiff] | None = None


@dataclass
class JobSubmission(Model):
    source: str = ""
    format: str = ""
    variable_flags: dict[str, str] | None = None
    variables: str = ""


@dataclass
class JobUIConfig(Model):
    description: str = ""
    links: list[JobUILink] | None = None


@dataclass
class JobUILink(Model):
    label: str = ""
    url: str = field(default="", metadata={'json': 'URL'})


@dataclass
class JobVersionTag(Model):
    name: str = ""
    description: str = ""
    tagged_time: int = 0


@dataclass
class Multiregion(Model):
    strategy: MultiregionStrategy | None = None
    regions: list[MultiregionRegion] | None = None


@dataclass
class MultiregionRegion(Model):
    name: str = ""
    count: int | None = None
    datacenters: list[str] | None = None
    node_pool: str = ""
    meta: dict[str, str] | None = None


@dataclass
class MultiregionStrategy(Model):
    max_parallel: int | None = None
    on_failure: str | None = None


@dataclass
class ObjectDiff(Model):
    type: str = ""
    name: str = ""
    fields: list[FieldDiff] | None = None
    objects: list[ObjectDiff] | None = None


@dataclass
class ParameterizedJobConfig(Model):
    payload: str = ""
    meta_required: list[str] | None = None
    meta_optional: list[str] | None = None


@dataclass
class PeriodicConfig(Model):
    enabled: bool | None = None
    spec: str | None = None
    specs: list[str] | None = None
    spec_type: str | None = None
    prohibit_overlap: bool | None = None
    time_zone: str | None = None


@dataclass
class PlanAnnotations(Model):
    desired_tg_updates: dict[str, DesiredUpdates] | None = field(default=None, metadata={'json': 'DesiredTGUpdates'})
    preempted_allocs: list[_allocations.AllocationListStub] | None = None


@dataclass
class TaskDiff(Model):
    type: str = ""
    name: str = ""
    fields: list[FieldDiff] | None = None
    objects: list[ObjectDiff] | None = None
    annotations: list[str] | None = None


@dataclass
class TaskGroupDiff(Model):
    type: str = ""
    name: str = ""
    fields: list[FieldDiff] | None = None
    objects: list[ObjectDiff] | None = None
    tasks: list[TaskDiff] | None = None
    updates: dict[str, int] | None = None


@dataclass
class UpdateStrategy(Model):
    stagger: int | None = None
    max_parallel: int | None = None
    health_check: str | None = None
    min_healthy_time: int | None = None
    healthy_deadline: int | None = None
    progress_deadline: int | None = None
    canary: int | None = None
    auto_revert: bool | None = None
    auto_promote: bool | None = None


@dataclass
class TaskGroupSummary(Model):
    queued: int = 0
    complete: int = 0
    failed: int = 0
    running: int = 0
    starting: int = 0
    lost: int = 0
    unknown: int = 0


@dataclass
class JobChildrenSummary(Model):
    pending: int = 0
    running: int = 0
    dead: int = 0

    def sum(self) -> int:
        return self.pending + self.running + self.dead


@dataclass
class JobSummary(Model):
    job_id: str = field(default="", metadata={"json": "JobID"})
    namespace: str = ""
    summary: dict[str, TaskGroupSummary] = field(default_factory=dict)
    children: JobChildrenSummary | None = None
    create_index: int = 0
    modify_index: int = 0


@dataclass
class JobListStub(Model):
    id: str = field(default="", metadata={"json": "ID"})
    parent_id: str = field(default="", metadata={"json": "ParentID"})
    name: str = ""
    namespace: str = field(default="", metadata={"omitempty": True})
    datacenters: list[str] | None = None
    type: str = ""
    priority: int = 0
    periodic: bool = False
    parameterized_job: bool = False
    stop: bool = False
    status: str = ""
    status_description: str = ""
    job_summary: JobSummary | None = None
    create_index: int = 0
    modify_index: int = 0
    job_modify_index: int = 0
    submit_time: int = 0
    meta: dict[str, str] | None = field(default=None, metadata={"omitempty": True})


@dataclass
class JobValidateResponse(Model):
    driver_config_validated: bool = False
    validation_errors: list[str] | None = None
    error: str = ""
    warnings: str = ""


@dataclass
class JobRegisterResponse(Model):
    eval_id: str = field(default="", metadata={"json": "EvalID"})
    eval_create_index: int = 0
    job_modify_index: int = 0
    warnings: str = ""


@dataclass
class JobPlanResponse(Model):
    job_modify_index: int = 0
    created_evals: list[Evaluation] | None = None
    diff: JobDiff | None = None
    annotations: PlanAnnotations | None = None
    failed_tg_allocs: dict[str, Any] | None = field(default=None, metadata={"json": "FailedTGAllocs"})
    next_periodic_launch: str = field(default="", metadata={"time": True})
    warnings: str = ""


@dataclass
class JobDispatchResponse(Model):
    dispatched_job_id: str = field(default="", metadata={"json": "DispatchedJobID"})
    eval_id: str = field(default="", metadata={"json": "EvalID"})
    eval_create_index: int = 0
    job_create_index: int = 0


@dataclass
class JobStabilityResponse(Model):
    job_modify_index: int = 0


def _path(job_id: str) -> str:
    return "/v1/job/" + quote(job_id, safe="")


def _job_json(job: Model | dict[str, Any]) -> dict[str, Any]:
    return job.to_json() if isinstance(job, Model) else job


class Jobs:
    """Jobs queries the job endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def parse_hcl(self, job_hcl: str, canonicalize: bool = False, *, variables: str = "") -> Job:
        """parse_hcl converts an HCL job specification to a Job using the server."""
        req = {"JobHCL": job_hcl, "Canonicalize": canonicalize, "Variables": variables}
        resp, _ = self._client.put("/v1/jobs/parse", req)
        return Job.from_json(resp)

    def validate(self, job: Job | dict[str, Any], w: WriteOptions | None = None) -> tuple[JobValidateResponse, WriteMeta]:
        req: dict[str, Any] = {"Job": _job_json(job)}
        if w is not None and w.region:
            req["Region"] = w.region
        resp, wm = self._client.put("/v1/validate/job", req, w)
        return JobValidateResponse.from_json(resp), wm

    def register(self, job: Job | dict[str, Any], w: WriteOptions | None = None, *, enforce_index: bool = False, modify_index: int = 0,
                 policy_override: bool = False, preserve_counts: bool = False, preserve_resources: bool = False,
                 eval_priority: int = 0, submission: JobSubmission | dict[str, Any] | None = None) -> tuple[JobRegisterResponse, WriteMeta]:
        """register submits a Job, or a dict in the JSON shape the API documents."""
        req: dict[str, Any] = {"Job": _job_json(job)}
        if enforce_index:
            req["EnforceIndex"] = True
            req["JobModifyIndex"] = modify_index
        if policy_override:
            req["PolicyOverride"] = True
        if preserve_counts:
            req["PreserveCounts"] = True
        if preserve_resources:
            req["PreserveResources"] = True
        if eval_priority:
            req["EvalPriority"] = eval_priority
        if submission is not None:
            req["Submission"] = _job_json(submission)
        resp, wm = self._client.put("/v1/jobs", req, w)
        return JobRegisterResponse.from_json(resp), wm

    def list(self, q: QueryOptions | None = None, *, meta: bool = False) -> tuple[list[JobListStub], QueryMeta]:
        endpoint = "/v1/jobs?meta=true" if meta else "/v1/jobs"
        resp, qm = self._client.query(endpoint, q)
        jobs = [JobListStub.from_json(j) for j in resp]
        jobs.sort(key=lambda j: j.id)
        return jobs, qm

    def prefix_list(self, prefix: str) -> tuple[list[JobListStub], QueryMeta]:
        from .api import QueryOptions

        return self.list(QueryOptions(prefix=prefix))

    def info(self, job_id: str, q: QueryOptions | None = None) -> tuple[Job, QueryMeta]:
        resp, qm = self._client.query(_path(job_id), q)
        return Job.from_json(resp), qm

    def scale(self, job_id: str, group: str, count: int | None = None, message: str = "", error: bool = False,
              meta: dict[str, Any] | None = None, w: WriteOptions | None = None) -> tuple[JobRegisterResponse, WriteMeta]:
        req = ScalingRequest(count=count, target={"Job": job_id, "Group": group}, error=error, message=message, meta=meta)
        return self.scale_with_request(job_id, req, w)

    def scale_with_request(self, job_id: str, req: ScalingRequest, w: WriteOptions | None = None) -> tuple[JobRegisterResponse, WriteMeta]:
        resp, wm = self._client.put(_path(job_id) + "/scale", req.to_json(), w)
        return JobRegisterResponse.from_json(resp), wm

    def scale_status(self, job_id: str, q: QueryOptions | None = None) -> tuple[JobScaleStatusResponse, QueryMeta]:
        resp, qm = self._client.query(_path(job_id) + "/scale", q)
        return JobScaleStatusResponse.from_json(resp), qm

    def versions(self, job_id: str, diffs: bool = False, q: QueryOptions | None = None, *, diff_tag: str = "",
                 diff_version: int | None = None) -> tuple[list[Job], list[JobDiff], QueryMeta]:
        endpoint = _path(job_id) + f"/versions?diffs={str(diffs).lower()}"
        if diff_tag:
            endpoint += "&diff_tag=" + quote(diff_tag, safe="")
        if diff_version is not None:
            endpoint += f"&diff_version={diff_version}"
        resp, qm = self._client.query(endpoint, q)
        versions = [Job.from_json(v) for v in resp["Versions"]]
        diffs = [JobDiff.from_json(d) for d in resp.get("Diffs") or []]
        return versions, diffs, qm

    def version_by_tag(self, job_id: str, tag: str, q: QueryOptions | None = None) -> tuple[Job, QueryMeta]:
        versions, _, qm = self.versions(job_id, False, q)
        for version in versions:
            if version.version_tag is not None and version.version_tag.name == tag:
                return version, qm
        raise LookupError(f"version tag {tag} not found for job {job_id}")

    def submission(self, job_id: str, version: int, q: QueryOptions | None = None) -> tuple[JobSubmission, QueryMeta]:
        resp, qm = self._client.query(_path(job_id) + f"/submission?version={version}", q)
        return JobSubmission.from_json(resp), qm

    def allocations(self, job_id: str, all_allocs: bool = False, q: QueryOptions | None = None) -> tuple[list[dict[str, Any]], QueryMeta]:
        resp, qm = self._client.query(_path(job_id) + f"/allocations?all={str(all_allocs).lower()}", q)
        resp.sort(key=lambda a: a["CreateIndex"], reverse=True)
        return resp, qm

    def deployments(self, job_id: str, all: bool = False, q: QueryOptions | None = None) -> tuple[list[Deployment], QueryMeta]:
        resp, qm = self._client.query(_path(job_id) + f"/deployments?all={str(all).lower()}", q)
        return _deployments(resp), qm

    def latest_deployment(self, job_id: str, q: QueryOptions | None = None) -> tuple[Deployment | None, QueryMeta]:
        resp, qm = self._client.query(_path(job_id) + "/deployment", q)
        return (Deployment.from_json(resp) if resp else None), qm

    def evaluations(self, job_id: str, q: QueryOptions | None = None) -> tuple[list[Evaluation], QueryMeta]:
        resp, qm = self._client.query(_path(job_id) + "/evaluations", q)
        evals = [Evaluation.from_json(e) for e in resp]
        evals.sort(key=lambda e: e.create_index, reverse=True)
        return evals, qm

    def deregister(self, job_id: str, purge: bool = False, w: WriteOptions | None = None, *, global_: bool = False,
                   eval_priority: int = 0, no_shutdown_delay: bool = False) -> tuple[str, WriteMeta]:
        endpoint = _path(job_id) + (f"?purge={str(purge).lower()}&global={str(global_).lower()}"
                                    f"&eval_priority={eval_priority}&no_shutdown_delay={str(no_shutdown_delay).lower()}")
        resp, wm = self._client.delete(endpoint, None, w)
        return resp["EvalID"], wm

    def force_evaluate(self, job_id: str, w: WriteOptions | None = None, *, force_reschedule: bool = False) -> tuple[str, WriteMeta]:
        req = {"JobID": job_id, "EvalOptions": {"ForceReschedule": force_reschedule}}
        resp, wm = self._client.put(_path(job_id) + "/evaluate", req, w)
        return resp["EvalID"], wm

    def periodic_force(self, job_id: str, w: WriteOptions | None = None) -> tuple[str, WriteMeta]:
        resp, wm = self._client.put(_path(job_id) + "/periodic/force", None, w)
        return resp["EvalID"], wm

    def plan(self, job: Job | dict[str, Any], diff: bool = False, w: WriteOptions | None = None, *, policy_override: bool = False) -> tuple[JobPlanResponse, WriteMeta]:
        body = _job_json(job)
        if not body.get("ID"):
            raise ValueError("job is missing ID")
        req = {"Job": body, "Diff": diff, "PolicyOverride": policy_override}
        resp, wm = self._client.put(_path(body["ID"]) + "/plan", req, w)
        return JobPlanResponse.from_json(resp), wm

    def summary(self, job_id: str, q: QueryOptions | None = None) -> tuple[JobSummary, QueryMeta]:
        resp, qm = self._client.query(_path(job_id) + "/summary", q)
        return JobSummary.from_json(resp), qm

    def dispatch(self, job_id: str, meta: dict[str, str] | None = None, payload: bytes | None = None,
                 id_prefix_template: str = "", w: WriteOptions | None = None, *, priority: int = 0) -> tuple[JobDispatchResponse, WriteMeta]:
        req: dict[str, Any] = {
            "JobID": job_id,
            "Meta": meta,
            # Go marshals []byte as base64.
            "Payload": base64.b64encode(payload).decode() if payload is not None else None,
            "IdPrefixTemplate": id_prefix_template,
            "Priority": priority,
        }
        resp, wm = self._client.put(_path(job_id) + "/dispatch", req, w)
        return JobDispatchResponse.from_json(resp), wm

    def revert(self, job_id: str, version: int, enforce_prior_version: int | None = None,
               w: WriteOptions | None = None) -> tuple[JobRegisterResponse, WriteMeta]:
        req = {"JobID": job_id, "JobVersion": version, "EnforcePriorVersion": enforce_prior_version}
        resp, wm = self._client.put(_path(job_id) + "/revert", req, w)
        return JobRegisterResponse.from_json(resp), wm

    def stable(self, job_id: str, version: int, stable: bool, w: WriteOptions | None = None) -> tuple[JobStabilityResponse, WriteMeta]:
        req = {"JobID": job_id, "JobVersion": version, "Stable": stable}
        resp, wm = self._client.put(_path(job_id) + "/stable", req, w)
        return JobStabilityResponse.from_json(resp), wm

    def services(self, job_id: str, q: QueryOptions | None = None) -> tuple[list[ServiceRegistration], QueryMeta]:
        resp, qm = self._client.query(_path(job_id) + "/services", q)
        return [ServiceRegistration.from_json(s) for s in resp], qm

    def tag_version(self, job_id: str, name: str, version: int = 0, description: str = "",
                    w: WriteOptions | None = None, *, latest: bool = False) -> WriteMeta:
        req = {"Version": version, "Latest": latest, "Description": description}
        _, wm = self._client.put(_path(job_id) + f"/versions/{name}/tag", req, w)
        return wm

    def untag_version(self, job_id: str, name: str, w: WriteOptions | None = None) -> WriteMeta:
        _, wm = self._client.delete(_path(job_id) + f"/versions/{name}/tag", None, w)
        return wm
