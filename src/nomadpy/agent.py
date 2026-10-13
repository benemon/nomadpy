from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryOptions, WriteOptions


@dataclass
class KeyringResponse(Model):
    messages: dict[str, str] | None = None
    keys: dict[str, int] | None = None
    num_nodes: int = 0


@dataclass
class AgentMember(Model):
    name: str = ""
    addr: str = ""
    port: int = 0
    tags: dict[str, str] | None = None
    status: str = ""
    protocol_min: int = 0
    protocol_max: int = 0
    protocol_cur: int = 0
    delegate_min: int = 0
    delegate_max: int = 0
    delegate_cur: int = 0


@dataclass
class ServerMembers(Model):
    server_name: str = ""
    server_region: str = ""
    server_dc: str = field(default="", metadata={"json": "ServerDC"})
    members: list[AgentMember] | None = None


@dataclass
class AgentSelf(Model):
    config: dict[str, Any] = field(default_factory=dict, metadata={"json": "config"})
    member: AgentMember = field(default_factory=AgentMember, metadata={"json": "member"})
    stats: dict[str, dict[str, str]] = field(default_factory=dict, metadata={"json": "stats"})


@dataclass
class AgentHealth(Model):
    ok: bool = field(default=False, metadata={"json": "ok"})
    message: str = field(default="", metadata={"json": "message"})


@dataclass
class AgentHealthResponse(Model):
    client: AgentHealth | None = field(default=None, metadata={"json": "client", "omitempty": True})
    server: AgentHealth | None = field(default=None, metadata={"json": "server", "omitempty": True})


@dataclass
class DiskUsage(Model):
    disk_mb: int = field(default=0, metadata={"json": "DiskMB"})
    used_mb: int = field(default=0, metadata={"json": "UsedMB"})


@dataclass
class HostData(Model):
    os: str = field(default="", metadata={"json": "OS"})
    network: list[dict[str, str]] | None = None
    resolv_conf: str = ""
    hosts: str = ""
    environment: dict[str, str] | None = None
    disk: dict[str, DiskUsage] | None = None


@dataclass
class HostDataResponse(Model):
    agent_id: str = field(default="", metadata={"json": "AgentID"})
    host_data: HostData | None = field(default=None, metadata={"omitempty": True})


@dataclass
class SchedulerWorkerPoolArgs(Model):
    num_schedulers: int = 0
    enabled_schedulers: list[str] | None = None


@dataclass
class AgentSchedulerWorkerInfo(Model):
    id: str = field(default="", metadata={"json": "id"})
    enabled_schedulers: list[str] | None = field(default=None, metadata={"json": "enabled_schedulers"})
    started: str = field(default="", metadata={"json": "started"})
    status: str = field(default="", metadata={"json": "status"})
    workload_status: str = field(default="", metadata={"json": "workload_status"})


@dataclass
class AgentSchedulerWorkersInfo(Model):
    server_id: str = field(default="", metadata={"json": "server_id"})
    schedulers: list[AgentSchedulerWorkerInfo] | None = field(default=None, metadata={"json": "schedulers"})


class Agent:
    """Agent queries the agent endpoints. Node name, datacenter and region are cached from the first self() call, as in Go."""

    def __init__(self, client: Client):
        self._client = client
        self._node_name = ""
        self._datacenter = ""
        self._region = ""

    def self(self) -> AgentSelf:
        resp, _ = self._client.query("/v1/agent/self")
        info = AgentSelf.from_json(resp)
        self._node_name = info.member.name
        self._datacenter = info.config.get("Datacenter", "")
        self._region = info.config.get("Region", "")
        return info

    def node_name(self) -> str:
        if not self._node_name:
            self.self()
        return self._node_name

    def datacenter(self) -> str:
        if not self._datacenter:
            self.self()
        return self._datacenter

    def region(self) -> str:
        if not self._region:
            self.self()
        return self._region

    def join(self, *addrs: str) -> tuple[int, str]:
        """join asks the agent to join the given addresses and returns the number joined and any warning; an error raises."""
        resp, _ = self._client.put("/v1/agent/join?" + urlencode([("address", a) for a in addrs]), None)
        if resp.get("error"):
            raise RuntimeError(f"failed joining: {resp['error']}")
        return resp.get("num_joined", 0), resp.get("warning", "")

    def members(self, q: QueryOptions | None = None) -> ServerMembers:
        resp, _ = self._client.query("/v1/agent/members", q)
        return ServerMembers.from_json(resp)

    def force_leave(self, node: str, *, prune: bool = False) -> None:
        params = [("node", node)] + ([("prune", "1")] if prune else [])
        self._client.put("/v1/agent/force-leave?" + urlencode(params), None)

    def servers(self) -> list[str]:
        resp, _ = self._client.query("/v1/agent/servers")
        return resp

    def set_servers(self, addrs: list[str]) -> None:
        self._client.put("/v1/agent/servers?" + urlencode([("address", a) for a in addrs]), None)

    def list_keys(self) -> KeyringResponse:
        resp, _ = self._client.query("/v1/agent/keyring/list")
        return KeyringResponse.from_json(resp)

    def reload(self, w: WriteOptions | None = None) -> None:
        self._client.put("/v1/agent/reload", None, w)

    def install_key(self, key: str) -> KeyringResponse:
        resp, _ = self._client.put("/v1/agent/keyring/install", {"Key": key})
        return KeyringResponse.from_json(resp)

    def use_key(self, key: str) -> KeyringResponse:
        resp, _ = self._client.put("/v1/agent/keyring/use", {"Key": key})
        return KeyringResponse.from_json(resp)

    def remove_key(self, key: str) -> KeyringResponse:
        resp, _ = self._client.put("/v1/agent/keyring/remove", {"Key": key})
        return KeyringResponse.from_json(resp)

    def health(self) -> AgentHealthResponse:
        """health decodes the agent's health whatever the status code, since an unhealthy agent answers 500 with the same body."""
        _, resp, _ = self._client.request("GET", "/v1/agent/health", expected=(200, 500, 503))
        return AgentHealthResponse.from_json(resp)

    def host(self, server_id: str = "", node_id: str = "", q: QueryOptions | None = None) -> HostDataResponse:
        from .api import QueryOptions

        if q is None:
            q = QueryOptions()
        if server_id:
            q.params["server_id"] = server_id
        if node_id:
            q.params["node_id"] = node_id
        resp, _ = self._client.query("/v1/agent/host", q)
        return HostDataResponse.from_json(resp)

    def get_scheduler_worker_config(self, q: QueryOptions | None = None) -> SchedulerWorkerPoolArgs:
        resp, _ = self._client.query("/v1/agent/schedulers/config", q)
        return SchedulerWorkerPoolArgs(resp.get("num_schedulers", 0), resp.get("enabled_schedulers"))

    def set_scheduler_worker_config(self, args: SchedulerWorkerPoolArgs, w: WriteOptions | None = None) -> SchedulerWorkerPoolArgs:
        req = {"num_schedulers": args.num_schedulers, "enabled_schedulers": args.enabled_schedulers}
        resp, _ = self._client.put("/v1/agent/schedulers/config", req, w)
        return SchedulerWorkerPoolArgs(resp.get("num_schedulers", 0), resp.get("enabled_schedulers"))

    def get_scheduler_workers_info(self, q: QueryOptions | None = None) -> AgentSchedulerWorkersInfo:
        resp, _ = self._client.query("/v1/agent/schedulers", q)
        return AgentSchedulerWorkersInfo.from_json(resp)
