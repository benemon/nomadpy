import os
from datetime import timedelta

import pytest

from nomadpy import Client, Config, HttpBasicAuth, QueryOptions, UnexpectedResponseError, WriteOptions, default_config


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
    client = Client(Config(address=recorder.address, region="r0", namespace="ns0", secret_id="tok0",
                           wait_time=timedelta(seconds=2), headers={"X-Custom": "1"}))
    q = QueryOptions(region="r1", namespace="ns1", allow_stale=True, wait_index=12,
                     wait_time=timedelta(seconds=1.5), prefix="p", filter="f == 1", per_page=5,
                     next_token="nt", reverse=True, params={"x": "y"}, headers={"H": "v"}, auth_token="tok1")
    resp, qm = client.query("/v1/jobs?extra=1", q)
    assert resp == {"ok": True}
    last = recorder.last
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
    client = Client(Config(address=recorder.address, region="r0", namespace="ns0", secret_id="tok0",
                           wait_time=timedelta(seconds=2)))
    client.query("/v1/jobs")
    last = recorder.last
    assert last["query"] == {"region": ["r0"], "namespace": ["ns0"], "wait": ["2000ms"]}
    assert last["headers"]["X-Nomad-Token"] == "tok0"


def test_write_encodes_options_and_body(recorder):
    client = Client(Config(address=recorder.address, secret_id="tok0"))
    w = WriteOptions(region="r1", namespace="ns1", auth_token="tok1", idempotency_token="idem", headers={"H": "v"})
    resp, wm = client.put("/v1/namespace/x", {"Name": "x"}, w)
    last = recorder.last
    assert last["method"] == "PUT"
    assert last["body"] == {"Name": "x"}
    assert last["query"] == {"region": ["r1"], "namespace": ["ns1"], "idempotency_token": ["idem"]}
    assert last["headers"]["X-Nomad-Token"] == "tok1"
    assert last["headers"]["H"] == "v"
    assert wm.last_index == 42
    assert wm.request_time > timedelta(0)

    client.delete("/v1/namespace/x")
    assert recorder.last["method"] == "DELETE"
    assert recorder.last["body"] is None
    client.post("/v1/jobs", {"Job": {}})
    assert recorder.last["method"] == "POST"


def test_basic_auth_from_url_and_config(recorder):
    host = recorder.address.removeprefix("http://")
    Client(Config(address=f"http://u:p@{host}")).query("/v1/jobs")
    assert recorder.last["headers"]["Authorization"] == "Basic dTpw"
    Client(Config(address=recorder.address, http_auth=HttpBasicAuth("u", "p"))).query("/v1/jobs")
    assert recorder.last["headers"]["Authorization"] == "Basic dTpw"


def test_setters(recorder):
    client = Client(Config(address=recorder.address))
    client.set_region("r9")
    client.set_namespace("ns9")
    client.set_secret_id("tok9")
    client.query("/v1/jobs")
    assert recorder.last["query"] == {"region": ["r9"], "namespace": ["ns9"]}
    assert recorder.last["headers"]["X-Nomad-Token"] == "tok9"
    assert client.address() == recorder.address


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
    assert isinstance(resp, list)
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


def test_options_repr_omits_credentials():
    config = Config(address="http://127.0.0.1:1", secret_id="SECRET-ID", http_auth=HttpBasicAuth("user", "PASS-WORD"))
    for text in (repr(config), str(config), repr(QueryOptions(auth_token="AUTH-TOKEN")), repr(WriteOptions(auth_token="AUTH-TOKEN"))):
        assert "SECRET-ID" not in text and "PASS-WORD" not in text and "AUTH-TOKEN" not in text


def test_unsupported_scheme_error_omits_userinfo():
    with pytest.raises(ValueError) as e:
        Client(Config(address="ftp://user:PASS-WORD@host:1"))
    assert "PASS-WORD" not in str(e.value) and "user" not in str(e.value) and "ftp://host:1" in str(e.value)
