"""Job specifications and wait helpers for the tests that run jobs on an agent."""

import time
from datetime import timedelta

from nomadpy import QueryOptions
from nomadpy.deployments import DEPLOYMENT_STATUS_PENDING, DEPLOYMENT_STATUS_RUNNING
from nomadpy.evaluations import EVAL_STATUS_CANCELLED, EVAL_STATUS_COMPLETE, EVAL_STATUS_FAILED

WAIT = timedelta(seconds=10)
DEADLINE = 90


def service_job(job_id, count=1, canary=0, sleep=600, nomad_service=False, scaling=False, command=None):
    service = ""
    if scaling:
        service += """
    scaling {
      min     = 1
      max     = 3
      enabled = true
      policy {
        cooldown = "1m"
      }
    }
"""
    if nomad_service:
        service += f"""
    network {{
      port "http" {{}}
    }}
    service {{
      name     = "{job_id}-svc"
      provider = "nomad"
      port     = "http"
      tags     = ["nomadpy"]
    }}
"""
    return f"""
job "{job_id}" {{
  datacenters = ["dc1"]
  type        = "service"

  group "g" {{
    count = {count}
{service}

    update {{
      max_parallel     = 1
      canary           = {canary}
      min_healthy_time = "1s"
      healthy_deadline = "30s"
      auto_revert      = false
    }}

    task "t" {{
      driver = "raw_exec"
      config {{
        command = "/bin/sh"
        args    = ["-c", "{command or f'sleep {sleep}'}"]
      }}
      resources {{
        cpu    = 10
        memory = 32
      }}
    }}
  }}
}}
"""


def batch_job(job_id, parameterized=False, periodic=False):
    extra = ""
    if parameterized:
        extra += '  parameterized {\n    payload = "optional"\n    meta_optional = ["key"]\n  }\n'
    if periodic:
        extra += '  periodic {\n    cron             = "0 0 1 1 *"\n    prohibit_overlap = true\n  }\n'
    return f"""
job "{job_id}" {{
  datacenters = ["dc1"]
  type        = "batch"
{extra}
  group "g" {{
    task "t" {{
      driver = "raw_exec"
      config {{
        command = "/bin/sh"
        args    = ["-c", "exit 0"]
      }}
      resources {{
        cpu    = 10
        memory = 32
      }}
    }}
  }}
}}
"""


def wait_for_eval(client, eval_id):
    """Blocks on the evaluation until it leaves the pending states and returns it."""
    index = 0
    deadline = time.monotonic() + DEADLINE
    while time.monotonic() < deadline:
        ev, qm = client.evaluations.info(eval_id, QueryOptions(wait_index=index, wait_time=WAIT))
        if ev.status in (EVAL_STATUS_COMPLETE, EVAL_STATUS_FAILED, EVAL_STATUS_CANCELLED):
            return ev
        index = qm.last_index
    raise AssertionError(f"evaluation {eval_id} did not finish")


def wait_for_deployment(client, deployment_id, until=None):
    """Blocks on the deployment until it reaches a terminal status, or `until`, and returns it."""
    index = 0
    deadline = time.monotonic() + DEADLINE
    while time.monotonic() < deadline:
        dep, qm = client.deployments.info(deployment_id, QueryOptions(wait_index=index, wait_time=WAIT))
        if until is not None and dep.status == until:
            return dep
        if until is None and dep.status not in (DEPLOYMENT_STATUS_RUNNING, DEPLOYMENT_STATUS_PENDING):
            return dep
        index = qm.last_index
    raise AssertionError(f"deployment {deployment_id} did not reach {until or 'a terminal status'}: {dep.status}")


def register_and_wait(client, job_id, **spec):
    """Registers a service job from HCL and waits for its deployment to succeed."""
    job = client.jobs.parse_hcl(service_job(job_id, **spec))
    resp, _ = client.jobs.register(job)
    assert wait_for_eval(client, resp.eval_id).status == EVAL_STATUS_COMPLETE
    dep, _ = client.jobs.latest_deployment(job_id)
    return wait_for_deployment(client, dep.id)
