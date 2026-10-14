from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import quote

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions

@dataclass
class ServiceRegistration(Model):
    id: str = field(default="", metadata={"json": "ID"})
    service_name: str = ""
    namespace: str = ""
    node_id: str = field(default="", metadata={"json": "NodeID"})
    datacenter: str = ""
    job_id: str = field(default="", metadata={"json": "JobID"})
    alloc_id: str = field(default="", metadata={"json": "AllocID"})
    tags: list[str] | None = None
    address: str = ""
    port: int = 0
    create_index: int = 0
    modify_index: int = 0

@dataclass
class ServiceRegistrationStub(Model):
    service_name: str = ""
    tags: list[str] | None = None

@dataclass
class ServiceRegistrationListStub(Model):
    namespace: str = ""
    services: list[ServiceRegistrationStub] | None = None

class Services:
    """Services queries the Nomad-native service registration endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[ServiceRegistrationListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/services", q)
        return [ServiceRegistrationListStub.from_json(s) for s in resp], qm

    def get(self, service_name: str, q: QueryOptions | None = None) -> tuple[list[ServiceRegistration], QueryMeta]:
        resp, qm = self._client.query("/v1/service/" + quote(service_name, safe=""), q)
        return [ServiceRegistration.from_json(s) for s in resp], qm

    def delete(self, service_name: str, service_id: str, w: WriteOptions | None = None) -> WriteMeta:
        _, wm = self._client.delete(f"/v1/service/{quote(service_name, safe='')}/{quote(service_id, safe='')}", None, w)
        return wm

# The specification models below reference tasks and consul, which import jobs, which imports this module;
# importing them here, after ServiceRegistration exists, keeps that cycle importable in any order.
from . import consul as _consul  # noqa: E402
from . import tasks as _tasks  # noqa: E402


# generated from surface.json: file=services.go only=Service,ServiceCheck,CheckRestart,ServiceWeights
from . import consul as _consul  # noqa: E402
from . import tasks as _tasks  # noqa: E402

ON_UPDATE_REQUIRE_HEALTHY = "require_healthy"
ON_UPDATE_IGNORE_WARN = "ignore_warnings"
ON_UPDATE_IGNORE = "ignore"
SERVICE_PROVIDER_CONSUL = "consul"


@dataclass
class CheckRestart(Model):
    limit: int = 0
    grace: int | None = None
    ignore_warnings: bool = False


@dataclass
class Service(Model):
    name: str = ""
    tags: list[str] | None = None
    canary_tags: list[str] | None = None
    enable_tag_override: bool = False
    port_label: str = ""
    address_mode: str = ""
    address: str = ""
    checks: list[ServiceCheck] | None = None
    check_restart: CheckRestart | None = None
    connect: _consul.ConsulConnect | None = None
    meta: dict[str, str] | None = None
    canary_meta: dict[str, str] | None = None
    tagged_addresses: dict[str, str] | None = None
    task_name: str = ""
    on_update: str = ""
    identity: _tasks.WorkloadIdentity | None = None
    weights: ServiceWeights | None = None
    provider: str = ""
    cluster: str = ""
    kind: str = ""


@dataclass
class ServiceCheck(Model):
    name: str = ""
    type: str = ""
    command: str = ""
    args: list[str] | None = None
    path: str = ""
    protocol: str = ""
    port_label: str = ""
    expose: bool = False
    address_mode: str = ""
    advertise: str = ""
    interval: int = 0
    timeout: int = 0
    initial_status: str = ""
    notes: str = ""
    tls_server_name: str = field(default="", metadata={'json': 'TLSServerName'})
    tls_skip_verify: bool = field(default=False, metadata={'json': 'TLSSkipVerify'})
    header: dict[str, list[str]] | None = None
    method: str = ""
    check_restart: CheckRestart | None = None
    grpc_service: str = field(default="", metadata={'json': 'GRPCService'})
    grpc_use_tls: bool = field(default=False, metadata={'json': 'GRPCUseTLS'})
    task_name: str = ""
    success_before_passing: int = 0
    failures_before_critical: int = 0
    failures_before_warning: int = 0
    body: str = ""
    on_update: str = ""


@dataclass
class ServiceWeights(Model):
    passing: int = 0
    warning: int = 0


# end generated


