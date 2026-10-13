from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .jobs import JobListStub
from .models import Model
from .nodes import NodeListStub
from .operator_autopilot import AutopilotConfiguration, OperatorHealthReply
from .operator_metrics import MetricsSummary

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions

SCHEDULER_ALGORITHM_BINPACK = "binpack"
SCHEDULER_ALGORITHM_SPREAD = "spread"


@dataclass
class RaftServer(Model):
    id: str = field(default="", metadata={"json": "ID"})
    node: str = ""
    address: str = ""
    leader: bool = False
    voter: bool = False
    raft_protocol: str = ""


@dataclass
class RaftConfiguration(Model):
    servers: list[RaftServer] | None = None
    index: int = 0


@dataclass
class PreemptionConfig(Model):
    system_scheduler_enabled: bool = False
    sys_batch_scheduler_enabled: bool = False
    batch_scheduler_enabled: bool = False
    service_scheduler_enabled: bool = False


@dataclass
class SchedulerConfiguration(Model):
    scheduler_algorithm: str = ""
    preemption_config: PreemptionConfig = field(default_factory=PreemptionConfig)
    memory_oversubscription_enabled: bool = False
    reject_job_registration: bool = False
    pause_eval_broker: bool = False
    node_limit_for_feasibility_checks: int = 0
    create_index: int = 0
    modify_index: int = 0


@dataclass
class SchedulerConfigurationResponse(Model):
    scheduler_config: SchedulerConfiguration | None = None


@dataclass
class SchedulerSetConfigurationResponse(Model):
    updated: bool = False


@dataclass
class License(Model):
    license_id: str = field(default="", metadata={"json": "LicenseID"})
    customer_id: str = field(default="", metadata={"json": "CustomerID"})
    installation_id: str = field(default="", metadata={"json": "InstallationID"})
    issue_time: str = field(default="", metadata={"time": True})
    start_time: str = field(default="", metadata={"time": True})
    expiration_time: str = field(default="", metadata={"time": True})
    termination_time: str = field(default="", metadata={"time": True})
    non_production: bool = False
    product: str = ""
    flags: dict[str, Any] | None = None
    modules: list[str] | None = None
    features: list[str] | None = None


@dataclass
class LicenseReply(Model):
    license: License | None = None
    config_outdated: bool = False


@dataclass
class VaultAccessor(Model):
    alloc_id: str = field(default="", metadata={"json": "AllocID"})
    task: str = ""
    node_id: str = field(default="", metadata={"json": "NodeID"})
    accessor: str = ""
    creation_ttl: int = field(default=0, metadata={"json": "CreationTTL"})
    create_index: int = 0


@dataclass
class VaultWorkloadIdentityUpgradeCheck(Model):
    jobs_without_vault_identity: list[JobListStub] | None = None
    outdated_nodes: list[NodeListStub] | None = None
    vault_tokens: list[VaultAccessor] | None = None

    def ready(self) -> bool:
        return not self.vault_tokens and not self.outdated_nodes and not self.jobs_without_vault_identity


@dataclass
class OperatorUtilizationSnapshotResponse(Model):
    bundle: str = ""


class Operator:
    """Operator queries the operator endpoints. The licence endpoints are Enterprise."""

    def __init__(self, client: Client):
        self._client = client

    def raft_get_configuration(self, q: QueryOptions | None = None) -> RaftConfiguration:
        resp, _ = self._client.query("/v1/operator/raft/configuration", q)
        return RaftConfiguration.from_json(resp)

    def raft_remove_peer_by_address(self, address: str, w: WriteOptions | None = None) -> None:
        self._client.delete(f"/v1/operator/raft/peer?address={address}", None, w)

    def raft_remove_peer_by_id(self, id: str, w: WriteOptions | None = None) -> None:
        self._client.delete(f"/v1/operator/raft/peer?id={id}", None, w)

    def raft_transfer_leadership_by_address(self, address: str, w: WriteOptions | None = None) -> None:
        self._client.put(f"/v1/operator/raft/transfer-leadership?address={address}", None, w)

    def raft_transfer_leadership_by_id(self, id: str, w: WriteOptions | None = None) -> None:
        self._client.put(f"/v1/operator/raft/transfer-leadership?id={id}", None, w)

    def scheduler_get_configuration(self, q: QueryOptions | None = None) -> tuple[SchedulerConfigurationResponse, QueryMeta]:
        resp, qm = self._client.query("/v1/operator/scheduler/configuration", q)
        return SchedulerConfigurationResponse.from_json(resp), qm

    def scheduler_set_configuration(self, conf: SchedulerConfiguration, w: WriteOptions | None = None) -> tuple[SchedulerSetConfigurationResponse, WriteMeta]:
        resp, wm = self._client.put("/v1/operator/scheduler/configuration", conf.to_json(), w)
        return SchedulerSetConfigurationResponse.from_json(resp), wm

    def scheduler_cas_configuration(self, conf: SchedulerConfiguration, w: WriteOptions | None = None) -> tuple[SchedulerSetConfigurationResponse, WriteMeta]:
        resp, wm = self._client.put(f"/v1/operator/scheduler/configuration?cas={conf.modify_index}", conf.to_json(), w)
        return SchedulerSetConfigurationResponse.from_json(resp), wm

    def apply_license(self, license: str, w: WriteOptions | None = None, *, force: bool = False) -> WriteMeta:
        """apply_license uploads a licence (Enterprise); the body is the raw licence text."""
        endpoint = "/v1/operator/license" + ("?force=true" if force else "")
        _, wm = self._client.put(endpoint, license.encode(), w)
        return wm

    def license_get(self, q: QueryOptions | None = None) -> tuple[LicenseReply | None, QueryMeta]:
        """license_get returns None on a Community server, which answers 204."""
        status, resp, qm = self._client.request("GET", "/v1/operator/license", None, q, (200, 204))
        return (LicenseReply.from_json(resp) if status == 200 else None), qm

    def upgrade_check_vault_workload_identity(self, q: QueryOptions | None = None) -> tuple[VaultWorkloadIdentityUpgradeCheck, QueryMeta]:
        resp, qm = self._client.query("/v1/operator/upgrade-check/vault-workload-identity", q)
        return VaultWorkloadIdentityUpgradeCheck.from_json(resp), qm

    def utilization(self, w: WriteOptions | None = None, *, today_only: bool = False) -> tuple[OperatorUtilizationSnapshotResponse, WriteMeta]:
        endpoint = "/v1/operator/utilization" + ("?today=true" if today_only else "")
        resp, wm = self._client.post(endpoint, None, w)
        return OperatorUtilizationSnapshotResponse.from_json(resp), wm

    def autopilot_get_configuration(self, q: QueryOptions | None = None) -> tuple[AutopilotConfiguration, QueryMeta]:
        resp, qm = self._client.query("/v1/operator/autopilot/configuration", q)
        return AutopilotConfiguration.from_json(resp), qm

    def autopilot_set_configuration(self, conf: AutopilotConfiguration, w: WriteOptions | None = None) -> WriteMeta:
        _, wm = self._client.put("/v1/operator/autopilot/configuration", conf.to_json(), w)
        return wm

    def autopilot_cas_configuration(self, conf: AutopilotConfiguration, w: WriteOptions | None = None) -> tuple[bool, WriteMeta]:
        resp, wm = self._client.put(f"/v1/operator/autopilot/configuration?cas={conf.modify_index}", conf.to_json(), w)
        return bool(resp), wm

    def autopilot_server_health(self, q: QueryOptions | None = None) -> tuple[OperatorHealthReply, QueryMeta]:
        resp, qm = self._client.query("/v1/operator/autopilot/health", q)
        return OperatorHealthReply.from_json(resp), qm

    def metrics(self, q: QueryOptions | None = None) -> bytes:
        """metrics returns the raw metrics body; pass params={"format": "prometheus"} for the Prometheus exposition format."""
        raw, _ = self._client.raw_query("/v1/metrics", q)
        return raw

    def metrics_summary(self, q: QueryOptions | None = None) -> tuple[MetricsSummary, QueryMeta]:
        resp, qm = self._client.query("/v1/metrics", q)
        return MetricsSummary.from_json(resp), qm
