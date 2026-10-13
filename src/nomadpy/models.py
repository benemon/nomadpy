from __future__ import annotations

import dataclasses
import re
import types
import typing
from typing import Any


GO_ZERO_TIME = "0001-01-01T00:00:00Z"


def json_name(name: str) -> str:
    """json_name converts a snake_case field name to the Go struct field name Nomad uses in JSON."""
    return "".join(part.capitalize() for part in name.split("_"))


class Model:
    """Model is the base for dataclasses that are decoded from, and encoded to, Nomad JSON.

    JSON keys are the Go field names. A field whose Go name is not the
    capitalised form of its Python name (ID, JobID, TGUpdates) declares it
    with `field(metadata={"json": "JobID"})`. Keys the dataclass does not
    declare are ignored so newer servers do not break older clients.

    A field with `metadata={"duration": "string"}` is a Go time.Duration
    that the Go client marshals as a duration string ("1h0m0s"); it is an
    int of nanoseconds in Python and is encoded and decoded like Go does.
    A field with `metadata={"time": True}` is a Go time.Time: an RFC 3339
    string in Python, sent as Go's zero time when empty. A field with
    `metadata={"omitempty": True}` mirrors the Go json tag and is left out
    of the encoding when it is None or zero.
    """

    @classmethod
    def from_json(cls, data: dict[str, Any]):
        hints = typing.get_type_hints(cls)
        kwargs = {}
        for f in dataclasses.fields(cls):
            key = f.metadata.get("json", json_name(f.name))
            if key not in data:
                continue
            if f.metadata.get("duration") == "string":
                kwargs[f.name] = _decode_duration(data[key])
            else:
                kwargs[f.name] = _convert(hints[f.name], data[key])
        return cls(**kwargs)

    def to_json(self) -> dict[str, Any]:
        """to_json encodes every field under its Go name, as the Go client does."""
        out = {}
        for f in dataclasses.fields(self):
            value = getattr(self, f.name)
            if f.metadata.get("omitempty") and not value:
                continue
            if f.metadata.get("duration") == "string":
                # Go's ACL types blank a zero duration; the autopilot types render it as "0s" (metadata zero="0s").
                value = format_duration(value) if value else f.metadata.get("zero", "")
            elif f.metadata.get("time") and not value:
                value = GO_ZERO_TIME
            out[f.metadata.get("json", json_name(f.name))] = _encode(value)
        return out


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


def _encode(value: Any) -> Any:
    if isinstance(value, Model):
        return value.to_json()
    if isinstance(value, list):
        return [_encode(v) for v in value]
    if isinstance(value, dict):
        return {k: _encode(v) for k, v in value.items()}
    return value


def _decode_duration(value: Any) -> int:
    # The server answers with nanoseconds; the Go client and older servers use strings.
    if isinstance(value, str):
        return parse_duration(value) if value else 0
    return int(value)


_UNITS = {"ns": 1, "us": 1_000, "µs": 1_000, "μs": 1_000, "ms": 1_000_000, "s": 1_000_000_000,
          "m": 60_000_000_000, "h": 3_600_000_000_000}
_DURATION = re.compile(r"(\d+(?:\.\d*)?|\.\d+)(ns|us|µs|μs|ms|s|m|h)")


def parse_duration(text: str) -> int:
    """parse_duration reads a Go duration string such as "1h30m" or "1.5s" into nanoseconds."""
    s = text
    sign = 1
    if s.startswith(("-", "+")):
        sign = -1 if s[0] == "-" else 1
        s = s[1:]
    if s == "0":
        return 0
    pos = 0
    total = 0
    while pos < len(s):
        m = _DURATION.match(s, pos)
        if m is None:
            raise ValueError(f"invalid duration {text!r}")
        total += round(float(m.group(1)) * _UNITS[m.group(2)])
        pos = m.end()
    if total == 0 and not s:
        raise ValueError(f"invalid duration {text!r}")
    return sign * total


def format_duration(ns: int) -> str:
    """format_duration renders nanoseconds the way Go's time.Duration.String does ("1h0m0s", "1.5s", "500ms")."""
    if ns == 0:
        return "0s"
    sign = "-" if ns < 0 else ""
    ns = abs(ns)
    if ns < 1_000_000_000:
        if ns < 1_000:
            return f"{sign}{ns}ns"
        if ns < 1_000_000:
            return f"{sign}{_fraction(ns, 1_000)}µs"
        return f"{sign}{_fraction(ns, 1_000_000)}ms"
    hours, rest = divmod(ns, 3_600_000_000_000)
    minutes, rest = divmod(rest, 60_000_000_000)
    out = f"{_fraction(rest, 1_000_000_000)}s"
    if hours or minutes:
        out = f"{minutes}m{out}"
    if hours:
        out = f"{hours}h{out}"
    return sign + out


def _fraction(ns: int, unit: int) -> str:
    whole, rest = divmod(ns, unit)
    if rest == 0:
        return str(whole)
    digits = len(str(unit)) - 1
    return f"{whole}.{str(rest).rjust(digits, '0').rstrip('0')}"
