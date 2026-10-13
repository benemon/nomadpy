from __future__ import annotations

from typing import TYPE_CHECKING

from .api import QueryOptions

if TYPE_CHECKING:
    from .api import Client


class Status:
    """Status queries the status-related endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def leader(self) -> str:
        resp, _ = self._client.query("/v1/status/leader")
        return resp

    def region_leader(self, region: str) -> str:
        resp, _ = self._client.query("/v1/status/leader", QueryOptions(region=region))
        return resp

    def peers(self) -> list[str]:
        resp, _ = self._client.query("/v1/status/peers")
        return resp
