from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api import Client


class Regions:
    """Regions queries the regions in the cluster."""

    def __init__(self, client: Client):
        self._client = client

    def list(self) -> list[str]:
        resp, _ = self._client.query("/v1/regions")
        return sorted(resp)
