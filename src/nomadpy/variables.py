from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .api import QueryOptions
from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, WriteMeta, WriteOptions

ERR_VARIABLE_NOT_FOUND = "variable not found"


@dataclass
class VariableLock(Model):
    id: str = field(default="", metadata={"json": "ID"})
    ttl: str = field(default="", metadata={"json": "TTL"})
    lock_delay: str = ""


@dataclass
class VariableMetadata(Model):
    namespace: str = ""
    path: str = ""
    create_index: int = 0
    modify_index: int = 0
    create_time: int = 0
    modify_time: int = 0
    lock: VariableLock | None = field(default=None, metadata={"omitempty": True})


@dataclass
class Variable(Model):
    namespace: str = ""
    path: str = ""
    create_index: int = 0
    modify_index: int = 0
    create_time: int = 0
    modify_time: int = 0
    # None, not {}: the server rejects an Items object on lock operations, and Go sends null for a nil map.
    items: dict[str, str] | None = None
    lock: VariableLock | None = field(default=None, metadata={"omitempty": True})

    def metadata(self) -> VariableMetadata:
        return VariableMetadata(self.namespace, self.path, self.create_index, self.modify_index, self.create_time, self.modify_time)

    def is_zero_value(self) -> bool:
        return self.metadata() == VariableMetadata() and self.items is None

    def lock_id(self) -> str:
        return self.lock.id if self.lock else ""


class ErrCASConflict(Exception):
    """ErrCASConflict is raised by the checked operations when the variable's modify index does not match."""

    def __init__(self, check_index: int, conflict: Variable):
        self.check_index = check_index
        self.conflict = conflict
        super().__init__(f"cas conflict: expected ModifyIndex {check_index}; found {conflict.modify_index}")


def _clean(path: str) -> str:
    return path.strip(" /")


class Variables:
    """Variables queries the variable endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def create(self, v: Variable, w: WriteOptions | None = None) -> tuple[Variable, WriteMeta]:
        v.path = _clean(v.path)
        resp, wm = self._client.put(f"/v1/var/{v.path}", v.to_json(), w)
        return Variable.from_json(resp), wm

    def checked_create(self, v: Variable, w: WriteOptions | None = None) -> tuple[Variable, WriteMeta]:
        """checked_create creates the variable only if it does not exist, raising ErrCASConflict otherwise."""
        v.path = _clean(v.path)
        return self._write_checked(f"/v1/var/{v.path}?cas=0", v, 0, w)

    def read(self, path: str, q: QueryOptions | None = None) -> tuple[Variable, QueryMeta]:
        v, qm = self.peek(path, q)
        if v is None:
            raise LookupError(ERR_VARIABLE_NOT_FOUND)
        return v, qm

    def peek(self, path: str, q: QueryOptions | None = None) -> tuple[Variable | None, QueryMeta]:
        """peek reads the variable and returns None instead of raising when it does not exist."""
        status, resp, qm = self._client.request("GET", f"/v1/var/{_clean(path)}", None, q, (200, 404))
        return (Variable.from_json(resp) if status == 200 else None), qm

    def update(self, v: Variable, w: WriteOptions | None = None) -> tuple[Variable, WriteMeta]:
        v.path = _clean(v.path)
        resp, wm = self._client.put(f"/v1/var/{v.path}", v.to_json(), w)
        return Variable.from_json(resp), wm

    def checked_update(self, v: Variable, w: WriteOptions | None = None) -> tuple[Variable, WriteMeta]:
        """checked_update writes only if the stored modify index equals v.modify_index, raising ErrCASConflict otherwise."""
        v.path = _clean(v.path)
        return self._write_checked(f"/v1/var/{v.path}?cas={v.modify_index}", v, v.modify_index, w)

    def delete(self, path: str, w: WriteOptions | None = None) -> WriteMeta:
        _, _, wm = self._client.request("DELETE", f"/v1/var/{_clean(path)}", None, w, (200, 204))
        return wm

    def checked_delete(self, path: str, check_index: int, w: WriteOptions | None = None) -> WriteMeta:
        """checked_delete deletes only if the stored modify index equals check_index, raising ErrCASConflict otherwise."""
        status, resp, wm = self._client.request("DELETE", f"/v1/var/{_clean(path)}?cas={check_index}", None, w, (200, 204, 409))
        if status == 409:
            raise ErrCASConflict(check_index, Variable.from_json(resp))
        return wm

    def list(self, q: QueryOptions | None = None) -> tuple[list[VariableMetadata], QueryMeta]:
        resp, qm = self._client.query("/v1/vars", q)
        return [VariableMetadata.from_json(v) for v in resp], qm

    def prefix_list(self, prefix: str, q: QueryOptions | None = None) -> tuple[list[VariableMetadata], QueryMeta]:
        return self.list(dataclasses.replace(q or QueryOptions(), prefix=prefix))

    def get_items(self, path: str, q: QueryOptions | None = None) -> tuple[dict[str, str], QueryMeta]:
        v, qm = self.read(path, q)
        return v.items, qm

    def renew_lock(self, v: Variable, w: WriteOptions | None = None) -> tuple[VariableMetadata, WriteMeta]:
        v.path = _clean(v.path)
        resp, wm = self._client.put(f"/v1/var/{v.path}?lock-renew", v.to_json(), w)
        return VariableMetadata.from_json(resp), wm

    def release_lock(self, v: Variable, w: WriteOptions | None = None) -> tuple[Variable, WriteMeta]:
        return self._lock_operation(v, w, "lock-release")

    def acquire_lock(self, v: Variable, w: WriteOptions | None = None) -> tuple[Variable, WriteMeta]:
        return self._lock_operation(v, w, "lock-acquire")

    def _lock_operation(self, v: Variable, w: WriteOptions | None, operation: str) -> tuple[Variable, WriteMeta]:
        v.path = _clean(v.path)
        resp, wm = self._client.put(f"/v1/var/{v.path}?{operation}", v.to_json(), w)
        return Variable.from_json(resp), wm

    def _write_checked(self, endpoint: str, v: Variable, check_index: int, w: WriteOptions | None) -> tuple[Variable, WriteMeta]:
        status, resp, wm = self._client.request("PUT", endpoint, v.to_json(), w, (200, 204, 409))
        if status == 409:
            raise ErrCASConflict(check_index, Variable.from_json(resp))
        return (Variable.from_json(resp) if resp else Variable()), wm
