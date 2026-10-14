from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from collections.abc import Iterator
from urllib.parse import urlencode

from .models import Model

ORIGIN_START = "start"
ORIGIN_END = "end"
FS_LOG_NAME_STDOUT = "stdout"
FS_LOG_NAME_STDERR = "stderr"

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions


@dataclass
class AllocFileInfo(Model):
    name: str = ""
    is_dir: bool = False
    size: int = 0
    file_mode: str = ""
    mod_time: str = field(default="", metadata={"time": True})
    content_type: str = ""


@dataclass
class StreamFrame(Model):
    offset: int = field(default=0, metadata={"omitempty": True})
    data: str | None = field(default=None, metadata={"omitempty": True})
    file: str = field(default="", metadata={"omitempty": True})
    file_event: str = field(default="", metadata={"omitempty": True})

    def is_heartbeat(self) -> bool:
        return not self.data and not self.file_event and not self.file and self.offset == 0

    @property
    def data_bytes(self) -> bytes:
        """The frame's data decoded; the wire form is base64, as Go marshals []byte."""
        return base64.b64decode(self.data) if self.data else b""


class AllocFS:
    """AllocFS reads an allocation's filesystem and logs through the server."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, alloc_id: str, path: str, q: QueryOptions | None = None) -> tuple[list[AllocFileInfo], QueryMeta]:
        resp, qm = self._client.query(f"/v1/client/fs/ls/{alloc_id}?" + urlencode([("path", path)]), q)
        return [AllocFileInfo.from_json(f) for f in resp], qm

    def stat(self, alloc_id: str, path: str, q: QueryOptions | None = None) -> tuple[AllocFileInfo, QueryMeta]:
        resp, qm = self._client.query(f"/v1/client/fs/stat/{alloc_id}?" + urlencode([("path", path)]), q)
        return AllocFileInfo.from_json(resp), qm

    def read_at(self, alloc_id: str, path: str, offset: int, limit: int, q: QueryOptions | None = None) -> bytes:
        params = urlencode([("path", path), ("offset", str(offset)), ("limit", str(limit))])
        raw, _ = self._client.raw_query(f"/v1/client/fs/readat/{alloc_id}?" + params, q)
        return raw

    def cat(self, alloc_id: str, path: str, q: QueryOptions | None = None) -> bytes:
        raw, _ = self._client.raw_query(f"/v1/client/fs/cat/{alloc_id}?" + urlencode([("path", path)]), q)
        return raw

    def stream(self, alloc_id: str, path: str, origin: str, offset: int, q: QueryOptions | None = None,
               timeout: float | None = None) -> Iterator[StreamFrame]:
        """stream follows a file in the allocation, yielding frames until the generator is closed."""
        params = urlencode([("path", path), ("offset", str(offset)), ("origin", origin)])
        yield from self._frames(f"/v1/client/fs/stream/{alloc_id}?" + params, q, timeout)

    def logs(self, alloc_id: str, follow: bool, task: str, log_type: str, origin: str, offset: int,
             q: QueryOptions | None = None, timeout: float | None = None) -> Iterator[StreamFrame]:
        """logs yields a task's stdout or stderr frames; with follow it stays open until the generator is closed."""
        params = urlencode([("follow", str(follow).lower()), ("task", task), ("type", log_type), ("origin", origin), ("offset", str(offset))])
        yield from self._frames(f"/v1/client/fs/logs/{alloc_id}?" + params, q, timeout)

    def _frames(self, endpoint: str, q: QueryOptions | None, timeout: float | None) -> Iterator[StreamFrame]:
        for value in self._client.stream_json(endpoint, q, timeout):
            frame = StreamFrame.from_json(value)
            if not frame.is_heartbeat():
                yield frame
