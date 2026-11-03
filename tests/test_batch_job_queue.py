import pytest

from nomadpy import BatchQueueConfig, FifoQueueConfig, NodePool, QueryOptions
from nomadpy.batch_job_queue import BATCH_QUEUE_TYPE_FIFO


@pytest.mark.parametrize("config", [
    {"ConstraintTimeout": 15_000_000_000, "DynamicPriority": None, "Fifo": {}},
    {
        "ConstraintTimeout": 15_000_000_000,
        "DynamicPriority": {
            "CalcInterval": 20_000_000_000,
            "TenantFairshare": {
                "TenantType": "namespace",
                "MetadataKey": "",
                "CpuWeight": 1,
                "MemoryWeight": 2,
                "ExcludeAllocStatuses": ["complete"],
            },
            "Age": {"Weight": 3, "Max": 14_400_000_000_000},
            "JobSize": {"CpuWeight": 4, "CpuMax": 5000, "MemoryWeight": 6, "MemoryMax": 7000},
        },
        "Fifo": None,
    },
])
def test_node_pool_batch_queue_config_round_trip(config):
    pool = NodePool.from_json({"Name": "p", "BatchQueueConfig": config})
    assert pool.to_json()["BatchQueueConfig"] == config


def test_jobs_and_status(client):
    name = "nomadpy-batch-queue-endpoints"
    client.node_pools.register(NodePool(name=name, batch_queue_config=BatchQueueConfig(fifo=FifoQueueConfig())))
    try:
        q = QueryOptions(params={"node_pool": name})
        jobs, jobs_meta = client.batch_queue.jobs(q)
        status, status_meta = client.batch_queue.status(q)
        assert jobs.type == BATCH_QUEUE_TYPE_FIFO and jobs.workloads == [] and jobs_meta.last_index >= 0
        assert status.type == BATCH_QUEUE_TYPE_FIFO and status.status is None and status_meta.last_index >= 0
    finally:
        client.node_pools.delete(name)
