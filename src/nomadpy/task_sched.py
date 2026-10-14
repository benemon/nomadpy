# generated from surface.json: file=task_sched.go

from __future__ import annotations

from dataclasses import dataclass

from .models import Model


@dataclass
class TaskSchedule(Model):
    cron: TaskScheduleCron | None = None


@dataclass
class TaskScheduleCron(Model):
    start: str = ""
    end: str = ""
    timezone: str = ""

# end generated
