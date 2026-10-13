from __future__ import annotations

from dataclasses import dataclass, field

from .models import Model


@dataclass
class GaugeValue(Model):
    name: str = ""
    value: float = 0.0
    display_labels: dict[str, str] | None = field(default=None, metadata={"json": "Labels"})


@dataclass
class PointValue(Model):
    name: str = ""
    points: list[float] | None = None


@dataclass
class SampledValue(Model):
    name: str = ""
    count: int = 0
    rate: float = 0.0
    sum: float = 0.0
    min: float = 0.0
    max: float = 0.0
    mean: float = 0.0
    stddev: float = 0.0
    display_labels: dict[str, str] | None = field(default=None, metadata={"json": "Labels"})


@dataclass
class MetricsSummary(Model):
    timestamp: str = ""
    gauges: list[GaugeValue] | None = None
    points: list[PointValue] | None = None
    counters: list[SampledValue] | None = None
    samples: list[SampledValue] | None = None
