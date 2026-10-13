from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions


@dataclass
class NamespaceCapabilities(Model):
    enabled_task_drivers: list[str] | None = None
    disabled_task_drivers: list[str] | None = None
    enabled_network_modes: list[str] | None = None
    disabled_network_modes: list[str] | None = None


@dataclass
class NamespaceNodePoolConfiguration(Model):
    """NamespaceNodePoolConfiguration is Enterprise."""

    default: str = ""
    allowed: list[str] | None = None
    denied: list[str] | None = None


@dataclass
class NamespaceVaultConfiguration(Model):
    """NamespaceVaultConfiguration is Enterprise."""

    default: str = ""
    allowed: list[str] | None = None
    denied: list[str] | None = None


@dataclass
class NamespaceConsulConfiguration(Model):
    """NamespaceConsulConfiguration is Enterprise."""

    default: str = ""
    allowed: list[str] | None = None
    denied: list[str] | None = None


@dataclass
class Namespace(Model):
    """Namespace is a namespace. Quota, NodePoolConfiguration, VaultConfiguration and ConsulConfiguration are Enterprise."""

    name: str = ""
    description: str = ""
    quota: str = ""
    capabilities: NamespaceCapabilities | None = None
    node_pool_configuration: NamespaceNodePoolConfiguration | None = None
    vault_configuration: NamespaceVaultConfiguration | None = None
    consul_configuration: NamespaceConsulConfiguration | None = None
    meta: dict[str, str] | None = None
    create_index: int = 0
    modify_index: int = 0
    required_extra_claims: dict[str, str] | None = None
    optional_extra_claims: dict[str, str] | None = None


@dataclass
class NamespacedID(Model):
    namespace: str = ""
    id: str = field(default="", metadata={"json": "ID"})


class Namespaces:
    """Namespaces queries the namespace endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[Namespace], QueryMeta]:
        resp, qm = self._client.query("/v1/namespaces", q)
        namespaces = [Namespace.from_json(n) for n in resp]
        namespaces.sort(key=lambda n: n.create_index, reverse=True)
        return namespaces, qm

    def prefix_list(self, prefix: str, q: QueryOptions | None = None) -> tuple[list[Namespace], QueryMeta]:
        from .api import QueryOptions

        if q is None:
            q = QueryOptions()
        q.prefix = prefix
        return self.list(q)

    def info(self, name: str, q: QueryOptions | None = None) -> tuple[Namespace, QueryMeta]:
        resp, qm = self._client.query(f"/v1/namespace/{name}", q)
        return Namespace.from_json(resp), qm

    def register(self, namespace: Namespace, w: WriteOptions | None = None) -> WriteMeta:
        _, wm = self._client.put("/v1/namespace", namespace.to_json(), w)
        return wm

    def delete(self, name: str, w: WriteOptions | None = None) -> WriteMeta:
        _, wm = self._client.delete(f"/v1/namespace/{name}", None, w)
        return wm
