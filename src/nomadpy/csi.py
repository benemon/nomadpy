from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import quote, urlencode

from .api import QueryOptions
from .models import Model


# generated from surface.json: file=csi.go
from . import allocations as _allocations  # noqa: E402
from . import nodes as _nodes  # noqa: E402

CSI_VOLUME_ATTACHMENT_MODE_UNKNOWN = ""
CSI_VOLUME_ATTACHMENT_MODE_BLOCK_DEVICE = "block-device"
CSI_VOLUME_ATTACHMENT_MODE_FILESYSTEM = "file-system"
CSI_VOLUME_ACCESS_MODE_UNKNOWN = ""
CSI_VOLUME_ACCESS_MODE_SINGLE_NODE_READER = "single-node-reader-only"
CSI_VOLUME_ACCESS_MODE_SINGLE_NODE_WRITER = "single-node-writer"
CSI_VOLUME_ACCESS_MODE_MULTI_NODE_READER = "multi-node-reader-only"
CSI_VOLUME_ACCESS_MODE_MULTI_NODE_SINGLE_WRITER = "multi-node-single-writer"
CSI_VOLUME_ACCESS_MODE_MULTI_NODE_MULTI_WRITER = "multi-node-multi-writer"
CSI_VOLUME_TYPE_HOST = "host"
CSI_VOLUME_TYPE_CSI = "csi"


@dataclass
class CSIMountOptions(Model):
    fs_type: str = field(default="", metadata={'json': 'FSType'})
    mount_flags: list[str] | None = None


@dataclass
class CSIPlugin(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    provider: str = ""
    version: str = ""
    controller_required: bool = False
    controllers: dict[str, _nodes.CSIInfo] | None = None
    nodes: dict[str, _nodes.CSIInfo] | None = None
    allocations: list[_allocations.AllocationListStub] | None = None
    controllers_healthy: int = 0
    controllers_expected: int = 0
    nodes_healthy: int = 0
    nodes_expected: int = 0
    create_index: int = 0
    modify_index: int = 0
    create_time: int = 0
    modify_time: int = 0


@dataclass
class CSIPluginListStub(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    provider: str = ""
    controller_required: bool = False
    controllers_healthy: int = 0
    controllers_expected: int = 0
    nodes_healthy: int = 0
    nodes_expected: int = 0
    create_index: int = 0
    modify_index: int = 0


@dataclass
class CSISnapshot(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    external_source_volume_id: str = field(default="", metadata={'json': 'ExternalSourceVolumeID'})
    size_bytes: int = 0
    create_time: int = 0
    is_ready: bool = False
    source_volume_id: str = field(default="", metadata={'json': 'SourceVolumeID'})
    plugin_id: str = field(default="", metadata={'json': 'PluginID'})
    name: str = ""
    secrets: dict[str, str] | None = None
    parameters: dict[str, str] | None = None


@dataclass
class CSISnapshotCreateResponse(Model):
    snapshots: list[CSISnapshot] | None = None


@dataclass
class CSISnapshotListResponse(Model):
    snapshots: list[CSISnapshot] | None = None
    next_token: str = ""


@dataclass
class CSIVolume(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    name: str = ""
    external_id: str = field(default="", metadata={'json': 'ExternalID'})
    namespace: str = ""
    requested_topologies: _nodes.CSITopologyRequest | None = None
    topologies: list[_nodes.CSITopology] | None = None
    access_mode: str = ""
    attachment_mode: str = ""
    mount_options: CSIMountOptions | None = None
    secrets: dict[str, str] | None = None
    parameters: dict[str, str] | None = None
    context: dict[str, str] | None = None
    capacity: int = 0
    requested_capacity_min: int = 0
    requested_capacity_max: int = 0
    requested_capabilities: list[CSIVolumeCapability] | None = None
    clone_id: str = field(default="", metadata={'json': 'CloneID'})
    snapshot_id: str = field(default="", metadata={'json': 'SnapshotID'})
    read_allocs: dict[str, _allocations.Allocation] | None = None
    write_allocs: dict[str, _allocations.Allocation] | None = None
    allocations: list[_allocations.AllocationListStub] | None = None
    schedulable: bool = False
    plugin_id: str = field(default="", metadata={'json': 'PluginID'})
    provider: str = ""
    provider_version: str = ""
    controller_required: bool = False
    controllers_healthy: int = 0
    controllers_expected: int = 0
    nodes_healthy: int = 0
    nodes_expected: int = 0
    resource_exhausted: str = field(default="", metadata={'time': True})
    create_index: int = 0
    modify_index: int = 0
    create_time: int = 0
    modify_time: int = 0


@dataclass
class CSIVolumeCapability(Model):
    access_mode: str = ""
    attachment_mode: str = ""


@dataclass
class CSIVolumeCreateResponse(Model):
    volumes: list[CSIVolume] | None = None
    warnings: str = ""


@dataclass
class CSIVolumeExternalStub(Model):
    external_id: str = field(default="", metadata={'json': 'ExternalID'})
    capacity_bytes: int = 0
    volume_context: dict[str, str] | None = None
    clone_id: str = field(default="", metadata={'json': 'CloneID'})
    snapshot_id: str = field(default="", metadata={'json': 'SnapshotID'})
    published_external_node_ids: list[str] | None = field(default=None, metadata={'json': 'PublishedExternalNodeIDs'})
    is_abnormal: bool = False
    status: str = ""


@dataclass
class CSIVolumeListExternalResponse(Model):
    volumes: list[CSIVolumeExternalStub] | None = None
    next_token: str = ""


@dataclass
class CSIVolumeListStub(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    namespace: str = ""
    name: str = ""
    external_id: str = field(default="", metadata={'json': 'ExternalID'})
    topologies: list[_nodes.CSITopology] | None = None
    access_mode: str = ""
    attachment_mode: str = ""
    current_readers: int = 0
    current_writers: int = 0
    schedulable: bool = False
    plugin_id: str = field(default="", metadata={'json': 'PluginID'})
    provider: str = ""
    controller_required: bool = False
    controllers_healthy: int = 0
    controllers_expected: int = 0
    nodes_healthy: int = 0
    nodes_expected: int = 0
    resource_exhausted: str = field(default="", metadata={'time': True})
    create_index: int = 0
    modify_index: int = 0
    create_time: int = 0
    modify_time: int = 0


@dataclass
class CSIVolumeRegisterResponse(Model):
    volumes: list[CSIVolume] | None = None
    warnings: str = ""


# end generated


def _secrets_header(secrets: dict[str, str] | None) -> dict[str, str]:
    """_secrets_header encodes CSI secrets as the X-Nomad-CSI-Secrets header, comma-separated k=v pairs."""
    if not secrets:
        return {}
    return {"X-Nomad-CSI-Secrets": ",".join(f"{k}={v}" for k, v in sorted(secrets.items()))}


def _headers(opts, headers, query=False):
    """_headers returns opts with the extra headers added, as a copy."""
    from .api import QueryOptions, WriteOptions

    if not headers:
        return opts
    if opts is None:
        opts = QueryOptions() if query else WriteOptions()
    return dataclasses.replace(opts, headers={**opts.headers, **headers})


class CSIVolumes:
    """CSIVolumes queries the CSI volume endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[CSIVolumeListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/volumes?type=csi", q)
        stubs = [CSIVolumeListStub.from_json(v) for v in resp]
        stubs.sort(key=lambda v: v.create_index, reverse=True)
        return stubs, qm

    def list_external(self, plugin_id: str, q: QueryOptions | None = None) -> tuple[CSIVolumeListExternalResponse, QueryMeta]:
        params = [("plugin_id", plugin_id)]
        if q is not None and q.next_token:
            params.append(("next_token", q.next_token))
        if q is not None and q.per_page:
            params.append(("per_page", str(q.per_page)))
        resp, qm = self._client.query("/v1/volumes/external?" + urlencode(params), q)
        out = CSIVolumeListExternalResponse.from_json(resp)
        if out.volumes:
            out.volumes.sort(key=lambda v: v.external_id)
        return out, qm

    def plugin_list(self, plugin_id: str) -> tuple[list[CSIVolumeListStub], QueryMeta]:
        return self.list(QueryOptions(prefix=plugin_id))

    def info(self, id: str, q: QueryOptions | None = None) -> tuple[CSIVolume, QueryMeta]:
        resp, qm = self._client.query(f"/v1/volume/csi/{id}", q)
        return CSIVolume.from_json(resp), qm

    def register(self, vol: CSIVolume, w: WriteOptions | None = None) -> tuple[CSIVolumeRegisterResponse, WriteMeta]:
        resp, wm = self._client.put(f"/v1/volume/csi/{vol.id}", {"Volumes": [vol.to_json()]}, w)
        return CSIVolumeRegisterResponse.from_json(resp or {}), wm

    def deregister(self, id: str, force: bool = False, w: WriteOptions | None = None) -> None:
        self._client.delete(f"/v1/volume/csi/{quote(id, safe='')}?force={str(force).lower()}", None, w)

    def create(self, vol: CSIVolume, w: WriteOptions | None = None) -> tuple[CSIVolumeCreateResponse, WriteMeta]:
        resp, wm = self._client.put(f"/v1/volume/csi/{vol.id}/create", {"Volumes": [vol.to_json()]}, w)
        return CSIVolumeCreateResponse.from_json(resp or {}), wm

    def delete(self, external_vol_id: str, w: WriteOptions | None = None, *, secrets: dict[str, str] | None = None) -> None:
        self._client.delete(f"/v1/volume/csi/{quote(external_vol_id, safe='')}/delete", None, _headers(w, _secrets_header(secrets)))

    def detach(self, vol_id: str, node_id: str, w: WriteOptions | None = None) -> None:
        self._client.delete(f"/v1/volume/csi/{quote(vol_id, safe='')}/detach?node={node_id}", None, w)

    def create_snapshot(self, snap: CSISnapshot, w: WriteOptions | None = None) -> tuple[CSISnapshotCreateResponse, WriteMeta]:
        req = {"Snapshots": [snap.to_json()]}
        resp, wm = self._client.put("/v1/volumes/snapshot", req, _headers(w, _secrets_header(snap.secrets)))
        return CSISnapshotCreateResponse.from_json(resp or {}), wm

    def delete_snapshot(self, snap: CSISnapshot, w: WriteOptions | None = None) -> None:
        params = urlencode([("plugin_id", snap.plugin_id), ("snapshot_id", snap.id)])
        self._client.delete("/v1/volumes/snapshot?" + params, None, _headers(w, _secrets_header(snap.secrets)))

    def list_snapshots(self, plugin_id: str = "", q: QueryOptions | None = None, *, secrets: dict[str, str] | None = None) -> tuple[CSISnapshotListResponse, QueryMeta]:
        params = []
        if plugin_id:
            params.append(("plugin_id", plugin_id))
        if q is not None and q.next_token:
            params.append(("next_token", q.next_token))
        if q is not None and q.per_page:
            params.append(("per_page", str(q.per_page)))
        resp, qm = self._client.query("/v1/volumes/snapshot?" + urlencode(params), _headers(q, _secrets_header(secrets), query=True))
        out = CSISnapshotListResponse.from_json(resp)
        if out.snapshots:
            out.snapshots.sort(key=lambda s: s.create_time, reverse=True)
        return out, qm


class CSIPlugins:
    """CSIPlugins queries the CSI plugin endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[CSIPluginListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/plugins?type=csi", q)
        stubs = [CSIPluginListStub.from_json(p) for p in resp]
        stubs.sort(key=lambda p: p.create_index, reverse=True)
        return stubs, qm

    def info(self, id: str, q: QueryOptions | None = None) -> tuple[CSIPlugin, QueryMeta]:
        resp, qm = self._client.query(f"/v1/plugin/csi/{id}", q)
        return CSIPlugin.from_json(resp), qm
