from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api import Client


class System:
    """System triggers server-side maintenance."""

    def __init__(self, client: Client):
        self._client = client

    def garbage_collect(self) -> None:
        self._client.put("/v1/system/gc", {})

    def reconcile_summaries(self) -> None:
        self._client.put("/v1/system/reconcile/summaries", {})
