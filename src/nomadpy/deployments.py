from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .models import Model
from . import allocations as _allocations

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions

DEPLOYMENT_STATUS_RUNNING = "running"
DEPLOYMENT_STATUS_PAUSED = "paused"
DEPLOYMENT_STATUS_FAILED = "failed"
DEPLOYMENT_STATUS_SUCCESSFUL = "successful"
DEPLOYMENT_STATUS_CANCELLED = "cancelled"
DEPLOYMENT_STATUS_PENDING = "pending"
DEPLOYMENT_STATUS_BLOCKED = "blocked"
DEPLOYMENT_STATUS_UNBLOCKING = "unblocking"


@dataclass
class DeploymentState(Model):
    placed_canaries: list[str] | None = None
    auto_revert: bool = False
    progress_deadline: int = 0
    require_progress_by: str = field(default="", metadata={"time": True})
    promoted: bool = False
    desired_canaries: int = 0
    desired_total: int = 0
    placed_allocs: int = 0
    healthy_allocs: int = 0
    unhealthy_allocs: int = 0


@dataclass
class Deployment(Model):
    id: str = field(default="", metadata={"json": "ID"})
    namespace: str = ""
    job_id: str = field(default="", metadata={"json": "JobID"})
    job_version: int = 0
    job_modify_index: int = 0
    job_spec_modify_index: int = 0
    job_create_index: int = 0
    is_multiregion: bool = False
    task_groups: dict[str, DeploymentState] = field(default_factory=dict)
    status: str = ""
    status_description: str = ""
    create_index: int = 0
    modify_index: int = 0
    create_time: int = 0
    modify_time: int = 0


@dataclass
class DeploymentUpdateResponse(Model):
    eval_id: str = field(default="", metadata={"json": "EvalID"})
    eval_create_index: int = 0
    deployment_modify_index: int = 0
    reverted_job_version: int | None = None


def _deployments(resp: list[dict[str, Any]]) -> list[Deployment]:
    deployments = [Deployment.from_json(d) for d in resp]
    deployments.sort(key=lambda d: d.create_index, reverse=True)
    return deployments


class Deployments:
    """Deployments queries the deployment endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[Deployment], QueryMeta]:
        resp, qm = self._client.query("/v1/deployments", q)
        return _deployments(resp), qm

    def prefix_list(self, prefix: str) -> tuple[list[Deployment], QueryMeta]:
        from .api import QueryOptions

        return self.list(QueryOptions(prefix=prefix))

    def info(self, deployment_id: str, q: QueryOptions | None = None) -> tuple[Deployment, QueryMeta]:
        resp, qm = self._client.query(f"/v1/deployment/{deployment_id}", q)
        return Deployment.from_json(resp), qm

    def allocations(self, deployment_id: str, q: QueryOptions | None = None) -> tuple[list[_allocations.AllocationListStub], QueryMeta]:
        resp, qm = self._client.query(f"/v1/deployment/allocations/{deployment_id}", q)
        return _allocations._stubs(resp), qm

    def fail(self, deployment_id: str, w: WriteOptions | None = None) -> tuple[DeploymentUpdateResponse, WriteMeta]:
        return self._update("fail", deployment_id, {"DeploymentID": deployment_id}, w)

    def pause(self, deployment_id: str, pause: bool, w: WriteOptions | None = None) -> tuple[DeploymentUpdateResponse, WriteMeta]:
        return self._update("pause", deployment_id, {"DeploymentID": deployment_id, "Pause": pause}, w)

    def promote_all(self, deployment_id: str, w: WriteOptions | None = None) -> tuple[DeploymentUpdateResponse, WriteMeta]:
        return self._update("promote", deployment_id, {"DeploymentID": deployment_id, "All": True}, w)

    def promote_groups(self, deployment_id: str, groups: list[str], w: WriteOptions | None = None) -> tuple[DeploymentUpdateResponse, WriteMeta]:
        return self._update("promote", deployment_id, {"DeploymentID": deployment_id, "Groups": groups}, w)

    def unblock(self, deployment_id: str, w: WriteOptions | None = None) -> tuple[DeploymentUpdateResponse, WriteMeta]:
        return self._update("unblock", deployment_id, {"DeploymentID": deployment_id}, w)

    def set_alloc_health(self, deployment_id: str, healthy: list[str], unhealthy: list[str], w: WriteOptions | None = None) -> tuple[DeploymentUpdateResponse, WriteMeta]:
        req = {"DeploymentID": deployment_id, "HealthyAllocationIDs": healthy, "UnhealthyAllocationIDs": unhealthy}
        return self._update("allocation-health", deployment_id, req, w)

    def _update(self, action: str, deployment_id: str, req: dict[str, Any], w: WriteOptions | None) -> tuple[DeploymentUpdateResponse, WriteMeta]:
        resp, wm = self._client.put(f"/v1/deployment/{action}/{deployment_id}", req, w)
        return DeploymentUpdateResponse.from_json(resp), wm
