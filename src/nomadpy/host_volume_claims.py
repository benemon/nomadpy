from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import quote, urlencode

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions


# generated from surface.json: file=host_volume_claims.go

@dataclass
class TaskGroupHostVolumeClaim(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    namespace: str = ""
    job_id: str = field(default="", metadata={'json': 'JobID'})
    task_group_name: str = ""
    alloc_id: str = field(default="", metadata={'json': 'AllocID'})
    volume_id: str = field(default="", metadata={'json': 'VolumeID'})
    volume_name: str = ""
    create_index: int = 0
    modify_index: int = 0


# end generated


class TaskGroupHostVolumeClaims:
    """TaskGroupHostVolumeClaims queries the sticky host volume claim endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None, *, job_id: str = "", task_group: str = "", volume_name: str = "") -> tuple[list[TaskGroupHostVolumeClaim], QueryMeta]:
        params = [(k, v) for k, v in (("job_id", job_id), ("task_group", task_group), ("volume_name", volume_name)) if v]
        resp, qm = self._client.query("/v1/volumes/claims?" + urlencode(params), q)
        return [TaskGroupHostVolumeClaim.from_json(c) for c in resp or []], qm

    def delete(self, claim_id: str, w: WriteOptions | None = None) -> WriteMeta:
        _, wm = self._client.delete("/v1/volumes/claim/" + quote(claim_id, safe=""), None, w)
        return wm
