from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .api import QueryOptions
from .models import Model
from .services import ServiceRegistration

if TYPE_CHECKING:
    from .api import Client, QueryMeta, WriteMeta

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
    task_states: dict[str, _tasks.TaskState] | None = None
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


class DesiredTransitionMethods:
    def should_migrate(self) -> bool:
        return bool(self.migrate)

    def should_reschedule(self) -> bool:
        return bool(self.reschedule)

    def should_ignore_shutdown_delay(self) -> bool:
        return bool(self.no_shutdown_delay)

    def should_force_reschedule(self) -> bool:
        return bool(self.force_reschedule)

    def should_disable_migration_placement(self) -> bool:
        return bool(self.migrate_disable_placement)


class AllocationMethods:
    def stub(self) -> AllocationListStub:
        stub = AllocationListStub(
            id=self.id, eval_id=self.eval_id, name=self.name, namespace=self.namespace, node_id=self.node_id, node_name=self.node_name,
            job_id=self.job_id, task_group=self.task_group, desired_status=self.desired_status, desired_description=self.desired_description,
            client_status=self.client_status, client_description=self.client_description, task_states=self.task_states,
            deployment_status=self.deployment_status, followup_eval_id=self.followup_eval_id, next_allocation=self.next_allocation,
            reschedule_tracker=self.reschedule_tracker, preempted_allocations=self.preempted_allocations,
            preempted_by_allocation=self.preempted_by_allocation, create_index=self.create_index, modify_index=self.modify_index,
            create_time=self.create_time, modify_time=self.modify_time)
        if self.job is not None:
            stub.job_type = self.job.type or ""
            stub.job_version = self.job.version or 0
        return stub

    def get_task_group(self) -> _tasks.TaskGroup | None:
        for tg in (self.job.task_groups if self.job else None) or []:
            if tg.name == self.task_group:
                return tg
        return None

    def reschedule_info(self, t: int) -> tuple[int, int]:
        """reschedule_info returns (attempted, available) reschedule attempts within the policy interval at Unix nanosecond time t."""
        tg = self.get_task_group()
        if tg is None or tg.reschedule_policy is None:
            return 0, 0
        available = tg.reschedule_policy.attempts or 0
        interval = tg.reschedule_policy.interval or 0
        attempted = 0
        if self.reschedule_tracker is not None and available > 0 and interval > 0:
            for event in reversed(self.reschedule_tracker.events or []):
                if t - event.reschedule_time < interval:
                    attempted += 1
        return attempted, available

    def server_terminal_status(self) -> bool:
        return self.desired_status in (ALLOC_DESIRED_STATUS_STOP, ALLOC_DESIRED_STATUS_EVICT)

    def client_terminal_status(self) -> bool:
        return self.client_status in (ALLOC_CLIENT_STATUS_COMPLETE, ALLOC_CLIENT_STATUS_FAILED, ALLOC_CLIENT_STATUS_LOST)


# generated from surface.json: file=allocations.go only=Allocation,AllocationMetric,NodeScoreMeta,AllocNetworkStatus,DesiredTransition mixins=Allocation:AllocationMethods,DesiredTransition:DesiredTransitionMethods
from . import jobs as _jobs  # noqa: E402
from . import resources as _resources  # noqa: E402
from . import tasks as _tasks  # noqa: E402

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


@dataclass
class AllocNetworkStatus(Model):
    interface_name: str = ""
    address: str = ""
    address_i_pv6: str = ""
    dns: _resources.DNSConfig | None = field(default=None, metadata={'json': 'DNS'})


@dataclass
class AllocationMetric(Model):
    nodes_evaluated: int = 0
    nodes_filtered: int = 0
    nodes_in_pool: int = 0
    node_pool: str = ""
    nodes_available: dict[str, int] | None = None
    class_filtered: dict[str, int] | None = None
    constraint_filtered: dict[str, int] | None = None
    nodes_exhausted: int = 0
    class_exhausted: dict[str, int] | None = None
    dimension_exhausted: dict[str, int] | None = None
    quota_exhausted: list[str] | None = None
    resources_exhausted: dict[str, _resources.Resources] | None = None
    scores: dict[str, float] | None = None
    allocation_time: int = 0
    coalesced_failures: int = 0
    score_meta_data: list[NodeScoreMeta] | None = None


@dataclass
class DesiredTransition(DesiredTransitionMethods, Model):
    migrate: bool | None = None
    reschedule: bool | None = None
    force_reschedule: bool | None = None
    no_shutdown_delay: bool | None = None
    migrate_disable_placement: bool | None = None


@dataclass
class NodeScoreMeta(Model):
    node_id: str = field(default="", metadata={'json': 'NodeID'})
    scores: dict[str, float] | None = None
    norm_score: float = 0.0


@dataclass
class Allocation(AllocationMethods, Model):
    id: str = field(default="", metadata={'json': 'ID'})
    namespace: str = ""
    eval_id: str = field(default="", metadata={'json': 'EvalID'})
    name: str = ""
    node_id: str = field(default="", metadata={'json': 'NodeID'})
    node_name: str = ""
    job_id: str = field(default="", metadata={'json': 'JobID'})
    job: _jobs.Job | None = None
    task_group: str = ""
    resources: _resources.Resources | None = None
    task_resources: dict[str, _resources.Resources] | None = None
    allocated_resources: AllocatedResources | None = None
    services: dict[str, str] | None = None
    metrics: AllocationMetric | None = None
    desired_status: str = ""
    desired_description: str = ""
    desired_transition: DesiredTransition = field(default_factory=DesiredTransition)
    client_status: str = ""
    client_description: str = ""
    task_states: dict[str, _tasks.TaskState] | None = None
    deployment_id: str = field(default="", metadata={'json': 'DeploymentID'})
    deployment_status: AllocDeploymentStatus | None = None
    followup_eval_id: str = field(default="", metadata={'json': 'FollowupEvalID'})
    previous_allocation: str = ""
    next_allocation: str = ""
    reschedule_tracker: RescheduleTracker | None = None
    network_status: AllocNetworkStatus | None = None
    preempted_allocations: list[str] | None = None
    preempted_by_allocation: str = ""
    create_index: int = 0
    modify_index: int = 0
    alloc_modify_index: int = 0
    create_time: int = 0
    modify_time: int = 0


# end generated


def stubs(resp: list[dict[str, Any]]) -> list[AllocationListStub]:
    """stubs decodes a list response into AllocationListStub, newest first."""
    stubs = [AllocationListStub.from_json(a) for a in resp]
    stubs.sort(key=lambda a: a.create_index, reverse=True)
    return stubs


class Allocations:
    """Allocations queries the allocation endpoints. Methods that act on an allocation take its ID, where Go takes the Allocation."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[AllocationListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/allocations", q)
        return stubs(resp), qm

    def prefix_list(self, prefix: str) -> tuple[list[AllocationListStub], QueryMeta]:
        return self.list(QueryOptions(prefix=prefix))

    def info(self, alloc_id: str, q: QueryOptions | None = None) -> tuple[Allocation, QueryMeta]:
        resp, qm = self._client.query(f"/v1/allocation/{alloc_id}", q)
        return Allocation.from_json(resp), qm

    def stats(self, alloc_id: str, q: QueryOptions | None = None) -> _tasks.AllocResourceUsage:
        resp, _ = self._client.query(f"/v1/client/allocation/{alloc_id}/stats", q)
        return _tasks.AllocResourceUsage.from_json(resp)

    def checks(self, alloc_id: str, q: QueryOptions | None = None) -> dict[str, _tasks.AllocCheckStatus]:
        resp, _ = self._client.query(f"/v1/client/allocation/{alloc_id}/checks", q)
        return {k: _tasks.AllocCheckStatus.from_json(v) for k, v in (resp or {}).items()}

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

    def services(self, alloc_id: str, q: QueryOptions | None = None) -> tuple[list[ServiceRegistration], QueryMeta]:
        resp, qm = self._client.query(f"/v1/allocation/{alloc_id}/services", q)
        return [ServiceRegistration.from_json(s) for s in resp], qm
