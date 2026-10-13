import os
import shutil
import subprocess
import tempfile
import urllib.error

import pytest

from nomadpy import Client, Config, TLSConfig

from conftest import start_agent, stop_agent


@pytest.fixture(scope="module")
def tls_agent(nomad_bin):
    """A dev agent with HTTPS and client certificate verification, using certs from `nomad tls`."""
    workdir = tempfile.mkdtemp(prefix="nomadpy-tls-")
    subprocess.run([nomad_bin, "tls", "ca", "create"], cwd=workdir, check=True, capture_output=True)
    subprocess.run([nomad_bin, "tls", "cert", "create", "-server"], cwd=workdir, check=True, capture_output=True)
    subprocess.run([nomad_bin, "tls", "cert", "create", "-cli"], cwd=workdir, check=True, capture_output=True)
    paths = {
        "ca": os.path.join(workdir, "nomad-agent-ca.pem"),
        "cert": os.path.join(workdir, "global-cli-nomad.pem"),
        "key": os.path.join(workdir, "global-cli-nomad-key.pem"),
    }
    hcl = f"""
tls {{
  http = true
  rpc = true
  ca_file = "{paths["ca"]}"
  cert_file = "{os.path.join(workdir, "global-server-nomad.pem")}"
  key_file = "{os.path.join(workdir, "global-server-nomad-key.pem")}"
  verify_https_client = true
}}
"""
    tls = TLSConfig(ca_cert=paths["ca"], client_cert=paths["cert"], client_key=paths["key"])

    def ready(address):
        return Client(Config(address=https(address), tls_config=tls)).status.leader() != ""

    proc, address, agent_dir = start_agent(nomad_bin, hcl, ready=ready)
    yield https(address), paths
    stop_agent(proc)
    shutil.rmtree(agent_dir, ignore_errors=True)
    shutil.rmtree(workdir, ignore_errors=True)


def https(address):
    return "https://" + address.removeprefix("http://")


def test_mutual_tls(tls_agent):
    address, p = tls_agent
    client = Client(Config(address=address, tls_config=TLSConfig(ca_cert=p["ca"], client_cert=p["cert"], client_key=p["key"])))
    assert client.status.leader() != ""


def test_ca_path_directory(tls_agent):
    address, p = tls_agent
    cadir = tempfile.mkdtemp(prefix="nomadpy-capath-")
    shutil.copy(p["ca"], cadir)
    subprocess.run(["c_rehash", cadir], check=True, capture_output=True)
    client = Client(Config(address=address, tls_config=TLSConfig(ca_path=cadir, client_cert=p["cert"], client_key=p["key"])))
    assert client.status.leader() != ""
    shutil.rmtree(cadir)


def test_server_name_override(tls_agent):
    address, p = tls_agent
    good = TLSConfig(ca_cert=p["ca"], client_cert=p["cert"], client_key=p["key"], tls_server_name="server.global.nomad")
    assert Client(Config(address=address, tls_config=good)).status.leader() != ""
    bad = TLSConfig(ca_cert=p["ca"], client_cert=p["cert"], client_key=p["key"], tls_server_name="wrong.example")
    with pytest.raises(urllib.error.URLError):
        Client(Config(address=address, tls_config=bad)).status.leader()


def test_insecure_skips_verification(tls_agent):
    address, p = tls_agent
    client = Client(Config(address=address, tls_config=TLSConfig(client_cert=p["cert"], client_key=p["key"], insecure=True)))
    assert client.status.leader() != ""


def test_unknown_ca_is_rejected(tls_agent):
    address, p = tls_agent
    client = Client(Config(address=address, tls_config=TLSConfig(client_cert=p["cert"], client_key=p["key"])))
    with pytest.raises(urllib.error.URLError):
        client.status.leader()


def test_client_cert_without_key():
    with pytest.raises(ValueError):
        Client(Config(address="https://127.0.0.1:1", tls_config=TLSConfig(client_cert="/c.pem")))
