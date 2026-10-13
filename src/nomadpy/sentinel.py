"""Sentinel policies are Enterprise, in the Governance & Policy module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions

SENTINEL_SCOPE_SUBMIT_JOB = "submit-job"
SENTINEL_SCOPE_SUBMIT_HOST_VOLUME = "submit-host-volume"
SENTINEL_SCOPE_SUBMIT_CSI_VOLUME = "submit-csi-volume"


@dataclass
class SentinelPolicy(Model):
    name: str = ""
    description: str = ""
    scope: str = ""
    enforcement_level: str = ""
    policy: str = ""
    create_index: int = 0
    modify_index: int = 0


@dataclass
class SentinelPolicyListStub(Model):
    name: str = ""
    description: str = ""
    scope: str = ""
    enforcement_level: str = ""
    create_index: int = 0
    modify_index: int = 0


class SentinelPolicies:
    """SentinelPolicies queries the Sentinel policy endpoints (Enterprise)."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[SentinelPolicyListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/sentinel/policies", q)
        return [SentinelPolicyListStub.from_json(p) for p in resp], qm

    def upsert(self, policy: SentinelPolicy, w: WriteOptions | None = None) -> WriteMeta:
        if not policy.name:
            raise ValueError("missing policy name")
        _, wm = self._client.put(f"/v1/sentinel/policy/{policy.name}", policy.to_json(), w)
        return wm

    def delete(self, policy_name: str, w: WriteOptions | None = None) -> WriteMeta:
        if not policy_name:
            raise ValueError("missing policy name")
        _, wm = self._client.delete(f"/v1/sentinel/policy/{policy_name}", None, w)
        return wm

    def info(self, policy_name: str, q: QueryOptions | None = None) -> tuple[SentinelPolicy, QueryMeta]:
        if not policy_name:
            raise ValueError("missing policy name")
        resp, qm = self._client.query(f"/v1/sentinel/policy/{policy_name}", q)
        return SentinelPolicy.from_json(resp), qm
