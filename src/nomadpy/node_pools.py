from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import quote

from .jobs import JobListStub
from .models import Model
from .nodes import NodeListStub

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions

NODE_POOL_ALL = "all"
NODE_POOL_DEFAULT = "default"


@dataclass
class NodePoolSchedulerConfiguration(Model):
    """NodePoolSchedulerConfiguration is Enterprise."""

    scheduler_algorithm: str = ""
    memory_oversubscription_enabled: bool | None = None


@dataclass
class NodePool(Model):
    name: str = ""
    description: str = ""
    meta: dict[str, str] | None = None
    node_identity_ttl: int = field(default=0, metadata={"json": "NodeIdentityTTL", "duration": "string"})
    scheduler_configuration: NodePoolSchedulerConfiguration | None = None
    create_index: int = 0
    modify_index: int = 0


class NodePools:
    """NodePools queries the node pool endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[NodePool], QueryMeta]:
        resp, qm = self._client.query("/v1/node/pools", q)
        return [NodePool.from_json(p) for p in resp], qm

    def prefix_list(self, prefix: str, q: QueryOptions | None = None) -> tuple[list[NodePool], QueryMeta]:
        from .api import QueryOptions

        if q is None:
            q = QueryOptions()
        q.prefix = prefix
        return self.list(q)

    def info(self, name: str, q: QueryOptions | None = None) -> tuple[NodePool, QueryMeta]:
        if not name:
            raise ValueError("missing node pool name")
        resp, qm = self._client.query("/v1/node/pool/" + quote(name, safe=""), q)
        return NodePool.from_json(resp), qm

    def register(self, pool: NodePool, w: WriteOptions | None = None) -> WriteMeta:
        if not pool.name:
            raise ValueError("missing node pool name")
        _, wm = self._client.put("/v1/node/pools", pool.to_json(), w)
        return wm

    def delete(self, name: str, w: WriteOptions | None = None) -> WriteMeta:
        if not name:
            raise ValueError("missing node pool name")
        _, wm = self._client.delete("/v1/node/pool/" + quote(name, safe=""), None, w)
        return wm

    def list_jobs(self, pool_name: str, q: QueryOptions | None = None) -> tuple[list[JobListStub], QueryMeta]:
        resp, qm = self._client.query(f"/v1/node/pool/{quote(pool_name, safe='')}/jobs", q)
        return [JobListStub.from_json(j) for j in resp], qm

    def list_nodes(self, pool_name: str, q: QueryOptions | None = None) -> tuple[list[NodeListStub], QueryMeta]:
        resp, qm = self._client.query(f"/v1/node/pool/{quote(pool_name, safe='')}/nodes", q)
        return [NodeListStub.from_json(n) for n in resp], qm
