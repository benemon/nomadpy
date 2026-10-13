from __future__ import annotations

from dataclasses import dataclass, field

from .models import Model


@dataclass
class AutopilotConfiguration(Model):
    """AutopilotConfiguration; EnableRedundancyZones, DisableUpgradeMigration and EnableCustomUpgrades are Enterprise."""

    cleanup_dead_servers: bool = False
    last_contact_threshold: int = field(default=0, metadata={"duration": "string", "zero": "0s"})
    max_trailing_logs: int = 0
    min_quorum: int = 0
    server_stabilization_time: int = field(default=0, metadata={"duration": "string", "zero": "0s"})
    enable_redundancy_zones: bool = False
    disable_upgrade_migration: bool = False
    enable_custom_upgrades: bool = False
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ServerHealth(Model):
    id: str = field(default="", metadata={"json": "ID"})
    name: str = ""
    address: str = ""
    serf_status: str = ""
    version: str = ""
    leader: bool = False
    last_contact: int = field(default=0, metadata={"duration": "string", "zero": "0s"})
    last_term: int = 0
    last_index: int = 0
    healthy: bool = False
    voter: bool = False
    stable_since: str = field(default="", metadata={"time": True})


@dataclass
class AutopilotZone(Model):
    servers: list[str] | None = None
    voters: list[str] | None = None
    failure_tolerance: int = 0


@dataclass
class AutopilotZoneUpgradeVersions(Model):
    target_version_voters: list[str] | None = None
    target_version_non_voters: list[str] | None = None
    other_version_voters: list[str] | None = None
    other_version_non_voters: list[str] | None = None


@dataclass
class AutopilotUpgrade(Model):
    status: str = ""
    target_version: str = ""
    target_version_voters: list[str] | None = None
    target_version_non_voters: list[str] | None = None
    target_version_read_replicas: list[str] | None = None
    other_version_voters: list[str] | None = None
    other_version_non_voters: list[str] | None = None
    other_version_read_replicas: list[str] | None = None
    redundancy_zones: dict[str, AutopilotZoneUpgradeVersions] | None = None


@dataclass
class OperatorHealthReply(Model):
    healthy: bool = False
    failure_tolerance: int = 0
    servers: list[ServerHealth] | None = None
    leader: str = ""
    voters: list[str] | None = None
    read_replicas: list[str] | None = field(default=None, metadata={"omitempty": True})
    redundancy_zones: dict[str, AutopilotZone] | None = field(default=None, metadata={"omitempty": True})
    upgrade: AutopilotUpgrade | None = field(default=None, metadata={"omitempty": True})
    optimistic_failure_tolerance: int = field(default=0, metadata={"omitempty": True})
