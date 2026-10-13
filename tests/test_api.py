import json
import os
import threading
import urllib.parse
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from nomadpy import Client, Config, HttpBasicAuth, QueryOptions, UnexpectedResponseError, WriteOptions, default_config


class _Recorder(BaseHTTPRequestHandler):
    """Records the last request and answers 200 with fixed Nomad metadata headers."""

    last = None

    def do_GET(self):
        self._record()

    def do_PUT(self):
        self._record()

    def do_POST(self):
        self._record()

    def do_DELETE(self):
        self._record()

    def _record(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        url = urllib.parse.urlsplit(self.path)
        _Recorder.last = {
            "method": self.command,
            "path": url.path,
            "query": urllib.parse.parse_qs(url.query, keep_blank_values=True),
            "headers": dict(self.headers),
            "body": json.loads(body) if body else None,
        }
        payload = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Nomad-Index", "42")
        self.send_header("X-Nomad-LastContact", "7")
        self.send_header("X-Nomad-KnownLeader", "true")
        self.send_header("X-Nomad-NextToken", "abc")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


@pytest.fixture
def recorder():
    server = HTTPServer(("127.0.0.1", 0), _Recorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_default_config_reads_environment(monkeypatch):
    env = {
        "NOMAD_ADDR": "https://nomad.example:4646",
        "NOMAD_REGION": "eu",
        "NOMAD_NAMESPACE": "team",
        "NOMAD_HTTP_AUTH": "user:pass:word",
        "NOMAD_CACERT": "/ca.pem",
        "NOMAD_CAPATH": "/cas",
        "NOMAD_CLIENT_CERT": "/cert.pem",
        "NOMAD_CLIENT_KEY": "/key.pem",
        "NOMAD_TLS_SERVER_NAME": "server.global.nomad",
        "NOMAD_SKIP_VERIFY": "1",
        "NOMAD_TOKEN": "secret",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    c = default_config()
    assert c.address == "https://nomad.example:4646"
    assert c.region == "eu"
    assert c.namespace == "team"
    assert c.http_auth == HttpBasicAuth("user", "pass:word")
    assert c.secret_id == "secret"
    t = c.tls_config
    assert (t.ca_cert, t.ca_path, t.client_cert, t.client_key) == ("/ca.pem", "/cas", "/cert.pem", "/key.pem")
    assert t.tls_server_name == "server.global.nomad"
    assert t.insecure is True


def test_default_config_defaults(monkeypatch):
    for k in list(os.environ):
        if k.startswith("NOMAD_"):
            monkeypatch.delenv(k)
    c = default_config()
    assert c.address == "http://127.0.0.1:4646"
    assert c.http_auth is None
    assert c.tls_config.insecure is False


@pytest.mark.parametrize("value,expected", [("true", True), ("T", True), ("0", False), ("yes", False)])
def test_skip_verify_parses_like_go(monkeypatch, value, expected):
    monkeypatch.setenv("NOMAD_SKIP_VERIFY", value)
    assert default_config().tls_config.insecure is expected


def test_http_auth_without_password(monkeypatch):
    monkeypatch.setenv("NOMAD_HTTP_AUTH", "user")
    assert default_config().http_auth == HttpBasicAuth("user", "")


def test_query_encodes_options_and_parses_meta(recorder):
    client = Client(Config(address=recorder, region="r0", namespace="ns0", secret_id="tok0",
                           wait_time=timedelta(seconds=2), headers={"X-Custom": "1"}))
    q = QueryOptions(region="r1", namespace="ns1", allow_stale=True, wait_index=12,
                     wait_time=timedelta(seconds=1.5), prefix="p", filter="f == 1", per_page=5,
                     next_token="nt", reverse=True, params={"x": "y"}, headers={"H": "v"}, auth_token="tok1")
    resp, qm = client.query("/v1/jobs?extra=1", q)
    assert resp == {"ok": True}
    last = _Recorder.last
    assert last["method"] == "GET"
    assert last["path"] == "/v1/jobs"
    assert last["query"] == {
        "region": ["r1"], "namespace": ["ns1"], "stale": [""], "index": ["12"], "wait": ["1500ms"],
        "prefix": ["p"], "filter": ["f == 1"], "per_page": ["5"], "next_token": ["nt"],
        "reverse": ["true"], "x": ["y"], "extra": ["1"],
    }
    assert last["headers"]["X-Nomad-Token"] == "tok1"
    assert last["headers"]["X-Custom"] == "1"
    assert last["headers"]["H"] == "v"
    assert qm.last_index == 42
    assert qm.last_contact == timedelta(milliseconds=7)
    assert qm.known_leader is True
    assert qm.next_token == "abc"
    assert qm.request_time > timedelta(0)


def test_query_uses_config_defaults(recorder):
    client = Client(Config(address=recorder, region="r0", namespace="ns0", secret_id="tok0",
                           wait_time=timedelta(seconds=2)))
    client.query("/v1/jobs")
    last = _Recorder.last
    assert last["query"] == {"region": ["r0"], "namespace": ["ns0"], "wait": ["2000ms"]}
    assert last["headers"]["X-Nomad-Token"] == "tok0"


def test_write_encodes_options_and_body(recorder):
    client = Client(Config(address=recorder, secret_id="tok0"))
    w = WriteOptions(region="r1", namespace="ns1", auth_token="tok1", idempotency_token="idem", headers={"H": "v"})
    resp, wm = client.put("/v1/namespace/x", {"Name": "x"}, w)
    last = _Recorder.last
    assert last["method"] == "PUT"
    assert last["body"] == {"Name": "x"}
    assert last["query"] == {"region": ["r1"], "namespace": ["ns1"], "idempotency_token": ["idem"]}
    assert last["headers"]["X-Nomad-Token"] == "tok1"
    assert last["headers"]["H"] == "v"
    assert wm.last_index == 42
    assert wm.request_time > timedelta(0)

    client.delete("/v1/namespace/x")
    assert _Recorder.last["method"] == "DELETE"
    assert _Recorder.last["body"] is None
    client.post("/v1/jobs", {"Job": {}})
    assert _Recorder.last["method"] == "POST"


def test_basic_auth_from_url_and_config(recorder):
    host = recorder.removeprefix("http://")
    Client(Config(address=f"http://u:p@{host}")).query("/v1/jobs")
    assert _Recorder.last["headers"]["Authorization"] == "Basic dTpw"
    Client(Config(address=recorder, http_auth=HttpBasicAuth("u", "p"))).query("/v1/jobs")
    assert _Recorder.last["headers"]["Authorization"] == "Basic dTpw"


def test_setters(recorder):
    client = Client(Config(address=recorder))
    client.set_region("r9")
    client.set_namespace("ns9")
    client.set_secret_id("tok9")
    client.query("/v1/jobs")
    assert _Recorder.last["query"] == {"region": ["r9"], "namespace": ["ns9"]}
    assert _Recorder.last["headers"]["X-Nomad-Token"] == "tok9"
    assert client.address() == recorder


def test_unsupported_scheme():
    with pytest.raises(ValueError):
        Client(Config(address="unix:///tmp/nomad.sock"))


def test_blocking_query(client):
    # Empty tables report index 0, so write first to guarantee a non-zero index to block on.
    _, wm = client.put("/v1/namespace/nomadpy-block", {"Name": "nomadpy-block"})
    _, qm = client.query("/v1/namespaces")
    assert qm.known_leader is True
    assert qm.last_index >= wm.last_index > 0
    _, blocked = client.query("/v1/namespaces", QueryOptions(wait_index=qm.last_index, wait_time=timedelta(seconds=1)))
    assert blocked.request_time >= timedelta(seconds=1)
    assert blocked.last_index == qm.last_index


def test_stale_query(client):
    resp, qm = client.query("/v1/jobs", QueryOptions(allow_stale=True))
    assert resp == []
    assert qm.last_contact >= timedelta(0)


def test_write_then_read_then_delete(client):
    resp, wm = client.put("/v1/namespace/nomadpy-t1", {"Name": "nomadpy-t1", "Description": "d"})
    assert wm.last_index > 0
    ns, qm = client.query("/v1/namespace/nomadpy-t1")
    assert ns["Name"] == "nomadpy-t1"
    assert ns["Description"] == "d"
    assert qm.last_index >= wm.last_index
    client.delete("/v1/namespace/nomadpy-t1")
    with pytest.raises(UnexpectedResponseError) as e:
        client.query("/v1/namespace/nomadpy-t1")
    assert e.value.status_code == 404


@pytest.mark.parametrize("path", ["/v1/quotas", "/v1/sentinel/policies", "/v1/recommendations"])
def test_enterprise_endpoints_on_community(client, path):
    with pytest.raises(UnexpectedResponseError) as e:
        client.query(path)
    assert e.value.status_code == 501
    assert e.value.body == "Nomad Enterprise only endpoint"
    assert str(e.value) == "Unexpected response code: 501 (Nomad Enterprise only endpoint)"


def test_license_on_community(client):
    with pytest.raises(UnexpectedResponseError) as e:
        client.query("/v1/operator/license")
    assert e.value.status_code == 204
    assert e.value.body == ""


def test_license_on_enterprise(ent_client):
    resp, _ = ent_client.query("/v1/operator/license")
    assert resp["License"]["Product"] == "nomad"
