from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlencode

from .models import Model

HOST_VOLUME_STATE_PENDING = "pending"
HOST_VOLUME_STATE_READY = "ready"
HOST_VOLUME_STATE_UNAVAILABLE = "unavailable"
HOST_VOLUME_ATTACHMENT_MODE_UNKNOWN = ""
HOST_VOLUME_ATTACHMENT_MODE_BLOCK_DEVICE = "block-device"
HOST_VOLUME_ATTACHMENT_MODE_FILESYSTEM = "file-system"
HOST_VOLUME_ACCESS_MODE_UNKNOWN = ""
HOST_VOLUME_ACCESS_MODE_SINGLE_NODE_READER = "single-node-reader-only"
HOST_VOLUME_ACCESS_MODE_SINGLE_NODE_WRITER = "single-node-writer"
HOST_VOLUME_ACCESS_MODE_SINGLE_NODE_SINGLE_WRITER = "single-node-single-writer"
HOST_VOLUME_ACCESS_MODE_SINGLE_NODE_MULTI_WRITER = "single-node-multi-writer"

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions
from . import allocations as _allocations
from . import constraint as _constraint
HOST_VOLUME_ACCESS_MODE_SINGLE_NODE_MULTI_WRITER = "single-node-multi-writer"



@dataclass
class HostVolume(Model):
    namespace: str = ""
    id: str = field(default="", metadata={'json': 'ID'})
    name: str = ""
    plugin_id: str = field(default="", metadata={'json': 'PluginID'})
    node_pool: str = ""
    node_id: str = field(default="", metadata={'json': 'NodeID'})
    constraints: list[_constraint.Constraint] | None = field(default=None, metadata={'omitempty': True})
    requested_capacity_min_bytes: int = 0
    requested_capacity_max_bytes: int = 0
    capacity_bytes: int = 0
    requested_capabilities: list[HostVolumeCapability] | None = None
    parameters: dict[str, str] | None = field(default=None, metadata={'omitempty': True})
    host_path: str = ""
    state: str = ""
    create_index: int = 0
    create_time: int = 0
    modify_index: int = 0
    modify_time: int = 0
    allocations: list[_allocations.AllocationListStub] | None = field(default=None, metadata={'omitempty': True})


@dataclass
class HostVolumeCapability(Model):
    attachment_mode: str = ""
    access_mode: str = ""


@dataclass
class HostVolumeCreateRequest(Model):
    volume: HostVolume | None = None
    policy_override: bool = False


@dataclass
class HostVolumeCreateResponse(Model):
    volume: HostVolume | None = None
    warnings: str = ""


@dataclass
class HostVolumeDeleteRequest(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    force: bool = False


@dataclass
class HostVolumeListRequest(Model):
    node_id: str = field(default="", metadata={'json': 'NodeID'})
    node_pool: str = ""


@dataclass
class HostVolumeRegisterRequest(Model):
    volume: HostVolume | None = None
    policy_override: bool = False


@dataclass
class HostVolumeRegisterResponse(Model):
    volume: HostVolume | None = None
    warnings: str = ""


@dataclass
class HostVolumeStub(Model):
    namespace: str = ""
    id: str = field(default="", metadata={'json': 'ID'})
    name: str = ""
    plugin_id: str = field(default="", metadata={'json': 'PluginID'})
    node_pool: str = ""
    node_id: str = field(default="", metadata={'json': 'NodeID'})
    capacity_bytes: int = 0
    state: str = ""
    create_index: int = 0
    create_time: int = 0
    modify_index: int = 0
    modify_time: int = 0


class HostVolumes:
    """HostVolumes queries the dynamic host volume endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def create(self, volume: HostVolume, w: WriteOptions | None = None, *, policy_override: bool = False) -> tuple[HostVolumeCreateResponse, WriteMeta]:
        resp, wm = self._client.put("/v1/volume/host/create", {"Volume": volume.to_json(), "PolicyOverride": policy_override}, w)
        return HostVolumeCreateResponse.from_json(resp), wm

    def register(self, volume: HostVolume, w: WriteOptions | None = None, *, policy_override: bool = False) -> tuple[HostVolumeRegisterResponse, WriteMeta]:
        resp, wm = self._client.put("/v1/volume/host/register", {"Volume": volume.to_json(), "PolicyOverride": policy_override}, w)
        return HostVolumeRegisterResponse.from_json(resp), wm

    def get(self, id: str, q: QueryOptions | None = None) -> tuple[HostVolume, QueryMeta]:
        resp, qm = self._client.query("/v1/volume/host/" + quote(id, safe=""), q)
        return HostVolume.from_json(resp), qm

    def list(self, q: QueryOptions | None = None, *, node_id: str = "", node_pool: str = "") -> tuple[list[HostVolumeStub], QueryMeta]:
        params = [("type", "host")]
        if node_id:
            params.append(("node_id", node_id))
        if node_pool:
            params.append(("node_pool", node_pool))
        resp, qm = self._client.query("/v1/volumes?" + urlencode(params), q)
        return [HostVolumeStub.from_json(v) for v in resp], qm

    def delete(self, id: str, w: WriteOptions | None = None, *, force: bool = False) -> WriteMeta:
        _, wm = self._client.delete("/v1/volume/host/" + quote(id, safe="") + ("?force=true" if force else ""), None, w)
        return wm
