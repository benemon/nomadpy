from __future__ import annotations

import dataclasses
import types
import typing
from typing import Any


def json_name(name: str) -> str:
    """json_name converts a snake_case field name to the Go struct field name Nomad uses in JSON."""
    return "".join(part.capitalize() for part in name.split("_"))


class Model:
    """Model is the base for response dataclasses decoded from Nomad JSON.

    JSON keys are the Go field names. A field whose Go name is not the
    capitalised form of its Python name (ID, JobID, TGUpdates) declares it
    with `field(metadata={"json": "JobID"})`. Keys the dataclass does not
    declare are ignored so newer servers do not break older clients.
    """

    @classmethod
    def from_json(cls, data: dict[str, Any]):
        hints = typing.get_type_hints(cls)
        kwargs = {}
        for f in dataclasses.fields(cls):
            key = f.metadata.get("json", json_name(f.name))
            if key in data:
                kwargs[f.name] = _convert(hints[f.name], data[key])
        return cls(**kwargs)


def _convert(hint: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = typing.get_origin(hint)
    if origin in (typing.Union, types.UnionType):
        for arg in typing.get_args(hint):
            if arg is not type(None):
                return _convert(arg, value)
        return value
    if origin is list:
        (item,) = typing.get_args(hint)
        return [_convert(item, v) for v in value]
    if origin is dict:
        _, item = typing.get_args(hint)
        return {k: _convert(item, v) for k, v in value.items()}
    if isinstance(hint, type) and issubclass(hint, Model):
        return hint.from_json(value)
    return value
