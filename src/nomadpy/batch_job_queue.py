from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions


class BatchQueue:
    """BatchQueue queries the experimental batch job queue endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def jobs(self, q: QueryOptions | None = None) -> tuple[BatchJobQueueJobsResponse, QueryMeta]:
        resp, qm = self._client.query("/v1/queue/jobs", q)
        return BatchJobQueueJobsResponse.from_json(resp), qm

    def status(self, q: QueryOptions | None = None) -> tuple[BatchJobQueueStatusResponse, QueryMeta]:
        resp, qm = self._client.query("/v1/queue/status", q)
        return BatchJobQueueStatusResponse.from_json(resp), qm


# generated from surface.json: file=batch_job_queue.go

BATCH_QUEUE_TENANT_METADATA = "metadata"
BATCH_QUEUE_TENANT_NAMESPACE = "namespace"
BATCH_QUEUE_TYPE_DYNAMIC = "dynamic_priority"
BATCH_QUEUE_TYPE_FIFO = "fifo"
BATCH_QUEUE_TYPE_PASSTHROUGH = "passthrough"


@dataclass
class AgeConfig(Model):
    weight: int = 0
    max: int = 0


@dataclass
class BatchJobQueueJobsResponse(Model):
    type: str = ""
    workloads: Any = None


@dataclass
class BatchJobQueueStatusResponse(Model):
    type: str = ""
    status: Any = None


@dataclass
class BatchQueueConfig(Model):
    constraint_timeout: int = 0
    dynamic_priority: DynamicQueueConfig | None = None
    fifo: FifoQueueConfig | None = None


@dataclass
class DynamicPriorityTenant(Model):
    tenant_id: str = field(default="", metadata={'json': 'TenantID'})
    percentage_used: int = 0
    tenant_fairshare: dict[str, float] | None = None
    total_fairshare: dict[str, float] | None = None


@dataclass
class DynamicPriorityWorkload(Model):
    job_id: str = field(default="", metadata={'json': 'JobID'})
    tenant: str = ""
    status: str = ""
    position: int = 0
    adjusted_priority: int = 0
    base_priority: int = 0
    fairshare_adjustment: int = 0
    age_adjustment: int = 0
    cpu_adjustment: int = 0
    memory_adjustment: int = 0
    created_at: int = 0


@dataclass
class FifoQueueConfig(Model):
    pass


@dataclass
class JobSizeConfig(Model):
    cpu_weight: int = 0
    cpu_max: int = 0
    memory_weight: int = 0
    memory_max: int = 0


@dataclass
class TenantFairshareConfig(Model):
    tenant_type: str = ""
    metadata_key: str = ""
    cpu_weight: int = 0
    memory_weight: int = 0
    exclude_alloc_statuses: list[str] | None = None


@dataclass
class Workload(Model):
    job_id: str = field(default="", metadata={'json': 'JobID'})
    position: int = 0
    status: str = ""
    created_at: int = 0


@dataclass
class DynamicQueueConfig(Model):
    calc_interval: int = 0
    tenant_fairshare: TenantFairshareConfig = field(default_factory=TenantFairshareConfig)
    age: AgeConfig = field(default_factory=AgeConfig)
    job_size: JobSizeConfig = field(default_factory=JobSizeConfig)


# end generated
