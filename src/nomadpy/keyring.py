from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import quote, urlencode

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions

ENCRYPTION_ALGORITHM_AES256_GCM = "aes256-gcm"
ROOT_KEY_STATE_INACTIVE = "inactive"
ROOT_KEY_STATE_ACTIVE = "active"
ROOT_KEY_STATE_REKEYING = "rekeying"
ROOT_KEY_STATE_DEPRECATED = "deprecated"
ROOT_KEY_STATE_PREPUBLISHED = "prepublished"


@dataclass
class RootKeyMeta(Model):
    key_id: str = field(default="", metadata={"json": "KeyID"})
    algorithm: str = ""
    create_time: int = 0
    create_index: int = 0
    modify_index: int = 0
    state: str = ""
    publish_time: int = 0


class Keyring:
    """Keyring queries the server root keyring endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[RootKeyMeta], QueryMeta]:
        resp, qm = self._client.query("/v1/operator/keyring/keys", q)
        return [RootKeyMeta.from_json(k) for k in resp], qm

    def delete(self, key_id: str, w: WriteOptions | None = None, *, force: bool = False) -> WriteMeta:
        _, wm = self._client.delete(f"/v1/operator/keyring/key/{quote(key_id, safe='')}?force={str(force).lower()}", None, w)
        return wm

    def rotate(self, w: WriteOptions | None = None, *, full: bool = False, algorithm: str = "", publish_time: int = 0) -> tuple[RootKeyMeta | None, WriteMeta]:
        """rotate creates a new root key; publish_time (Unix nanoseconds) prepublishes it instead of activating it."""
        params = []
        if algorithm:
            params.append(("algo", algorithm))
        if full:
            params.append(("full", "true"))
        if publish_time > 0:
            params.append(("publish_time", str(publish_time)))
        resp, wm = self._client.put("/v1/operator/keyring/rotate?" + urlencode(params), None, w)
        key = resp.get("Key") if resp else None
        return (RootKeyMeta.from_json(key) if key else None), wm
