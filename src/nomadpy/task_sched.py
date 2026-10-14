from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Model


@dataclass
class TaskSchedule(Model):
    cron: TaskScheduleCron | None = None


@dataclass
class TaskScheduleCron(Model):
    start: str = ""
    end: str = ""
    timezone: str = ""

