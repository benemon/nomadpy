from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta

ALLOC_DESIRED_STATUS_RUN = "run"
ALLOC_DESIRED_STATUS_STOP = "stop"
ALLOC_DESIRED_STATUS_EVICT = "evict"
ALLOC_CLIENT_STATUS_PENDING = "pending"
ALLOC_CLIENT_STATUS_RUNNING = "running"
ALLOC_CLIENT_STATUS_COMPLETE = "complete"
ALLOC_CLIENT_STATUS_FAILED = "failed"
ALLOC_CLIENT_STATUS_LOST = "lost"
ALLOC_CLIENT_STATUS_UNKNOWN = "unknown"
ALLOC_RESTART_REASON_WITHIN_POLICY = "Restart within policy"

# The full Allocation stays a dict; see the ledger.
Allocation = dict[str, Any]


@dataclass
class AllocDeploymentStatus(Model):
    healthy: bool | None = None
    timestamp: str = field(default="", metadata={"time": True})
    canary: bool = False
    modify_index: int = 0


@dataclass
class PortMapping(Model):
    label: str = ""
    value: int = 0
    to: int = 0
    host_ip: str = field(default="", metadata={"json": "HostIP"})


@dataclass
class AllocatedCpuResources(Model):
    cpu_shares: int = 0
    reserved_cores: list[int] | None = None


@dataclass
class AllocatedMemoryResources(Model):
    memory_mb: int = field(default=0, metadata={"json": "MemoryMB"})
    memory_max_mb: int = field(default=0, metadata={"json": "MemoryMaxMB"})


@dataclass
class AllocatedDeviceResource(Model):
    vendor: str = ""
    type: str = ""
    name: str = ""
    device_ids: list[str] | None = field(default=None, metadata={"json": "DeviceIDs"})


@dataclass
class AllocatedTaskResources(Model):
    cpu: AllocatedCpuResources = field(default_factory=AllocatedCpuResources)
    memory: AllocatedMemoryResources = field(default_factory=AllocatedMemoryResources)
    networks: list[dict[str, Any]] | None = None
    devices: list[AllocatedDeviceResource] | None = None


@dataclass
class AllocatedSharedResources(Model):
    disk_mb: int = field(default=0, metadata={"json": "DiskMB"})
    networks: list[dict[str, Any]] | None = None
    ports: list[PortMapping] | None = None


@dataclass
class AllocatedResources(Model):
    tasks: dict[str, AllocatedTaskResources] | None = None
    shared: AllocatedSharedResources = field(default_factory=AllocatedSharedResources)


@dataclass
class RescheduleEvent(Model):
    reschedule_time: int = 0
    prev_alloc_id: str = field(default="", metadata={"json": "PrevAllocID"})
    prev_node_id: str = field(default="", metadata={"json": "PrevNodeID"})


@dataclass
class RescheduleTracker(Model):
    events: list[RescheduleEvent] | None = None
    last_reschedule: str = ""


@dataclass
class AllocationListStub(Model):
    id: str = field(default="", metadata={"json": "ID"})
    eval_id: str = field(default="", metadata={"json": "EvalID"})
    name: str = ""
    namespace: str = ""
    node_id: str = field(default="", metadata={"json": "NodeID"})
    node_name: str = ""
    job_id: str = field(default="", metadata={"json": "JobID"})
    job_type: str = ""
    job_version: int = 0
    task_group: str = ""
    allocated_resources: AllocatedResources | None = field(default=None, metadata={"omitempty": True})
    desired_status: str = ""
    desired_description: str = ""
    client_status: str = ""
    client_description: str = ""
    task_states: dict[str, dict[str, Any]] | None = None
    deployment_status: AllocDeploymentStatus | None = None
    followup_eval_id: str = field(default="", metadata={"json": "FollowupEvalID"})
    next_allocation: str = ""
    reschedule_tracker: RescheduleTracker | None = None
    preempted_allocations: list[str] | None = None
    preempted_by_allocation: str = ""
    create_index: int = 0
    modify_index: int = 0
    create_time: int = 0
    modify_time: int = 0


@dataclass
class AllocStopResponse(Model):
    eval_id: str = field(default="", metadata={"json": "EvalID"})


def _stubs(resp: list[dict[str, Any]]) -> list[AllocationListStub]:
    stubs = [AllocationListStub.from_json(a) for a in resp]
    stubs.sort(key=lambda a: a.create_index, reverse=True)
    return stubs


class Allocations:
    """Allocations queries the allocation endpoints. Methods that act on an allocation take its ID, where Go takes the Allocation."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[AllocationListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/allocations", q)
        return _stubs(resp), qm

    def prefix_list(self, prefix: str) -> tuple[list[AllocationListStub], QueryMeta]:
        from .api import QueryOptions

        return self.list(QueryOptions(prefix=prefix))

    def info(self, alloc_id: str, q: QueryOptions | None = None) -> tuple[Allocation, QueryMeta]:
        return self._client.query(f"/v1/allocation/{alloc_id}", q)

    def stats(self, alloc_id: str, q: QueryOptions | None = None) -> dict[str, Any]:
        resp, _ = self._client.query(f"/v1/client/allocation/{alloc_id}/stats", q)
        return resp

    def checks(self, alloc_id: str, q: QueryOptions | None = None) -> dict[str, dict[str, Any]]:
        resp, _ = self._client.query(f"/v1/client/allocation/{alloc_id}/checks", q)
        return resp or {}

    def gc(self, alloc_id: str, q: QueryOptions | None = None) -> None:
        self._client.query(f"/v1/client/allocation/{alloc_id}/gc")

    def restart(self, alloc_id: str, task_name: str = "", q: QueryOptions | None = None) -> None:
        self._client.put_query(f"/v1/client/allocation/{alloc_id}/restart", {"TaskName": task_name, "AllTasks": False}, q)

    def restart_all_tasks(self, alloc_id: str, q: QueryOptions | None = None) -> None:
        self._client.put_query(f"/v1/client/allocation/{alloc_id}/restart", {"TaskName": "", "AllTasks": True}, q)

    def stop(self, alloc_id: str, q: QueryOptions | None = None) -> tuple[AllocStopResponse, QueryMeta]:
        resp, qm = self._client.put_query(f"/v1/allocation/{alloc_id}/stop", None, q)
        return AllocStopResponse.from_json(resp), qm

    def signal(self, alloc_id: str, task: str, signal: str, q: QueryOptions | None = None) -> None:
        self._client.put_query(f"/v1/client/allocation/{alloc_id}/signal", {"Task": task, "Signal": signal}, q)

    def set_pause_state(self, alloc_id: str, task: str, state: str, q: QueryOptions | None = None) -> None:
        self._client.put_query(f"/v1/client/allocation/{alloc_id}/pause", {"Task": task, "ScheduleState": state}, q)

    def get_pause_state(self, alloc_id: str, task: str, q: QueryOptions | None = None) -> tuple[str, QueryMeta]:
        resp, qm = self._client.query(f"/v1/client/allocation/{alloc_id}/pause?task={task}", q)
        return resp.get("ScheduleState", ""), qm

    def services(self, alloc_id: str, q: QueryOptions | None = None) -> tuple[list[dict[str, Any]], QueryMeta]:
        return self._client.query(f"/v1/allocation/{alloc_id}/services", q)
