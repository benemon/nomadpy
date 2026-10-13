from __future__ import annotations

import base64
import http.client
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from .error_unexpected_response import UnexpectedResponseError

DEFAULT_ADDRESS = "http://127.0.0.1:4646"
ALL_NAMESPACES_NAMESPACE = "*"


@dataclass
class QueryOptions:
    """QueryOptions are used to parameterise a query."""

    region: str = ""
    namespace: str = ""
    allow_stale: bool = False
    wait_index: int = 0
    wait_time: timedelta | None = None
    prefix: str = ""
    params: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    auth_token: str = ""
    filter: str = ""
    per_page: int = 0
    next_token: str = ""
    reverse: bool = False


@dataclass
class WriteOptions:
    """WriteOptions are used to parameterise a write."""

    region: str = ""
    namespace: str = ""
    auth_token: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    idempotency_token: str = ""


@dataclass
class QueryMeta:
    """QueryMeta is used to return meta data about a query."""

    last_index: int = 0
    last_contact: timedelta = timedelta(0)
    known_leader: bool = False
    request_time: timedelta = timedelta(0)
    next_token: str = ""


@dataclass
class WriteMeta:
    """WriteMeta is used to return meta data about a write."""

    last_index: int = 0
    request_time: timedelta = timedelta(0)


@dataclass
class HttpBasicAuth:
    username: str
    password: str = ""


@dataclass
class TLSConfig:
    """TLSConfig contains the parameters needed to configure TLS on the HTTP client."""

    ca_cert: str = ""
    ca_path: str = ""
    client_cert: str = ""
    client_key: str = ""
    tls_server_name: str = ""
    insecure: bool = False


@dataclass
class Config:
    """Config is used to configure the creation of a client."""

    address: str = ""
    region: str = ""
    secret_id: str = ""
    namespace: str = ""
    http_auth: HttpBasicAuth | None = None
    wait_time: timedelta | None = None
    tls_config: TLSConfig = field(default_factory=TLSConfig)
    headers: dict[str, str] = field(default_factory=dict)


def default_config() -> Config:
    """default_config returns a default configuration for the client, read from the NOMAD_* environment."""
    config = Config(address=DEFAULT_ADDRESS)
    env = os.environ
    if v := env.get("NOMAD_ADDR"):
        config.address = v
    if v := env.get("NOMAD_REGION"):
        config.region = v
    if v := env.get("NOMAD_NAMESPACE"):
        config.namespace = v
    if auth := env.get("NOMAD_HTTP_AUTH"):
        username, _, password = auth.partition(":")
        config.http_auth = HttpBasicAuth(username, password)
    tls = config.tls_config
    if v := env.get("NOMAD_CACERT"):
        tls.ca_cert = v
    if v := env.get("NOMAD_CAPATH"):
        tls.ca_path = v
    if v := env.get("NOMAD_CLIENT_CERT"):
        tls.client_cert = v
    if v := env.get("NOMAD_CLIENT_KEY"):
        tls.client_key = v
    if v := env.get("NOMAD_TLS_SERVER_NAME"):
        tls.tls_server_name = v
    if v := env.get("NOMAD_SKIP_VERIFY"):
        # Go's strconv.ParseBool accepts these spellings and ignores anything else.
        if v in ("1", "t", "T", "TRUE", "true", "True"):
            tls.insecure = True
        elif v in ("0", "f", "F", "FALSE", "false", "False"):
            tls.insecure = False
    if v := env.get("NOMAD_TOKEN"):
        config.secret_id = v
    return config


def _ssl_context(tls: TLSConfig) -> ssl.SSLContext:
    if bool(tls.client_cert) != bool(tls.client_key):
        raise ValueError("Both client cert and client key must be provided")
    ctx = ssl.create_default_context(cafile=tls.ca_cert or None, capath=tls.ca_path or None)
    if tls.client_cert:
        ctx.load_cert_chain(tls.client_cert, tls.client_key)
    if tls.insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


class _ServerNameHTTPSHandler(urllib.request.HTTPSHandler):
    """Verifies the certificate against a fixed server name instead of the URL host, like Go's tls.Config.ServerName."""

    def __init__(self, context: ssl.SSLContext, server_name: str):
        super().__init__(context=context)
        self._server_name = server_name

    def https_open(self, req):
        server_name = self._server_name

        class Connection(http.client.HTTPSConnection):
            def connect(self):
                http.client.HTTPConnection.connect(self)
                self.sock = self._context.wrap_socket(self.sock, server_hostname=server_name)

        return self.do_open(Connection, req, context=self._context)


def _msec(d: timedelta) -> str:
    return f"{int(d.total_seconds() * 1000)}ms"


def _parse_index(headers, name: str) -> int:
    try:
        return int(headers.get(name, ""))
    except ValueError:
        return 0


class Client:
    """Client provides a client to the Nomad API."""

    def __init__(self, config: Config | None = None):
        if config is None:
            config = default_config()
        if not config.address:
            config.address = default_config().address
        self.config = config
        self._url = urllib.parse.urlsplit(config.address)
        if self._url.scheme not in ("http", "https"):
            raise ValueError(f"invalid address '{config.address}': unsupported scheme")
        self._netloc = self._url.netloc.rpartition("@")[2]
        handlers = []
        if self._url.scheme == "https":
            ctx = _ssl_context(config.tls_config)
            if config.tls_config.tls_server_name:
                handlers.append(_ServerNameHTTPSHandler(ctx, config.tls_config.tls_server_name))
            else:
                handlers.append(urllib.request.HTTPSHandler(context=ctx))
        self._opener = urllib.request.build_opener(*handlers)

        self.acl_auth = ACLAuth(self)
        self.acl_auth_methods = ACLAuthMethods(self)
        self.acl_binding_rules = ACLBindingRules(self)
        self.acl_identity = ACLIdentity(self)
        self.acl_policies = ACLPolicies(self)
        self.acl_roles = ACLRoles(self)
        self.acl_tokens = ACLTokens(self)
        self.deployments = Deployments(self)
        self.evaluations = Evaluations(self)
        self.jobs = Jobs(self)
        self.namespaces = Namespaces(self)
        self.regions = Regions(self)
        self.status = Status(self)

    def address(self) -> str:
        return self.config.address

    def set_region(self, region: str) -> None:
        self.config.region = region

    def set_namespace(self, namespace: str) -> None:
        self.config.namespace = namespace

    def set_secret_id(self, secret_id: str) -> None:
        self.config.secret_id = secret_id

    def query(self, endpoint: str, q: QueryOptions | None = None) -> tuple[Any, QueryMeta]:
        return self._query("GET", endpoint, None, q)

    def put_query(self, endpoint: str, body: Any, q: QueryOptions | None = None) -> tuple[Any, QueryMeta]:
        return self._query("PUT", endpoint, body, q)

    def post_query(self, endpoint: str, body: Any, q: QueryOptions | None = None) -> tuple[Any, QueryMeta]:
        return self._query("POST", endpoint, body, q)

    def put(self, endpoint: str, body: Any, w: WriteOptions | None = None) -> tuple[Any, WriteMeta]:
        return self._write("PUT", endpoint, body, w)

    def post(self, endpoint: str, body: Any, w: WriteOptions | None = None) -> tuple[Any, WriteMeta]:
        return self._write("POST", endpoint, body, w)

    def delete(self, endpoint: str, body: Any = None, w: WriteOptions | None = None) -> tuple[Any, WriteMeta]:
        return self._write("DELETE", endpoint, body, w)

    def _query(self, method: str, endpoint: str, body: Any, q: QueryOptions | None) -> tuple[Any, QueryMeta]:
        params, headers, token = self._base_request(endpoint)
        if q is not None:
            if q.region:
                params["region"] = q.region
            if q.namespace:
                params["namespace"] = q.namespace
            if q.auth_token:
                token = q.auth_token
            if q.allow_stale:
                params["stale"] = ""
            if q.wait_index:
                params["index"] = str(q.wait_index)
            if q.wait_time:
                params["wait"] = _msec(q.wait_time)
            if q.prefix:
                params["prefix"] = q.prefix
            if q.filter:
                params["filter"] = q.filter
            if q.per_page:
                params["per_page"] = str(q.per_page)
            if q.next_token:
                params["next_token"] = q.next_token
            if q.reverse:
                params["reverse"] = "true"
            params.update(q.params)
            headers.update(q.headers)
        rtt, resp_headers, data = self._do(method, endpoint, params, headers, token, body)
        qm = QueryMeta(
            last_index=_parse_index(resp_headers, "X-Nomad-Index"),
            last_contact=timedelta(milliseconds=_parse_index(resp_headers, "X-Nomad-LastContact")),
            known_leader=resp_headers.get("X-Nomad-KnownLeader") == "true",
            request_time=rtt,
            next_token=resp_headers.get("X-Nomad-NextToken", ""),
        )
        return _decode(data), qm

    def _write(self, method: str, endpoint: str, body: Any, w: WriteOptions | None) -> tuple[Any, WriteMeta]:
        params, headers, token = self._base_request(endpoint)
        if w is not None:
            if w.region:
                params["region"] = w.region
            if w.namespace:
                params["namespace"] = w.namespace
            if w.auth_token:
                token = w.auth_token
            if w.idempotency_token:
                params["idempotency_token"] = w.idempotency_token
            headers.update(w.headers)
        rtt, resp_headers, data = self._do(method, endpoint, params, headers, token, body)
        wm = WriteMeta(last_index=_parse_index(resp_headers, "X-Nomad-Index"), request_time=rtt)
        return _decode(data), wm

    def _base_request(self, endpoint: str) -> tuple[dict[str, str], dict[str, str], str]:
        params: dict[str, str] = {}
        if self.config.region:
            params["region"] = self.config.region
        if self.config.namespace:
            params["namespace"] = self.config.namespace
        if self.config.wait_time:
            params["wait"] = _msec(self.config.wait_time)
        params.update(urllib.parse.parse_qsl(urllib.parse.urlsplit(endpoint).query))
        return params, dict(self.config.headers), self.config.secret_id

    def _do(self, method: str, endpoint: str, params: dict[str, str], headers: dict[str, str], token: str, body: Any):
        path = urllib.parse.urlsplit(endpoint).path
        url = urllib.parse.urlunsplit((self._url.scheme, self._netloc, path, urllib.parse.urlencode(params), ""))
        if self._url.username is not None:
            auth = f"{self._url.username}:{self._url.password or ''}"
        elif self.config.http_auth is not None:
            auth = f"{self.config.http_auth.username}:{self.config.http_auth.password}"
        else:
            auth = ""
        if auth:
            headers["Authorization"] = "Basic " + base64.b64encode(auth.encode()).decode()
        if token:
            headers["X-Nomad-Token"] = token
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        start = time.monotonic()
        try:
            resp = self._opener.open(req)
        except urllib.error.HTTPError as e:
            resp = e
        rtt = timedelta(seconds=time.monotonic() - start)
        with resp:
            raw = resp.read()
        if resp.status != 200:
            raise UnexpectedResponseError(resp.status, resp.reason, raw.decode(errors="replace").strip(), (200,))
        return rtt, resp.headers, raw


def _decode(raw: bytes) -> Any:
    if not raw:
        return None
    return json.loads(raw)


# Service modules import the option types above, so they can only be imported once those exist.
from .acl import ACLAuth, ACLAuthMethods, ACLBindingRules, ACLIdentity, ACLPolicies, ACLRoles, ACLTokens  # noqa: E402
from .deployments import Deployments  # noqa: E402
from .evaluations import Evaluations  # noqa: E402
from .jobs import Jobs  # noqa: E402
from .namespace import Namespaces  # noqa: E402
from .regions import Regions  # noqa: E402
from .status import Status  # noqa: E402
