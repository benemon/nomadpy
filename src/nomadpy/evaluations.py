from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .api import QueryOptions
from .models import Model
from . import allocations as _allocations

if TYPE_CHECKING:
    from .api import Client, QueryMeta, WriteMeta, WriteOptions

EVAL_STATUS_BLOCKED = "blocked"
EVAL_STATUS_PENDING = "pending"
EVAL_STATUS_COMPLETE = "complete"
EVAL_STATUS_FAILED = "failed"
EVAL_STATUS_CANCELLED = "canceled"


@dataclass
class EvaluationStub(Model):
    id: str = field(default="", metadata={"json": "ID"})
    priority: int = 0
    type: str = ""
    triggered_by: str = ""
    namespace: str = ""
    job_id: str = field(default="", metadata={"json": "JobID"})
    node_id: str = field(default="", metadata={"json": "NodeID"})
    deployment_id: str = field(default="", metadata={"json": "DeploymentID"})
    status: str = ""
    status_description: str = ""
    wait_until: str = field(default="", metadata={"time": True})
    next_eval: str = ""
    previous_eval: str = ""
    blocked_eval: str = ""
    create_index: int = 0
    modify_index: int = 0
    create_time: int = 0
    modify_time: int = 0


@dataclass
class Evaluation(Model):
    id: str = field(default="", metadata={"json": "ID"})
    priority: int = 0
    type: str = ""
    triggered_by: str = ""
    namespace: str = ""
    job_id: str = field(default="", metadata={"json": "JobID"})
    job_modify_index: int = 0
    node_id: str = field(default="", metadata={"json": "NodeID"})
    node_modify_index: int = 0
    deployment_id: str = field(default="", metadata={"json": "DeploymentID"})
    status: str = ""
    status_description: str = ""
    wait: int = 0
    wait_until: str = field(default="", metadata={"time": True})
    next_eval: str = ""
    previous_eval: str = ""
    blocked_eval: str = ""
    related_evals: list[EvaluationStub] | None = None
    failed_tg_allocs: dict[str, Any] | None = field(default=None, metadata={"json": "FailedTGAllocs"})
    plan_annotations: dict[str, Any] | None = None
    class_eligibility: dict[str, bool] | None = None
    escaped_computed_class: bool = False
    quota_limit_reached: str = ""
    missing_non_node_resources: list[str] | None = None
    annotate_plan: bool = False
    queued_allocations: dict[str, int] | None = None
    snapshot_index: int = 0
    create_index: int = 0
    modify_index: int = 0
    create_time: int = 0
    modify_time: int = 0


class Evaluations:
    """Evaluations queries the evaluation endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[Evaluation], QueryMeta]:
        resp, qm = self._client.query("/v1/evaluations", q)
        evals = [Evaluation.from_json(e) for e in resp]
        evals.sort(key=lambda e: e.create_index, reverse=True)
        return evals, qm

    def prefix_list(self, prefix: str) -> tuple[list[Evaluation], QueryMeta]:
        return self.list(QueryOptions(prefix=prefix))

    def count(self, q: QueryOptions | None = None) -> tuple[int, QueryMeta]:
        resp, qm = self._client.query("/v1/evaluations/count", q)
        return resp["Count"], qm

    def info(self, eval_id: str, q: QueryOptions | None = None) -> tuple[Evaluation, QueryMeta]:
        resp, qm = self._client.query(f"/v1/evaluation/{eval_id}?related=true", q)
        return Evaluation.from_json(resp), qm

    def delete(self, eval_ids: list[str] | None = None, w: WriteOptions | None = None, *, filter: str = "") -> tuple[int, WriteMeta]:
        """delete removes evaluations by ID or by filter and returns the number deleted. The eval broker must be paused."""
        req: dict[str, Any] = {"EvalIDs": eval_ids or []}
        if filter:
            req["Filter"] = filter
        resp, wm = self._client.delete("/v1/evaluations", req, w)
        return resp["Count"], wm

    def allocations(self, eval_id: str, q: QueryOptions | None = None) -> tuple[list[_allocations.AllocationListStub], QueryMeta]:
        resp, qm = self._client.query(f"/v1/evaluation/{eval_id}/allocations", q)
        return _allocations.stubs(resp), qm
