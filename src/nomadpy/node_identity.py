from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .api import QueryOptions
from .models import Model

if TYPE_CHECKING:
    from .api import Client


@dataclass
class NodeIdentityGetResponse(Model):
    claims: dict[str, Any] | None = None


@dataclass
class NodeIdentityRenewResponse(Model):
    pass


class NodeIdentity:
    """NodeIdentity reads and renews a node's workload identity."""

    def __init__(self, client: Client):
        self._client = client

    def get(self, node_id: str = "", q: QueryOptions | None = None) -> NodeIdentityGetResponse:
        if q is None:
            q = QueryOptions()
        if node_id:
            q.params["node_id"] = node_id
        resp, _ = self._client.query("/v1/client/identity", q)
        return NodeIdentityGetResponse.from_json(resp)

    def renew(self, node_id: str, q: QueryOptions | None = None) -> NodeIdentityRenewResponse:
        resp, _ = self._client.post_query("/v1/client/identity/renew", {"NodeID": node_id}, q)
        return NodeIdentityRenewResponse.from_json(resp or {})
