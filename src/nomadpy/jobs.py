from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .deployments import Deployment, _deployments
from .evaluations import Evaluation
from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions

# The job itself is a plain dict in the shape the HTTP API documents; the
# typed Job struct is a separate piece of work.
Job = dict[str, Any]

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
    namespace: str = ""
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
    meta: dict[str, str] | None = None


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
    diff: dict[str, Any] | None = None
    annotations: dict[str, Any] | None = None
    failed_tg_allocs: dict[str, Any] | None = field(default=None, metadata={"json": "FailedTGAllocs"})
    next_periodic_launch: str = ""
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


class Jobs:
    """Jobs queries the job endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def parse_hcl(self, job_hcl: str, canonicalize: bool = False, *, variables: str = "") -> Job:
        """parse_hcl converts an HCL job specification to its JSON form using the server."""
        req = {"JobHCL": job_hcl, "Canonicalize": canonicalize, "Variables": variables}
        resp, _ = self._client.put("/v1/jobs/parse", req)
        return resp

    def validate(self, job: Job, w: WriteOptions | None = None) -> tuple[JobValidateResponse, WriteMeta]:
        req: dict[str, Any] = {"Job": job}
        if w is not None and w.region:
            req["Region"] = w.region
        resp, wm = self._client.put("/v1/validate/job", req, w)
        return JobValidateResponse.from_json(resp), wm

    def register(self, job: Job, w: WriteOptions | None = None, *, enforce_index: bool = False, modify_index: int = 0,
                 policy_override: bool = False, preserve_counts: bool = False, preserve_resources: bool = False,
                 eval_priority: int = 0, submission: dict[str, Any] | None = None) -> tuple[JobRegisterResponse, WriteMeta]:
        req: dict[str, Any] = {"Job": job}
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
            req["Submission"] = submission
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
        return self._client.query(_path(job_id), q)

    def scale(self, job_id: str, group: str, count: int | None = None, message: str = "", error: bool = False,
              meta: dict[str, Any] | None = None, w: WriteOptions | None = None) -> tuple[JobRegisterResponse, WriteMeta]:
        req = {"Count": count, "Target": {"Job": job_id, "Group": group}, "Error": error, "Message": message, "Meta": meta}
        resp, wm = self._client.put(_path(job_id) + "/scale", req, w)
        return JobRegisterResponse.from_json(resp), wm

    def scale_status(self, job_id: str, q: QueryOptions | None = None) -> tuple[dict[str, Any], QueryMeta]:
        return self._client.query(_path(job_id) + "/scale", q)

    def versions(self, job_id: str, diffs: bool = False, q: QueryOptions | None = None, *, diff_tag: str = "",
                 diff_version: int | None = None) -> tuple[list[Job], list[dict[str, Any]], QueryMeta]:
        endpoint = _path(job_id) + f"/versions?diffs={str(diffs).lower()}"
        if diff_tag:
            endpoint += "&diff_tag=" + quote(diff_tag, safe="")
        if diff_version is not None:
            endpoint += f"&diff_version={diff_version}"
        resp, qm = self._client.query(endpoint, q)
        return resp["Versions"], resp.get("Diffs") or [], qm

    def version_by_tag(self, job_id: str, tag: str, q: QueryOptions | None = None) -> tuple[Job, QueryMeta]:
        versions, _, qm = self.versions(job_id, False, q)
        for version in versions:
            if (version.get("VersionTag") or {}).get("Name") == tag:
                return version, qm
        raise LookupError(f"version tag {tag} not found for job {job_id}")

    def submission(self, job_id: str, version: int, q: QueryOptions | None = None) -> tuple[dict[str, Any], QueryMeta]:
        return self._client.query(_path(job_id) + f"/submission?version={version}", q)

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

    def plan(self, job: Job, diff: bool = False, w: WriteOptions | None = None, *, policy_override: bool = False) -> tuple[JobPlanResponse, WriteMeta]:
        if not job.get("ID"):
            raise ValueError("job is missing ID")
        req = {"Job": job, "Diff": diff, "PolicyOverride": policy_override}
        resp, wm = self._client.put(_path(job["ID"]) + "/plan", req, w)
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

    def services(self, job_id: str, q: QueryOptions | None = None) -> tuple[list[dict[str, Any]], QueryMeta]:
        return self._client.query(_path(job_id) + "/services", q)

    def tag_version(self, job_id: str, name: str, version: int = 0, description: str = "",
                    w: WriteOptions | None = None, *, latest: bool = False) -> WriteMeta:
        req = {"Version": version, "Latest": latest, "Description": description}
        _, wm = self._client.put(_path(job_id) + f"/versions/{name}/tag", req, w)
        return wm

    def untag_version(self, job_id: str, name: str, w: WriteOptions | None = None) -> WriteMeta:
        _, wm = self._client.delete(_path(job_id) + f"/versions/{name}/tag", None, w)
        return wm
