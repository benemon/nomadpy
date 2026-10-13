import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request

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
    probes the leader endpoint over plain HTTP.
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
            with urllib.request.urlopen(f"{addr}/v1/status/leader", timeout=2) as resp:
                return resp.status == 200 and resp.read() not in (b"", b'""')

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


@pytest.fixture
def ent_client(ent_agent):
    return Client(Config(address=ent_agent))
