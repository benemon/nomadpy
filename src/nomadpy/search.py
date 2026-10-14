from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions

# Search contexts, from the Go api/contexts sub-package.
CONTEXT_ALLOCS = "allocs"
CONTEXT_DEPLOYMENTS = "deployment"
CONTEXT_EVALS = "evals"
CONTEXT_JOBS = "jobs"
CONTEXT_NODES = "nodes"
CONTEXT_NODE_POOLS = "node_pools"
CONTEXT_NAMESPACES = "namespaces"
CONTEXT_QUOTAS = "quotas"
CONTEXT_RECOMMENDATIONS = "recommendations"
CONTEXT_SCALING_POLICIES = "scaling_policy"
CONTEXT_PLUGINS = "plugins"
CONTEXT_VARIABLES = "vars"
CONTEXT_VOLUMES = "volumes"
CONTEXT_HOST_VOLUMES = "host_volumes"
CONTEXT_GROUPS = "groups"
CONTEXT_SERVICES = "services"
CONTEXT_TASKS = "tasks"
CONTEXT_IMAGES = "images"
CONTEXT_COMMANDS = "commands"
CONTEXT_CLASSES = "classes"
CONTEXT_ALL = "all"


@dataclass
class SearchResponse(Model):
    matches: dict[str, list[str]] | None = None
    truncations: dict[str, bool] | None = None


@dataclass
class FuzzyMatch(Model):
    id: str = field(default="", metadata={"json": "ID"})
    scope: list[str] | None = field(default=None, metadata={"omitempty": True})


@dataclass
class FuzzySearchResponse(Model):
    matches: dict[str, list[FuzzyMatch]] | None = None
    truncations: dict[str, bool] | None = None


class Search:
    """Search queries the prefix and fuzzy search endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def prefix_search(self, prefix: str, context: str, q: QueryOptions | None = None) -> tuple[SearchResponse, QueryMeta]:
        resp, qm = self._client.put_query("/v1/search", {"Prefix": prefix, "Context": context}, q)
        return SearchResponse.from_json(resp), qm

    def fuzzy_search(self, text: str, context: str, q: QueryOptions | None = None) -> tuple[FuzzySearchResponse, QueryMeta]:
        resp, qm = self._client.put_query("/v1/search/fuzzy", {"Text": text, "Context": context}, q)
        return FuzzySearchResponse.from_json(resp), qm
