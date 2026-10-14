from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import quote

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions

ON_UPDATE_REQUIRE_HEALTHY = "require_healthy"
ON_UPDATE_IGNORE_WARN = "ignore_warnings"
ON_UPDATE_IGNORE = "ignore"
SERVICE_PROVIDER_CONSUL = "consul"


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
