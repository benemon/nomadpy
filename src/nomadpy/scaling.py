from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions

SCALING_POLICY_TYPE_HORIZONTAL = "horizontal"


@dataclass
class ScalingRequest(Model):
    count: int | None = None
    target: dict[str, str] | None = None
    message: str = ""
    error: bool = False
    meta: dict[str, Any] | None = None
    policy_override: bool = False
    job_modify_index: int = 0


@dataclass
class ScalingPolicy(Model):
    """ScalingPolicy; vertical policy types are Enterprise (Dynamic Application Sizing)."""

    min: int | None = None
    max: int | None = None
    policy: dict[str, Any] | None = None
    enabled: bool | None = None
    type: str = ""
    id: str = field(default="", metadata={"json": "ID"})
    namespace: str = ""
    target: dict[str, str] | None = None
    create_index: int = 0
    modify_index: int = 0

    def canonicalize(self, task_group_count: int) -> None:
        if self.enabled is None:
            self.enabled = True
        if self.min is None:
            self.min = task_group_count
        if not self.type:
            self.type = SCALING_POLICY_TYPE_HORIZONTAL


@dataclass
class ScalingPolicyListStub(Model):
    id: str = field(default="", metadata={"json": "ID"})
    enabled: bool = False
    type: str = ""
    target: dict[str, str] | None = None
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ScalingEvent(Model):
    count: int | None = None
    previous_count: int = 0
    error: bool = False
    message: str = ""
    meta: dict[str, Any] | None = None
    eval_id: str | None = field(default=None, metadata={"json": "EvalID"})
    time: int = 0
    create_index: int = 0


@dataclass
class TaskGroupScaleStatus(Model):
    desired: int = 0
    placed: int = 0
    running: int = 0
    healthy: int = 0
    unhealthy: int = 0
    events: list[ScalingEvent] | None = None


@dataclass
class JobScaleStatusResponse(Model):
    job_id: str = field(default="", metadata={"json": "JobID"})
    namespace: str = ""
    job_create_index: int = 0
    job_modify_index: int = 0
    job_stopped: bool = False
    task_groups: dict[str, TaskGroupScaleStatus] | None = None


class Scaling:
    """Scaling queries the scaling policy endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list_policies(self, q: QueryOptions | None = None) -> tuple[list[ScalingPolicyListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/scaling/policies", q)
        return [ScalingPolicyListStub.from_json(p) for p in resp], qm

    def get_policy(self, id: str, q: QueryOptions | None = None) -> tuple[ScalingPolicy, QueryMeta]:
        resp, qm = self._client.query("/v1/scaling/policy/" + quote(id, safe=""), q)
        return ScalingPolicy.from_json(resp), qm
