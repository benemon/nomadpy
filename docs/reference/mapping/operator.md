# Operator

[Operator][nomadpy.operator.Operator] in `nomadpy.operator`.

| Python | Go | HTTP | API docs |
|---|---|---|---|
| [apply_license][nomadpy.operator.Operator.apply_license] | ApplyLicense, LicensePut | `PUT /v1/operator/license` | [operator/license](https://developer.hashicorp.com/nomad/api-docs/operator/license) Enterprise |
| [autopilot_cas_configuration][nomadpy.operator.Operator.autopilot_cas_configuration] | AutopilotCASConfiguration | `PUT /v1/operator/autopilot/configuration` | [operator/autopilot](https://developer.hashicorp.com/nomad/api-docs/operator/autopilot) |
| [autopilot_get_configuration][nomadpy.operator.Operator.autopilot_get_configuration] | AutopilotGetConfiguration | `GET /v1/operator/autopilot/configuration` | [operator/autopilot](https://developer.hashicorp.com/nomad/api-docs/operator/autopilot) |
| [autopilot_server_health][nomadpy.operator.Operator.autopilot_server_health] | AutopilotServerHealth | `GET /v1/operator/autopilot/health` | [operator/autopilot](https://developer.hashicorp.com/nomad/api-docs/operator/autopilot) |
| [autopilot_set_configuration][nomadpy.operator.Operator.autopilot_set_configuration] | AutopilotSetConfiguration | `PUT /v1/operator/autopilot/configuration` | [operator/autopilot](https://developer.hashicorp.com/nomad/api-docs/operator/autopilot) |
| [license_get][nomadpy.operator.Operator.license_get] | LicenseGet | `GET /v1/operator/license` | [operator/license](https://developer.hashicorp.com/nomad/api-docs/operator/license) Enterprise |
| [metrics][nomadpy.operator.Operator.metrics] | Metrics | `GET /v1/metrics` | [metrics](https://developer.hashicorp.com/nomad/api-docs/metrics) |
| [metrics_summary][nomadpy.operator.Operator.metrics_summary] | MetricsSummary | `GET /v1/metrics` | [metrics](https://developer.hashicorp.com/nomad/api-docs/metrics) |
| [raft_get_configuration][nomadpy.operator.Operator.raft_get_configuration] | RaftGetConfiguration | `GET /v1/operator/raft/configuration` | [operator/raft](https://developer.hashicorp.com/nomad/api-docs/operator/raft) |
| [raft_remove_peer_by_address][nomadpy.operator.Operator.raft_remove_peer_by_address] | RaftRemovePeerByAddress | `DELETE /v1/operator/raft/peer` | [operator/raft](https://developer.hashicorp.com/nomad/api-docs/operator/raft) |
| [raft_remove_peer_by_id][nomadpy.operator.Operator.raft_remove_peer_by_id] | RaftRemovePeerByID | `DELETE /v1/operator/raft/peer` | [operator/raft](https://developer.hashicorp.com/nomad/api-docs/operator/raft) |
| [raft_transfer_leadership_by_address][nomadpy.operator.Operator.raft_transfer_leadership_by_address] | RaftTransferLeadershipByAddress | `PUT /v1/operator/raft/transfer-leadership` | [operator/raft](https://developer.hashicorp.com/nomad/api-docs/operator/raft) |
| [raft_transfer_leadership_by_id][nomadpy.operator.Operator.raft_transfer_leadership_by_id] | RaftTransferLeadershipByID | `PUT /v1/operator/raft/transfer-leadership` | [operator/raft](https://developer.hashicorp.com/nomad/api-docs/operator/raft) |
| [scheduler_cas_configuration][nomadpy.operator.Operator.scheduler_cas_configuration] | SchedulerCASConfiguration | `PUT /v1/operator/scheduler/configuration` | [operator/scheduler](https://developer.hashicorp.com/nomad/api-docs/operator/scheduler) |
| [scheduler_get_configuration][nomadpy.operator.Operator.scheduler_get_configuration] | SchedulerGetConfiguration | `GET /v1/operator/scheduler/configuration` | [operator/scheduler](https://developer.hashicorp.com/nomad/api-docs/operator/scheduler) |
| [scheduler_set_configuration][nomadpy.operator.Operator.scheduler_set_configuration] | SchedulerSetConfiguration | `PUT /v1/operator/scheduler/configuration` | [operator/scheduler](https://developer.hashicorp.com/nomad/api-docs/operator/scheduler) |
| [upgrade_check_vault_workload_identity][nomadpy.operator.Operator.upgrade_check_vault_workload_identity] | UpgradeCheckVaultWorkloadIdentity | `GET /v1/operator/upgrade-check/vault-workload-identity` | [operator/upgrade-check](https://developer.hashicorp.com/nomad/api-docs/operator/upgrade-check) |
| [utilization][nomadpy.operator.Operator.utilization] | Utilization | `POST /v1/operator/utilization` | [operator/utilization](https://developer.hashicorp.com/nomad/api-docs/operator/utilization) Enterprise |
