from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryOptions


@dataclass
class NodeMetaResponse(Model):
    meta: dict[str, str] | None = None
    dynamic: dict[str, str | None] | None = None
    static: dict[str, str] | None = None


class NodeMeta:
    """NodeMeta reads and writes a node's dynamic metadata."""

    def __init__(self, client: Client):
        self._client = client

    def apply(self, node_id: str, meta: dict[str, str | None], q: QueryOptions | None = None) -> NodeMetaResponse:
        """apply merges meta into the node's dynamic metadata; a None value deletes the key."""
        resp, _ = self._client.post_query("/v1/client/metadata", {"NodeID": node_id, "Meta": meta}, q)
        return NodeMetaResponse.from_json(resp)

    def read(self, node_id: str = "", q: QueryOptions | None = None) -> NodeMetaResponse:
        from .api import QueryOptions

        if q is None:
            q = QueryOptions()
        if node_id:
            q.params["node_id"] = node_id
        resp, _ = self._client.query("/v1/client/metadata", q)
        return NodeMetaResponse.from_json(resp)
