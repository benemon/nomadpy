# generated from surface.json: file=tasks.go

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Model
from . import constraint as _constraint
from . import consul as _consul
from . import csi as _csi
from . import jobs as _jobs
from . import nodes as _nodes
from . import resources as _resources
from . import scaling as _scaling
from . import services as _services
from . import task_sched as _task_sched


RESTART_POLICY_MODE_DELAY = "delay"
RESTART_POLICY_MODE_FAIL = "fail"
RECONCILE_OPTION_KEEP_ORIGINAL = "keep_original"
RECONCILE_OPTION_KEEP_REPLACEMENT = "keep_replacement"
RECONCILE_OPTION_BEST_SCORE = "best_score"
RECONCILE_OPTION_LONGEST_RUNNING = "longest_running"
VOLUME_MOUNT_PROPAGATION_PRIVATE = "private"
VOLUME_MOUNT_PROPAGATION_HOST_TO_TASK = "host-to-task"
VOLUME_MOUNT_PROPAGATION_BIDIRECTIONAL = "bidirectional"
TASK_LIFECYCLE_HOOK_PRESTART = "prestart"
TASK_LIFECYCLE_HOOK_POSTSTART = "poststart"
TASK_LIFECYCLE_HOOK_POSTSTOP = "poststop"
TASK_SETUP = "Task Setup"
TASK_SETUP_FAILURE = "Setup Failure"
TASK_DRIVER_FAILURE = "Driver Failure"
TASK_DRIVER_MESSAGE = "Driver"
TASK_RECEIVED = "Received"
TASK_FAILED_VALIDATION = "Failed Validation"
TASK_STARTED = "Started"
TASK_TERMINATED = "Terminated"
TASK_KILLING = "Killing"
TASK_KILLED = "Killed"
TASK_RESTARTING = "Restarting"
TASK_NOT_RESTARTING = "Not Restarting"
TASK_DOWNLOADING_ARTIFACTS = "Downloading Artifacts"
TASK_ARTIFACT_DOWNLOAD_FAILED = "Failed Artifact Download"
TASK_SIBLING_FAILED = "Sibling Task Failed"
TASK_SIGNALING = "Signaling"
TASK_RESTART_SIGNAL = "Restart Signaled"
TASK_LEADER_DEAD = "Leader Task Dead"
TASK_BUILDING_TASK_DIR = "Building Task Directory"
TASK_CLIENT_RECONNECTED = "Reconnected"
CSI_PLUGIN_TYPE_NODE = "node"
CSI_PLUGIN_TYPE_CONTROLLER = "controller"
CSI_PLUGIN_TYPE_MONOLITH = "monolith"


@dataclass
class Action(Model):
    name: str = ""
    command: str = ""
    args: list[str] | None = None


@dataclass
class Affinity(Model):
    l_target: str = ""
    r_target: str = ""
    operand: str = ""
    weight: int | None = None


@dataclass
class AllocCheckStatus(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    check: str = ""
    group: str = ""
    mode: str = ""
    output: str = ""
    service: str = ""
    task: str = ""
    status: str = ""
    status_code: int = 0
    timestamp: int = 0


@dataclass
class AllocResourceUsage(Model):
    resource_usage: ResourceUsage | None = None
    tasks: dict[str, TaskResourceUsage] | None = None
    timestamp: int = 0


@dataclass
class ChangeScript(Model):
    command: str | None = None
    args: list[str] | None = None
    timeout: int | None = None
    fail_on_error: bool | None = None
    run_on_first_render: bool | None = None


@dataclass
class CpuStats(Model):
    system_mode: float = 0.0
    user_mode: float = 0.0
    total_ticks: float = 0.0
    throttled_periods: int = 0
    throttled_time: int = 0
    percent: float = 0.0
    measured: list[str] | None = None


@dataclass
class DisconnectStrategy(Model):
    lost_after: int | None = None
    stop_on_client_after: int | None = None
    replace: bool | None = None
    reconcile: str | None = None


@dataclass
class DispatchPayloadConfig(Model):
    file: str = ""


@dataclass
class EphemeralDisk(Model):
    sticky: bool | None = None
    migrate: bool | None = None
    size_mb: int | None = field(default=None, metadata={'json': 'SizeMB'})


@dataclass
class LogConfig(Model):
    max_files: int | None = None
    max_file_size_mb: int | None = field(default=None, metadata={'json': 'MaxFileSizeMB'})
    enabled: bool | None = None
    disabled: bool | None = None


@dataclass
class MemoryStats(Model):
    rss: int = field(default=0, metadata={'json': 'RSS'})
    cache: int = 0
    swap: int = 0
    usage: int = 0
    max_usage: int = 0
    kernel_usage: int = 0
    kernel_max_usage: int = 0
    measured: list[str] | None = None


@dataclass
class MigrateStrategy(Model):
    max_parallel: int | None = None
    health_check: str | None = None
    min_healthy_time: int | None = None
    healthy_deadline: int | None = None


@dataclass
class ReschedulePolicy(Model):
    attempts: int | None = None
    interval: int | None = None
    delay: int | None = None
    delay_function: str | None = None
    max_delay: int | None = None
    unlimited: bool | None = None


@dataclass
class ResourceUsage(Model):
    memory_stats: MemoryStats | None = None
    cpu_stats: CpuStats | None = None
    device_stats: list[_nodes.DeviceGroupStats] | None = None


@dataclass
class RestartPolicy(Model):
    interval: int | None = None
    attempts: int | None = None
    delay: int | None = None
    mode: str | None = None
    render_templates: bool | None = None


@dataclass
class Secret(Model):
    name: str = ""
    provider: str = ""
    path: str = ""
    config: dict[str, Any] | None = None
    env: dict[str, str] | None = None


@dataclass
class Spread(Model):
    attribute: str = ""
    weight: int | None = None
    spread_target: list[SpreadTarget] | None = None


@dataclass
class SpreadTarget(Model):
    value: str = ""
    percent: int = 0


@dataclass
class Task(Model):
    name: str = ""
    driver: str = ""
    user: str = ""
    lifecycle: TaskLifecycle | None = None
    config: dict[str, Any] | None = None
    constraints: list[_constraint.Constraint] | None = None
    affinities: list[Affinity] | None = None
    env: dict[str, str] | None = None
    services: list[_services.Service] | None = None
    resources: _resources.Resources | None = None
    restart_policy: RestartPolicy | None = None
    meta: dict[str, str] | None = None
    kill_timeout: int | None = None
    log_config: LogConfig | None = None
    artifacts: list[TaskArtifact] | None = None
    vault: Vault | None = None
    consul: _consul.Consul | None = None
    templates: list[Template] | None = None
    dispatch_payload: DispatchPayloadConfig | None = None
    volume_mounts: list[VolumeMount] | None = None
    csi_plugin_config: TaskCSIPluginConfig | None = field(default=None, metadata={'json': 'CSIPluginConfig', 'omitempty': True})
    leader: bool = False
    shutdown_delay: int = 0
    kill_signal: str = ""
    kind: str = ""
    scaling_policies: list[_scaling.ScalingPolicy] | None = None
    secrets: list[Secret] | None = None
    identity: WorkloadIdentity | None = None
    identities: list[WorkloadIdentity] | None = None
    actions: list[Action] | None = None
    schedule: _task_sched.TaskSchedule | None = None


@dataclass
class TaskArtifact(Model):
    getter_source: str | None = None
    getter_options: dict[str, str] | None = None
    getter_headers: dict[str, str] | None = None
    getter_mode: str | None = None
    getter_insecure: bool | None = None
    relative_dest: str | None = None
    chown: bool = False


@dataclass
class TaskCSIPluginConfig(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    type: str = ""
    mount_dir: str = ""
    stage_publish_base_dir: str = ""
    health_timeout: int = 0


@dataclass
class TaskEvent(Model):
    type: str = ""
    time: int = 0
    display_message: str = ""
    details: dict[str, str] | None = None
    message: str = ""
    fails_task: bool = False
    restart_reason: str = ""
    setup_error: str = ""
    driver_error: str = ""
    driver_message: str = ""
    exit_code: int = 0
    signal: int = 0
    kill_reason: str = ""
    kill_timeout: int = 0
    kill_error: str = ""
    start_delay: int = 0
    download_error: str = ""
    validation_error: str = ""
    disk_limit: int = 0
    disk_size: int = 0
    failed_sibling: str = ""
    vault_error: str = ""
    task_signal_reason: str = ""
    task_signal: str = ""
    generic_source: str = ""


@dataclass
class TaskGroup(Model):
    name: str | None = None
    count: int | None = None
    constraints: list[_constraint.Constraint] | None = None
    affinities: list[Affinity] | None = None
    tasks: list[Task] | None = None
    spreads: list[Spread] | None = None
    volumes: dict[str, VolumeRequest] | None = None
    restart_policy: RestartPolicy | None = None
    disconnect: DisconnectStrategy | None = None
    reschedule_policy: ReschedulePolicy | None = None
    ephemeral_disk: EphemeralDisk | None = None
    update: _jobs.UpdateStrategy | None = None
    migrate: MigrateStrategy | None = None
    networks: list[_resources.NetworkResource] | None = None
    meta: dict[str, str] | None = None
    services: list[_services.Service] | None = None
    shutdown_delay: int | None = None
    max_run_duration: int | None = None
    stop_after_client_disconnect: int | None = None
    max_client_disconnect: int | None = None
    scaling: _scaling.ScalingPolicy | None = None
    consul: _consul.Consul | None = None
    prevent_reschedule_on_lost: bool | None = None


@dataclass
class TaskLifecycle(Model):
    hook: str = ""
    sidecar: bool = False


@dataclass
class TaskResourceUsage(Model):
    resource_usage: ResourceUsage | None = None
    timestamp: int = 0
    pids: dict[str, ResourceUsage] | None = None


@dataclass
class TaskState(Model):
    state: str = ""
    failed: bool = False
    restarts: int = 0
    last_restart: str = field(default="", metadata={'time': True})
    started_at: str = field(default="", metadata={'time': True})
    finished_at: str = field(default="", metadata={'time': True})
    events: list[TaskEvent] | None = None


@dataclass
class Template(Model):
    source_path: str | None = None
    dest_path: str | None = None
    embedded_tmpl: str | None = None
    change_mode: str | None = None
    change_script: ChangeScript | None = None
    change_signal: str | None = None
    once: bool | None = None
    splay: int | None = None
    perms: str | None = None
    uid: int | None = None
    gid: int | None = None
    left_delim: str | None = None
    right_delim: str | None = None
    envvars: bool | None = None
    vault_grace: int | None = None
    wait: WaitConfig | None = None
    err_missing_key: bool | None = None


@dataclass
class Vault(Model):
    policies: list[str] | None = None
    role: str = ""
    namespace: str | None = None
    cluster: str = ""
    env: bool | None = None
    disable_file: bool | None = None
    change_mode: str | None = None
    change_signal: str | None = None
    allow_token_expiration: bool | None = None


@dataclass
class VolumeMount(Model):
    volume: str | None = None
    destination: str | None = None
    read_only: bool | None = None
    propagation_mode: str | None = None
    se_linux_label: str | None = field(default=None, metadata={'json': 'SELinuxLabel'})


@dataclass
class VolumeRequest(Model):
    name: str = ""
    type: str = ""
    source: str = ""
    read_only: bool = False
    sticky: bool = False
    access_mode: str = ""
    attachment_mode: str = ""
    mount_options: _csi.CSIMountOptions | None = None
    per_alloc: bool = False


@dataclass
class WaitConfig(Model):
    min: int | None = None
    max: int | None = None


@dataclass
class WorkloadIdentity(Model):
    name: str = ""
    audience: list[str] | None = None
    change_mode: str = ""
    change_signal: str = ""
    env: bool = False
    file: bool = False
    filepath: str = ""
    service_name: str = ""
    ttl: int = field(default=0, metadata={'json': 'TTL'})
    extra_claims: list[str] | None = None

# end generated
