from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import Model
from . import resources as _resources
from . import tasks as _tasks


@dataclass
class Consul(Model):
    namespace: str = ""
    cluster: str = ""
    partition: str = ""


@dataclass
class ConsulConnect(Model):
    native: bool = False
    gateway: ConsulGateway | None = None
    sidecar_service: ConsulSidecarService | None = None
    sidecar_task: SidecarTask | None = None


@dataclass
class ConsulExposeConfig(Model):
    paths: list[ConsulExposePath] | None = None
    path: list[ConsulExposePath] | None = None


@dataclass
class ConsulExposePath(Model):
    path: str = ""
    protocol: str = ""
    local_path_port: int = 0
    listener_port: str = ""


@dataclass
class ConsulGateway(Model):
    proxy: ConsulGatewayProxy | None = None
    ingress: ConsulIngressConfigEntry | None = None
    terminating: ConsulTerminatingConfigEntry | None = None
    mesh: ConsulMeshConfigEntry | None = None


@dataclass
class ConsulGatewayBindAddress(Model):
    name: str = ""
    address: str = ""
    port: int = 0


@dataclass
class ConsulGatewayProxy(Model):
    connect_timeout: int | None = None
    envoy_gateway_bind_tagged_addresses: bool = False
    envoy_gateway_bind_addresses: dict[str, ConsulGatewayBindAddress] | None = None
    envoy_gateway_no_default_bind: bool = False
    envoy_dns_discovery_type: str = field(default="", metadata={'json': 'EnvoyDNSDiscoveryType'})
    config: dict[str, Any] | None = None


@dataclass
class ConsulGatewayTLSConfig(Model):
    enabled: bool = False
    tls_min_version: str = field(default="", metadata={'json': 'TLSMinVersion'})
    tls_max_version: str = field(default="", metadata={'json': 'TLSMaxVersion'})
    cipher_suites: list[str] | None = None
    sds: ConsulGatewayTLSSDSConfig | None = field(default=None, metadata={'json': 'SDS'})


@dataclass
class ConsulGatewayTLSSDSConfig(Model):
    cluster_name: str = ""
    cert_resource: str = ""


@dataclass
class ConsulHTTPHeaderModifiers(Model):
    add: dict[str, str] | None = None
    set: dict[str, str] | None = None
    remove: list[str] | None = None


@dataclass
class ConsulIngressConfigEntry(Model):
    tls: ConsulGatewayTLSConfig | None = field(default=None, metadata={'json': 'TLS'})
    listeners: list[ConsulIngressListener] | None = None


@dataclass
class ConsulIngressListener(Model):
    port: int = 0
    protocol: str = ""
    services: list[ConsulIngressService] | None = None


@dataclass
class ConsulIngressService(Model):
    name: str = ""
    hosts: list[str] | None = None
    tls: ConsulGatewayTLSConfig | None = field(default=None, metadata={'json': 'TLS'})
    request_headers: ConsulHTTPHeaderModifiers | None = None
    response_headers: ConsulHTTPHeaderModifiers | None = None
    max_connections: int | None = None
    max_pending_requests: int | None = None
    max_concurrent_requests: int | None = None


@dataclass
class ConsulLinkedService(Model):
    name: str = ""
    ca_file: str = field(default="", metadata={'json': 'CAFile'})
    cert_file: str = ""
    key_file: str = ""
    sni: str = field(default="", metadata={'json': 'SNI'})


@dataclass
class ConsulMeshConfigEntry(Model):
    pass


@dataclass
class ConsulMeshGateway(Model):
    mode: str = ""


@dataclass
class ConsulProxy(Model):
    local_service_address: str = ""
    local_service_port: int = 0
    expose: ConsulExposeConfig | None = None
    expose_config: ConsulExposeConfig | None = None
    upstreams: list[ConsulUpstream] | None = None
    transparent_proxy: ConsulTransparentProxy | None = None
    config: dict[str, Any] | None = None


@dataclass
class ConsulSidecarService(Model):
    tags: list[str] | None = None
    port: str = ""
    proxy: ConsulProxy | None = None
    disable_default_tcp_check: bool = field(default=False, metadata={'json': 'DisableDefaultTCPCheck'})
    meta: dict[str, str] | None = None


@dataclass
class ConsulTerminatingConfigEntry(Model):
    services: list[ConsulLinkedService] | None = None


@dataclass
class ConsulTransparentProxy(Model):
    uid: str = field(default="", metadata={'json': 'UID'})
    outbound_port: int = 0
    exclude_inbound_ports: list[str] | None = None
    exclude_outbound_ports: list[int] | None = None
    exclude_outbound_cid_rs: list[str] | None = field(default=None, metadata={'json': 'ExcludeOutboundCIDRs'})
    exclude_ui_ds: list[str] | None = field(default=None, metadata={'json': 'ExcludeUIDs'})
    no_dns: bool = field(default=False, metadata={'json': 'NoDNS'})


@dataclass
class ConsulUpstream(Model):
    destination_name: str = ""
    destination_namespace: str = ""
    destination_peer: str = ""
    destination_partition: str = ""
    destination_type: str = ""
    local_bind_port: int = 0
    datacenter: str = ""
    local_bind_address: str = ""
    local_bind_socket_path: str = ""
    local_bind_socket_mode: str = ""
    mesh_gateway: ConsulMeshGateway | None = None
    config: dict[str, Any] | None = None


@dataclass
class SidecarTask(Model):
    name: str = ""
    driver: str = ""
    user: str = ""
    config: dict[str, Any] | None = None
    env: dict[str, str] | None = None
    resources: _resources.Resources | None = None
    meta: dict[str, str] | None = None
    kill_timeout: int | None = None
    log_config: _tasks.LogConfig | None = None
    shutdown_delay: int | None = None
    kill_signal: str = ""
    volume_mounts: list[_tasks.VolumeMount] | None = None
    identities: list[_tasks.WorkloadIdentity] | None = None

