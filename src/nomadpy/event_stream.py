from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterator
from urllib.parse import urlencode

from . import allocations as _allocations
from . import deployments as _deployments
from . import evaluations as _evaluations
from . import jobs as _jobs
from . import node_pools as _node_pools
from . import nodes as _nodes
from . import services as _services
from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryOptions

TOPIC_DEPLOYMENT = "Deployment"
TOPIC_EVALUATION = "Evaluation"
TOPIC_ALLOCATION = "Allocation"
TOPIC_JOB = "Job"
TOPIC_NODE = "Node"
TOPIC_NODE_POOL = "NodePool"
TOPIC_SERVICE = "Service"
TOPIC_ALL = "*"


@dataclass
class Event(Model):
    topic: str = ""
    type: str = ""
    key: str = ""
    filter_keys: list[str] | None = None
    index: int = 0
    payload: dict[str, Any] | None = None

    def deployment(self) -> _deployments.Deployment | None:
        return self._decode("Deployment", _deployments.Deployment)

    def evaluation(self) -> _evaluations.Evaluation | None:
        return self._decode("Evaluation", _evaluations.Evaluation)

    def allocation(self) -> _allocations.Allocation | None:
        return self._decode("Allocation", _allocations.Allocation)

    def job(self) -> _jobs.Job | None:
        return self._decode("Job", _jobs.Job)

    def deregistered_job(self) -> tuple[_jobs.Job | None, bool]:
        return self.job(), bool((self.payload or {}).get("Deleted"))

    def node(self) -> _nodes.Node | None:
        return self._decode("Node", _nodes.Node)

    def node_pool(self) -> _node_pools.NodePool | None:
        return self._decode("NodePool", _node_pools.NodePool)

    def service(self) -> _services.ServiceRegistration | None:
        return self._decode("Service", _services.ServiceRegistration)

    def _decode(self, key: str, cls):
        value = (self.payload or {}).get(key)
        return cls.from_json(value) if value is not None else None


@dataclass
class Events(Model):
    index: int = 0
    events: list[Event] | None = None
    err: Any = None

    def is_heartbeat(self) -> bool:
        return self.index == 0 and not self.events


class EventStream:
    """EventStream subscribes to the server's event stream."""

    def __init__(self, client: Client):
        self._client = client

    def stream(self, topics: dict[str, list[str]], index: int = 0, q: QueryOptions | None = None,
               timeout: float | None = None) -> Iterator[Events]:
        """stream yields event batches as the server sends them, skipping heartbeats.

        The subscription stays open until the generator is closed. `timeout`
        bounds each wait for the next batch; the server heartbeats when idle.
        """
        from .api import QueryOptions

        params = []
        for topic, keys in topics.items():
            params += [("topic", f"{topic}:{k}") for k in keys] or [("topic", topic)]
        # The index goes through the options' params, as in Go, so it overrides a wait index set there.
        q = dataclasses.replace(q or QueryOptions(), params={**(q.params if q else {}), "index": str(index)})
        endpoint = "/v1/event/stream?" + urlencode(params)
        for value in self._client.stream_json(endpoint, q, timeout):
            events = Events.from_json(value)
            if not events.is_heartbeat():
                yield events
