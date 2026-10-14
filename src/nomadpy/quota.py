"""Quotas are Enterprise, in the Governance & Policy module."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .api import QueryOptions
from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, WriteMeta, WriteOptions


@dataclass
class QuotaStorageResources(Model):
    variables_mb: int = field(default=0, metadata={"json": "VariablesMB"})
    host_volumes_mb: int = field(default=0, metadata={"json": "HostVolumesMB"})


@dataclass
class NodePoolLimit(Model):
    node_pool: str = ""
    cpu: int | None = field(default=None, metadata={"json": "CPU"})
    cores: int | None = None
    memory_mb: int | None = field(default=None, metadata={"json": "MemoryMB"})
    memory_max_mb: int | None = field(default=None, metadata={"json": "MemoryMaxMB"})
    devices: list[dict[str, Any]] | None = None
    numa: dict[str, Any] | None = field(default=None, metadata={"json": "NUMA"})
    secrets_mb: int | None = field(default=None, metadata={"json": "SecretsMB"})
    storage: QuotaStorageResources | None = None


@dataclass
class QuotaResources(Model):
    cpu: int | None = field(default=None, metadata={"json": "CPU"})
    cores: int | None = None
    memory_mb: int | None = field(default=None, metadata={"json": "MemoryMB"})
    memory_max_mb: int | None = field(default=None, metadata={"json": "MemoryMaxMB"})
    devices: list[dict[str, Any]] | None = None
    numa: dict[str, Any] | None = field(default=None, metadata={"json": "NUMA"})
    secrets_mb: int | None = field(default=None, metadata={"json": "SecretsMB"})
    storage: QuotaStorageResources | None = None
    node_pools: list[NodePoolLimit] | None = None


@dataclass
class QuotaLimit(Model):
    region: str = ""
    region_limit: QuotaResources | None = None
    variables_limit: int | None = None
    hash: str | None = None


@dataclass
class QuotaSpec(Model):
    name: str = ""
    description: str = ""
    limits: list[QuotaLimit] | None = None
    create_index: int = 0
    modify_index: int = 0


@dataclass
class QuotaUsage(Model):
    name: str = ""
    used: dict[str, QuotaLimit] | None = None
    create_index: int = 0
    modify_index: int = 0


class Quotas:
    """Quotas queries the quota endpoints (Enterprise)."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[QuotaSpec], QueryMeta]:
        resp, qm = self._client.query("/v1/quotas", q)
        specs = [QuotaSpec.from_json(s) for s in resp]
        specs.sort(key=lambda s: s.create_index, reverse=True)
        return specs, qm

    def prefix_list(self, prefix: str, q: QueryOptions | None = None) -> tuple[list[QuotaSpec], QueryMeta]:
        return self.list(dataclasses.replace(q or QueryOptions(), prefix=prefix))

    def list_usage(self, q: QueryOptions | None = None) -> tuple[list[QuotaUsage], QueryMeta]:
        resp, qm = self._client.query("/v1/quota-usages", q)
        usages = [QuotaUsage.from_json(u) for u in resp]
        usages.sort(key=lambda u: u.create_index, reverse=True)
        return usages, qm

    def prefix_list_usage(self, prefix: str, q: QueryOptions | None = None) -> tuple[list[QuotaUsage], QueryMeta]:
        return self.list_usage(dataclasses.replace(q or QueryOptions(), prefix=prefix))

    def info(self, name: str, q: QueryOptions | None = None) -> tuple[QuotaSpec, QueryMeta]:
        resp, qm = self._client.query("/v1/quota/" + quote(name, safe=""), q)
        return QuotaSpec.from_json(resp), qm

    def usage(self, name: str, q: QueryOptions | None = None) -> tuple[QuotaUsage, QueryMeta]:
        resp, qm = self._client.query("/v1/quota/usage/" + quote(name, safe=""), q)
        return QuotaUsage.from_json(resp), qm

    def register(self, spec: QuotaSpec, w: WriteOptions | None = None) -> WriteMeta:
        _, wm = self._client.put("/v1/quota", spec.to_json(), w)
        return wm

    def delete(self, quota: str, w: WriteOptions | None = None) -> WriteMeta:
        _, wm = self._client.delete("/v1/quota/" + quote(quota, safe=""), None, w)
        return wm
