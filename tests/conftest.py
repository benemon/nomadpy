import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from nomadpy import Client, Config


def free_ports(n):
    socks = [socket.socket() for _ in range(n)]
    for s in socks:
        s.bind(("127.0.0.1", 0))
    ports = [s.getsockname()[1] for s in socks]
    for s in socks:
        s.close()
    return ports


def start_agent(binary, extra_hcl="", env=None, ready=None):
    """Starts a dev agent on free ports and returns (process, http address, workdir).

    `ready` is called with the address until it returns True; the default
    waits over plain HTTP for the dev client node to be ready, so jobs
    registered by tests can be placed immediately.
    """
    http, rpc, serf = free_ports(3)
    workdir = tempfile.mkdtemp(prefix="nomadpy-agent-")
    config = os.path.join(workdir, "agent.hcl")
    with open(config, "w") as f:
        f.write(f"ports {{ http = {http} rpc = {rpc} serf = {serf} }}\n{extra_hcl}")
    log = open(os.path.join(workdir, "agent.log"), "w")
    proc = subprocess.Popen(
        [binary, "agent", "-dev", "-bind", "127.0.0.1", "-config", config, "-log-level", "ERROR"],
        stdout=log,
        stderr=subprocess.STDOUT,
        env={**os.environ, **(env or {})},
    )
    address = f"http://127.0.0.1:{http}"
    if ready is None:
        def ready(addr):
            with urllib.request.urlopen(f"{addr}/v1/nodes", timeout=2) as resp:
                return any(n["Status"] == "ready" for n in json.load(resp))

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            break
        try:
            if ready(address):
                return proc, address, workdir
        except Exception:
            pass
        time.sleep(0.25)
    stop_agent(proc)
    with open(os.path.join(workdir, "agent.log")) as f:
        raise RuntimeError(f"nomad agent did not become ready:\n{f.read()[-2000:]}")


def stop_agent(proc):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def _binary(var):
    path = os.environ.get(var)
    if not path:
        pytest.skip(f"{var} not set")
    if not os.path.isfile(path):
        pytest.skip(f"{var}={path} does not exist")
    return path


@pytest.fixture(scope="session")
def nomad_bin():
    return _binary("NOMADPY_TEST_CE_BIN")


@pytest.fixture(scope="session")
def nomad_agent(nomad_bin):
    proc, address, workdir = start_agent(nomad_bin)
    yield address
    stop_agent(proc)
    shutil.rmtree(workdir, ignore_errors=True)


@pytest.fixture(scope="session")
def ent_agent():
    binary = _binary("NOMADPY_TEST_ENT_BIN")
    license_path = os.environ.get("NOMAD_LICENSE_PATH")
    if not license_path:
        pytest.skip("NOMAD_LICENSE_PATH not set")
    if not os.path.isfile(license_path):
        pytest.skip(f"NOMAD_LICENSE_PATH={license_path} does not exist")
    proc, address, workdir = start_agent(binary, env={"NOMAD_LICENSE_PATH": license_path})
    yield address
    stop_agent(proc)
    shutil.rmtree(workdir, ignore_errors=True)


@pytest.fixture
def client(nomad_agent):
    return Client(Config(address=nomad_agent))


@pytest.fixture(scope="module")
def disposable_client(nomad_bin):
    """A client on an agent of its own, for tests that leave the server in a state other tests cannot share."""
    proc, address, workdir = start_agent(nomad_bin)
    yield Client(Config(address=address))
    stop_agent(proc)
    shutil.rmtree(workdir, ignore_errors=True)


def leader_ready(address):
    with urllib.request.urlopen(f"{address}/v1/status/leader", timeout=2) as resp:
        return resp.status == 200 and resp.read() not in (b"", b'""')


@pytest.fixture(scope="session")
def acl_agent(nomad_bin):
    """A dev agent with ACLs enabled. Node listing needs a token, so readiness is the leader endpoint."""
    proc, address, workdir = start_agent(nomad_bin, "acl { enabled = true }\n", ready=leader_ready)
    yield address
    stop_agent(proc)
    shutil.rmtree(workdir, ignore_errors=True)


@pytest.fixture(scope="session")
def ent_acl_agent():
    """An Enterprise dev agent with ACLs enabled, for the Enterprise features that require them."""
    binary = _binary("NOMADPY_TEST_ENT_BIN")
    license_path = os.environ.get("NOMAD_LICENSE_PATH")
    if not license_path:
        pytest.skip("NOMAD_LICENSE_PATH not set")
    if not os.path.isfile(license_path):
        pytest.skip(f"NOMAD_LICENSE_PATH={license_path} does not exist")
    proc, address, workdir = start_agent(binary, "acl { enabled = true }\n", env={"NOMAD_LICENSE_PATH": license_path}, ready=leader_ready)
    yield address
    stop_agent(proc)
    shutil.rmtree(workdir, ignore_errors=True)


def bootstrap(address):
    """A management-token client for an ACL-enabled agent, returned once the server keyring exists so signing endpoints work."""
    client = Client(Config(address=address))
    token, _ = client.acl_tokens.bootstrap()
    client.set_secret_id(token.secret_id)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        keys, _ = client.query("/v1/operator/keyring/keys")
        if keys:
            return client
        time.sleep(0.25)
    raise RuntimeError("server keyring never initialised")


@pytest.fixture(scope="session")
def ent_acl_client(ent_acl_agent):
    return bootstrap(ent_acl_agent)


@pytest.fixture(scope="session")
def acl_client(acl_agent):
    """A client holding the bootstrap management token of acl_agent."""
    return bootstrap(acl_agent)


@pytest.fixture
def ent_client(ent_agent):
    return Client(Config(address=ent_agent))


def _decode_body(body):
    if not body:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return body.decode(errors="replace")


class Recorder:
    """A local HTTP server that records the last request and answers 200 with fixed Nomad metadata headers.

    `response` is the JSON body returned, or None for an empty body; tests that decode a specific shape set it.
    """

    def __init__(self):
        self.last = None
        self.response = {"ok": True}
        recorder = self

        class Handler(BaseHTTPRequestHandler):
            # A WebSocket client rejects an HTTP/1.0 status line; the recorder answers every request as the server would.
            protocol_version = "HTTP/1.1"

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
                recorder.last = {
                    "method": self.command,
                    "path": urllib.parse.unquote(url.path),
                    "query": urllib.parse.parse_qs(url.query, keep_blank_values=True),
                    "headers": dict(self.headers),
                    "body": _decode_body(body),
                }
                payload = b"" if recorder.response is None else json.dumps(recorder.response).encode()
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

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.address = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture
def recorder():
    r = Recorder()
    yield r
    r.server.shutdown()
