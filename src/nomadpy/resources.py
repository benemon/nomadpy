from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Model
from . import constraint as _constraint
from . import tasks as _tasks


@dataclass
class Attribute(Model):
    float_val: float | None = field(default=None, metadata={'json': 'Float', 'omitempty': True})
    int_val: int | None = field(default=None, metadata={'json': 'Int', 'omitempty': True})
    string_val: str | None = field(default=None, metadata={'json': 'String', 'omitempty': True})
    bool_val: bool | None = field(default=None, metadata={'json': 'Bool', 'omitempty': True})
    unit: str = ""


@dataclass
class CNIConfig(Model):
    args: dict[str, str] | None = None


@dataclass
class DNSConfig(Model):
    servers: list[str] | None = None
    searches: list[str] | None = None
    options: list[str] | None = None


@dataclass
class NUMAResource(Model):
    affinity: str = ""
    devices: list[str] | None = None


@dataclass
class NetworkResource(Model):
    mode: str = ""
    device: str = ""
    cidr: str = field(default="", metadata={'json': 'CIDR'})
    ip: str = field(default="", metadata={'json': 'IP'})
    dns: DNSConfig | None = field(default=None, metadata={'json': 'DNS'})
    reserved_ports: list[Port] | None = None
    dynamic_ports: list[Port] | None = None
    hostname: str = ""
    m_bits: int | None = None
    cni: CNIConfig | None = field(default=None, metadata={'json': 'CNI'})


@dataclass
class NodeDevice(Model):
    id: str = field(default="", metadata={'json': 'ID'})
    healthy: bool = False
    health_description: str = ""
    locality: NodeDeviceLocality | None = None


@dataclass
class NodeDeviceLocality(Model):
    pci_bus_id: str = field(default="", metadata={'json': 'PciBusID'})


@dataclass
class NodeDeviceResource(Model):
    vendor: str = ""
    type: str = ""
    name: str = ""
    instances: list[NodeDevice] | None = None
    attributes: dict[str, Attribute] | None = None


@dataclass
class Port(Model):
    label: str = ""
    value: int = 0
    to: int = 0
    host_network: str = ""
    ignore_collision: bool = False


@dataclass
class RequestedDevice(Model):
    name: str = ""
    count: int | None = None
    constraints: list[_constraint.Constraint] | None = None
    affinities: list[_tasks.Affinity] | None = None


@dataclass
class Resources(Model):
    cpu: int | None = field(default=None, metadata={'json': 'CPU'})
    cores: int | None = None
    memory_mb: int | None = field(default=None, metadata={'json': 'MemoryMB'})
    memory_max_mb: int | None = field(default=None, metadata={'json': 'MemoryMaxMB'})
    disk_mb: int | None = field(default=None, metadata={'json': 'DiskMB'})
    networks: list[NetworkResource] | None = None
    devices: list[RequestedDevice] | None = None
    numa: NUMAResource | None = field(default=None, metadata={'json': 'NUMA'})
    secrets_mb: int | None = field(default=None, metadata={'json': 'SecretsMB'})
    iops: int | None = field(default=None, metadata={'json': 'IOPS'})

