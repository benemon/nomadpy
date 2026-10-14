from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .models import Model
from .node_identity import NodeIdentity
from .node_meta import NodeMeta
from . import resources as _resources

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions

NODE_STATUS_INIT = "initializing"
NODE_STATUS_READY = "ready"
NODE_STATUS_DOWN = "down"
NODE_STATUS_DISCONNECTED = "disconnected"
NODE_SCHEDULING_ELIGIBLE = "eligible"
NODE_SCHEDULING_INELIGIBLE = "ineligible"
DRAIN_STATUS_DRAINING = "draining"
DRAIN_STATUS_COMPLETE = "complete"
DRAIN_STATUS_CANCELED = "canceled"
NODE_EVENT_SUBSYSTEM_DRAIN = "Drain"
NODE_EVENT_SUBSYSTEM_DRIVER = "Driver"
NODE_EVENT_SUBSYSTEM_HEARTBEAT = "Heartbeat"
NODE_EVENT_SUBSYSTEM_CLUSTER = "Cluster"
MONITOR_MSG_LEVEL_NORMAL = 0
MONITOR_MSG_LEVEL_INFO = 1
MONITOR_MSG_LEVEL_WARN = 2
MONITOR_MSG_LEVEL_ERROR = 3



@dataclass
class DriverInfo(Model):
    attributes: dict[str, str] | None = None
    detected: bool = False
    healthy: bool = False
    health_description: str = ""
    update_time: str = field(default="", metadata={"time": True})


@dataclass
class DrainMetadata(Model):
    started_at: str = field(default="", metadata={"time": True})
    updated_at: str = field(default="", metadata={"time": True})
    status: str = ""
    accessor_id: str = field(default="", metadata={"json": "AccessorID"})
    meta: dict[str, str] | None = None


@dataclass
class NodeCpuResources(Model):
    cpu_shares: int = 0
    total_cpu_cores: int = 0
    reservable_cpu_cores: list[int] | None = None


@dataclass
class NodeMemoryResources(Model):
    memory_mb: int = field(default=0, metadata={"json": "MemoryMB"})


@dataclass
class NodeDiskResources(Model):
    disk_mb: int = field(default=0, metadata={"json": "DiskMB"})


@dataclass
class NodeResources(Model):
    cpu: NodeCpuResources = field(default_factory=NodeCpuResources)
    memory: NodeMemoryResources = field(default_factory=NodeMemoryResources)
    disk: NodeDiskResources = field(default_factory=NodeDiskResources)
    networks: list[dict[str, Any]] | None = None
    devices: list[dict[str, Any]] | None = None
    min_dynamic_port: int = 0
    max_dynamic_port: int = 0


@dataclass
class NodeReservedCpuResources(Model):
    cpu_shares: int = 0


@dataclass
class NodeReservedMemoryResources(Model):
    memory_mb: int = field(default=0, metadata={"json": "MemoryMB"})


@dataclass
class NodeReservedDiskResources(Model):
    disk_mb: int = field(default=0, metadata={"json": "DiskMB"})


@dataclass
class NodeReservedNetworkResources(Model):
    reserved_host_ports: str = ""


@dataclass
class NodeReservedResources(Model):
    cpu: NodeReservedCpuResources = field(default_factory=NodeReservedCpuResources)
    memory: NodeReservedMemoryResources = field(default_factory=NodeReservedMemoryResources)
    disk: NodeReservedDiskResources = field(default_factory=NodeReservedDiskResources)
    networks: NodeReservedNetworkResources = field(default_factory=NodeReservedNetworkResources)


@dataclass
class NodeListStub(Model):
    address: str = ""
    id: str = field(default="", metadata={"json": "ID"})
    attributes: dict[str, str] | None = field(default=None, metadata={"omitempty": True})
    datacenter: str = ""
    name: str = ""
    node_class: str = ""
    node_pool: str = ""
    version: str = ""
    drain: bool = False
    scheduling_eligibility: str = ""
    status: str = ""
    status_description: str = ""
    drivers: dict[str, DriverInfo] | None = None
    node_resources: NodeResources | None = field(default=None, metadata={"omitempty": True})
    reserved_resources: NodeReservedResources | None = field(default=None, metadata={"omitempty": True})
    last_drain: DrainMetadata | None = None
    create_index: int = 0
    modify_index: int = 0


@dataclass
class CSIControllerInfo(Model):
    supports_create_delete: bool = False
    supports_attach_detach: bool = False
    supports_list_volumes: bool = False
    supports_get_capacity: bool = False
    supports_create_delete_snapshot: bool = False
    supports_list_snapshots: bool = False
    supports_clone: bool = False
    supports_read_only_attach: bool = False
    supports_expand: bool = False
    supports_list_volumes_attached_nodes: bool = False
    supports_condition: bool = False
    supports_get: bool = False


@dataclass
class CSIInfo(Model):
    plugin_id: str = field(default="", metadata={'json': 'PluginID'})
    alloc_id: str = field(default="", metadata={'json': 'AllocID'})
    healthy: bool = False
    health_description: str = ""
    update_time: str = field(default="", metadata={'time': True})
    requires_controller_plugin: bool = False
    requires_topologies: bool = False
    controller_info: CSIControllerInfo | None = field(default=None, metadata={'omitempty': True})
    node_info: CSINodeInfo | None = field(default=None, metadata={'omitempty': True})


@dataclass
class CSINodeInfo(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    max_volumes: int = 0
    accessible_topology: CSITopology | None = None
    requires_node_stage_volume: bool = False
    supports_stats: bool = False
    supports_expand: bool = False
    supports_condition: bool = False


@dataclass
class CSITopology(Model):
    segments: dict[str, str] | None = None


@dataclass
class CSITopologyRequest(Model):
    required: list[CSITopology] | None = None
    preferred: list[CSITopology] | None = None


@dataclass
class DeviceGroupStats(Model):
    vendor: str = ""
    type: str = ""
    name: str = ""
    instance_stats: dict[str, DeviceStats] | None = None


@dataclass
class DeviceStats(Model):
    summary: StatValue | None = None
    stats: StatObject | None = None
    timestamp: str = field(default="", metadata={'time': True})


@dataclass
class HostCPUStats(Model):
    cpu: str = field(default="", metadata={'json': 'CPU'})
    user: float = 0.0
    system: float = 0.0
    idle: float = 0.0


@dataclass
class HostDiskStats(Model):
    device: str = ""
    mountpoint: str = ""
    size: int = 0
    used: int = 0
    available: int = 0
    used_percent: float = 0.0
    inodes_used_percent: float = 0.0


@dataclass
class HostMemoryStats(Model):
    total: int = 0
    available: int = 0
    used: int = 0
    free: int = 0


@dataclass
class HostNetworkInfo(Model):
    name: str = ""
    cidr: str = field(default="", metadata={'json': 'CIDR'})
    interface: str = ""
    reserved_ports: str = ""


@dataclass
class HostStats(Model):
    memory: HostMemoryStats | None = None
    cpu: list[HostCPUStats] | None = field(default=None, metadata={'json': 'CPU'})
    disk_stats: list[HostDiskStats] | None = None
    alloc_dir_stats: HostDiskStats | None = None
    device_stats: list[DeviceGroupStats] | None = None
    uptime: int = 0
    cpu_ticks_consumed: float = field(default=0.0, metadata={'json': 'CPUTicksConsumed'})


@dataclass
class HostVolumeInfo(Model):
    path: str = ""
    read_only: bool = False
    id: str = field(default="", metadata={'json': 'ID'})


@dataclass
class Node(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    datacenter: str = ""
    name: str = ""
    http_addr: str = field(default="", metadata={'json': 'HTTPAddr'})
    tls_enabled: bool = field(default=False, metadata={'json': 'TLSEnabled'})
    attributes: dict[str, str] | None = None
    resources: _resources.Resources | None = None
    reserved: _resources.Resources | None = None
    node_resources: NodeResources | None = None
    reserved_resources: NodeReservedResources | None = None
    links: dict[str, str] | None = None
    meta: dict[str, str] | None = None
    node_class: str = ""
    node_pool: str = ""
    cgroup_parent: str = ""
    drain: bool = False
    drain_strategy: DrainStrategy | None = None
    scheduling_eligibility: str = ""
    status: str = ""
    status_description: str = ""
    status_updated_at: int = 0
    events: list[NodeEvent] | None = None
    drivers: dict[str, DriverInfo] | None = None
    host_volumes: dict[str, HostVolumeInfo] | None = None
    gc_volumes_on_node_gc: bool = field(default=False, metadata={'json': 'GCVolumesOnNodeGC'})
    host_networks: dict[str, HostNetworkInfo] | None = None
    csi_controller_plugins: dict[str, CSIInfo] | None = field(default=None, metadata={'json': 'CSIControllerPlugins'})
    csi_node_plugins: dict[str, CSIInfo] | None = field(default=None, metadata={'json': 'CSINodePlugins'})
    last_drain: DrainMetadata | None = None
    create_index: int = 0
    modify_index: int = 0
    node_max_allocs: int = 0


@dataclass
class NodeEvent(Model):
    message: str = ""
    subsystem: str = ""
    details: dict[str, str] | None = None
    timestamp: str = field(default="", metadata={'time': True})
    create_index: int = 0


@dataclass
class StatObject(Model):
    nested: dict[str, StatObject] | None = None
    attributes: dict[str, StatValue] | None = None


@dataclass
class StatValue(Model):
    float_numerator_val: float | None = field(default=None, metadata={'omitempty': True})
    float_denominator_val: float | None = field(default=None, metadata={'omitempty': True})
    int_numerator_val: int | None = field(default=None, metadata={'omitempty': True})
    int_denominator_val: int | None = field(default=None, metadata={'omitempty': True})
    string_val: str | None = field(default=None, metadata={'omitempty': True})
    bool_val: bool | None = field(default=None, metadata={'omitempty': True})
    unit: str = field(default="", metadata={'omitempty': True})
    desc: str = field(default="", metadata={'omitempty': True})


@dataclass
class DrainSpec(Model):
    """DrainSpec describes a drain; deadline is nanoseconds, and a negative value means no deadline."""

    deadline: int = 0
    ignore_system_jobs: bool = False


@dataclass
class DrainStrategy(Model):
    deadline: int = 0
    ignore_system_jobs: bool = False
    force_deadline: str = field(default="", metadata={"time": True})
    started_at: str = field(default="", metadata={"time": True})

    def __str__(self) -> str:
        if self.ignore_system_jobs:
            return f"drain ignoring system jobs and deadline at {self.force_deadline}"
        return f"drain with deadline at {self.force_deadline}"


@dataclass
class NodeDrainUpdateResponse(Model):
    node_modify_index: int = 0
    eval_ids: list[str] | None = field(default=None, metadata={"json": "EvalIDs"})
    eval_create_index: int = 0


@dataclass
class NodeEligibilityUpdateResponse(Model):
    node_modify_index: int = 0
    eval_ids: list[str] | None = field(default=None, metadata={"json": "EvalIDs"})
    eval_create_index: int = 0


@dataclass
class NodePurgeResponse(Model):
    eval_ids: list[str] | None = field(default=None, metadata={"json": "EvalIDs"})
    eval_create_index: int = 0
    node_modify_index: int = 0


class Nodes:
    """Nodes queries the node endpoints."""

    def __init__(self, client: Client):
        self._client = client
        self.meta = NodeMeta(client)
        self.identity = NodeIdentity(client)

    def list(self, q: QueryOptions | None = None) -> tuple[list[NodeListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/nodes", q)
        nodes = [NodeListStub.from_json(n) for n in resp]
        nodes.sort(key=lambda n: n.create_index, reverse=True)
        return nodes, qm

    def prefix_list(self, prefix: str, q: QueryOptions | None = None) -> tuple[list[NodeListStub], QueryMeta]:
        from .api import QueryOptions

        if q is None:
            q = QueryOptions()
        q.prefix = prefix
        return self.list(q)

    def info(self, node_id: str, q: QueryOptions | None = None) -> tuple[Node, QueryMeta]:
        resp, qm = self._client.query(f"/v1/node/{node_id}", q)
        return Node.from_json(resp), qm

    def update_drain(self, node_id: str, spec: DrainSpec | None, mark_eligible: bool = False, w: WriteOptions | None = None,
                     *, meta: dict[str, str] | None = None) -> tuple[NodeDrainUpdateResponse, WriteMeta]:
        """update_drain starts a drain with spec, or stops it when spec is None."""
        req = {"NodeID": node_id, "DrainSpec": spec.to_json() if spec else None, "MarkEligible": mark_eligible, "Meta": meta}
        resp, wm = self._client.put(f"/v1/node/{node_id}/drain", req, w)
        return NodeDrainUpdateResponse.from_json(resp), wm

    def toggle_eligibility(self, node_id: str, eligible: bool, w: WriteOptions | None = None) -> tuple[NodeEligibilityUpdateResponse, WriteMeta]:
        req = {"NodeID": node_id, "Eligibility": NODE_SCHEDULING_ELIGIBLE if eligible else NODE_SCHEDULING_INELIGIBLE}
        resp, wm = self._client.put(f"/v1/node/{node_id}/eligibility", req, w)
        return NodeEligibilityUpdateResponse.from_json(resp), wm

    def allocations(self, node_id: str, q: QueryOptions | None = None) -> tuple[list[dict[str, Any]], QueryMeta]:
        resp, qm = self._client.query(f"/v1/node/{node_id}/allocations", q)
        resp.sort(key=lambda a: a["CreateIndex"], reverse=True)
        return resp, qm

    def csi_volumes(self, node_id: str, q: QueryOptions | None = None) -> list[dict[str, Any]]:
        resp, _ = self._client.query(f"/v1/volumes?type=csi&node_id={node_id}", q)
        return resp

    def force_evaluate(self, node_id: str, w: WriteOptions | None = None) -> tuple[str, WriteMeta]:
        resp, wm = self._client.put(f"/v1/node/{node_id}/evaluate", None, w)
        # The server answers with EvalIDs, not EvalID; Go decodes that as an empty string and so does this.
        return resp.get("EvalID", ""), wm

    def stats(self, node_id: str, q: QueryOptions | None = None) -> HostStats:
        resp, _ = self._client.query(f"/v1/client/stats?node_id={node_id}", q)
        return HostStats.from_json(resp)

    def gc(self, node_id: str, q: QueryOptions | None = None) -> None:
        self._client.query(f"/v1/client/gc?node_id={node_id}", q)

    def gc_alloc(self, alloc_id: str, q: QueryOptions | None = None) -> None:
        self._client.query(f"/v1/client/allocation/{alloc_id}/gc", q)

    def purge(self, node_id: str, q: QueryOptions | None = None) -> tuple[NodePurgeResponse, QueryMeta]:
        resp, qm = self._client.put_query(f"/v1/node/{node_id}/purge", None, q)
        return NodePurgeResponse.from_json(resp), qm
