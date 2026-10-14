from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Model

CONSTRAINT_DISTINCT_PROPERTY = "distinct_property"
CONSTRAINT_DISTINCT_HOSTS = "distinct_hosts"
CONSTRAINT_REGEX = "regexp"
CONSTRAINT_VERSION = "version"
CONSTRAINT_SEMVER = "semver"
CONSTRAINT_SET_CONTAINS = "set_contains"
CONSTRAINT_SET_CONTAINS_ALL = "set_contains_all"
CONSTRAINT_SET_CONTAINS_ANY = "set_contains_any"
CONSTRAINT_ATTRIBUTE_IS_SET = "is_set"
CONSTRAINT_ATTRIBUTE_IS_NOT_SET = "is_not_set"


@dataclass
class Constraint(Model):
    l_target: str = ""
    r_target: str = ""
    operand: str = ""

