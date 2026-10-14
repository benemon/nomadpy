"""Generates the reference pages under docs/reference from the oracle fixtures.

docs/reference/api/<module>.md holds one mkdocstrings directive per module of
src/nomadpy. docs/reference/mapping/<service>.md holds one table per service
class: each Python method, the Go methods it ports (a Foo/FooOpts pair or a
ledger fold is one row), the requests wire.json recorded for it, and the
page of the Nomad API docs that documents the endpoint. A wire.json op that
matches no Python method is an error. Run `make docs` after `make oracle`.

Usage: gen_docs.py
"""

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src/nomadpy"
DOCS = ROOT / "docs/reference"
API_DOCS = "https://developer.hashicorp.com/nomad/api-docs/"
CLASS = re.compile(r"^class (\w+)", re.M)
SERVICE = re.compile(r"self\.\w+ = (\w+)\((?:self|client)\)")

# The API docs page for the endpoints of each Go file.
FILE_PAGES = {
    "acl.go": "acl",
    "agent.go": "agent",
    "allocations.go": "allocations",
    "csi.go": "volumes",
    "deployments.go": "deployments",
    "evaluations.go": "evaluations",
    "event_stream.go": "events",
    "fs.go": "client",
    "host_volume_claims.go": "volumes",
    "host_volumes.go": "volumes",
    "jobs.go": "jobs",
    "keyring.go": "operator/keyring",
    "namespace.go": "namespaces",
    "node_identity.go": "client",
    "node_meta.go": "client",
    "node_pools.go": "node-pools",
    "nodes.go": "nodes",
    "operator.go": "operator",
    "operator_autopilot.go": "operator/autopilot",
    "operator_metrics.go": "metrics",
    "quota.go": "quotas",
    "recommendations.go": "recommendations",
    "regions.go": "regions",
    "scaling.go": "scaling-policies",
    "search.go": "search",
    "sentinel.go": "sentinel-policies",
    "services.go": "services",
    "status.go": "status",
    "system.go": "system",
    "variables.go": "variables/variables",
}
# Methods whose endpoint is documented on another page than their file's; the longest matching "Receiver.Method" prefix wins.
METHOD_PAGES = {
    "ACLAuth.": "acl/oidc",
    "ACLAuth.Login": "acl/login",
    "ACLAuthMethods.": "acl/auth-methods",
    "ACLBindingRules.": "acl/binding-rules",
    "ACLIdentity.": "acl/identities",
    "ACLPolicies.": "acl/policies",
    "ACLRoles.": "acl/roles",
    "ACLTokens.": "acl/tokens",
    "Allocations.GC": "client",
    "Allocations.Stats": "client",
    "CSIPlugins.": "plugins",
    "Jobs.Validate": "validate",
    "Nodes.GC": "client",
    "Nodes.GcAlloc": "client",
    "Nodes.Stats": "client",
    "Operator.ApplyLicense": "operator/license",
    "Operator.License": "operator/license",
    "Operator.Raft": "operator/raft",
    "Operator.Scheduler": "operator/scheduler",
    "Operator.UpgradeCheck": "operator/upgrade-check",
    "Operator.Utilization": "operator/utilization",
    "Variables.AcquireLock": "variables/locks",
    "Variables.ReleaseLock": "variables/locks",
    "Variables.RenewLock": "variables/locks",
}
# Marked Enterprise as the API docs mark them; the module and method docstrings in src/nomadpy say the same.
ENTERPRISE_FILES = {"quota.go", "recommendations.go", "sentinel.go"}
ENTERPRISE_METHODS = ("Allocations.GetPauseState", "Allocations.SetPauseState", "Operator.ApplyLicense", "Operator.License", "Operator.Utilization")


def snake(name):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


def python_methods(surface, ledger):
    """Go methods of the ported files grouped by the Python method they map to, with the same rules as tests/test_drift.py."""
    out = defaultdict(lambda: defaultdict(list))
    for go_file, file in surface["files"].items():
        if not (SRC / go_file.replace(".go", ".py")).exists():
            continue
        keys = {f'{m["receiver"]}.{m["name"]}' for m in file["methods"]}
        for m in file["methods"]:
            receiver, name = m["receiver"], m["name"]
            entry = ledger["methods"].get(f"{receiver}.{name}")
            if isinstance(entry, str):
                continue
            if isinstance(entry, dict):
                py = entry["folded"]
            elif name.endswith("Opts") and f"{receiver}.{name[:-4]}" in keys:
                py = snake(name[:-4])
            else:
                py = snake(name)
            out[receiver][py].append((go_file, name))
    return out


def requests_by_method(wire, methods):
    """wire.json requests keyed by (receiver, Python method): an op is `<service attribute>.<method>[_<variant>]`."""
    receivers = {snake(r): r for r in methods}
    out = defaultdict(list)
    for req in wire["requests"]:
        attr, rest = req["op"].split(".", 1)
        receiver = receivers.get(attr)
        parts = rest.split("_")
        hits = [p for p in ("_".join(parts[:i]) for i in range(len(parts), 0, -1)) if receiver and p in methods[receiver]]
        if not hits:
            raise SystemExit(f"wire op {req['op']} matches no Python method")
        line = f"`{req['method']} {req['path']}`"
        if line not in out[receiver, hits[0]]:
            out[receiver, hits[0]].append(line)
    return out


def page(go_file, receiver, name):
    key = f"{receiver}.{name}"
    prefixes = [p for p in METHOD_PAGES if key.startswith(p)]
    path = METHOD_PAGES[max(prefixes, key=len)] if prefixes else FILE_PAGES[go_file]
    enterprise = go_file in ENTERPRISE_FILES or key.startswith(ENTERPRISE_METHODS)
    return f"[{path}]({API_DOCS}{path})" + (" Enterprise" if enterprise else "")


def mapping_page(receiver, module, methods, requests):
    lines = [f"# {receiver}", "",
             f"[{receiver}][nomadpy.{module}.{receiver}] in `nomadpy.{module}`.", "",
             "| Python | Go | HTTP | API docs |", "|---|---|---|---|"]
    for py, gos in sorted(methods.items()):
        go_file, name = gos[0]
        lines.append(f"| [{py}][nomadpy.{module}.{receiver}.{py}] | {', '.join(n for _, n in gos)} "
                     f"| {'<br>'.join(requests.get((receiver, py), []))} | {page(go_file, receiver, name)} |")
    return "\n".join(lines) + "\n"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != text:
        path.write_text(text)
        return True
    return False


def main():
    surface = json.load(open(ROOT / "oracle/fixtures/surface.json"))
    wire = json.load(open(ROOT / "oracle/fixtures/wire.json"))
    ledger = json.load(open(ROOT / "oracle/ledger.json"))
    modules = sorted(p.stem for p in SRC.glob("*.py") if p.stem != "__init__")
    module_of = {c: m for m in modules for c in CLASS.findall((SRC / f"{m}.py").read_text())}
    services = sorted({s for m in modules for s in SERVICE.findall((SRC / f"{m}.py").read_text())})
    methods = python_methods(surface, ledger)
    requests = requests_by_method(wire, methods)

    changed = [m for m in modules if write(DOCS / f"api/{m}.md", f"# nomadpy.{m}\n\n::: nomadpy.{m}\n")]
    index = ["# Go and HTTP mapping", "",
             "One table per service class: the Python method, the Go methods of the pinned `api` module it ports, the "
             "requests `oracle/fixtures/wire.json` records for it (path segments such as `j1` are the fixture's "
             "identifiers), and the Nomad API docs page for the endpoint. Enterprise endpoints are marked as the API "
             "docs mark them.", ""]
    for s in services:
        index.append(f"- [{s}]({snake(s)}.md)")
        if write(DOCS / f"mapping/{snake(s)}.md", mapping_page(s, module_of[s], methods[s], requests)):
            changed.append(snake(s))
    if write(DOCS / "mapping/index.md", "\n".join(index) + "\n"):
        changed.append("mapping/index")
    print(f"{len(modules)} api pages, {len(services)} services, {len(wire['requests'])} wire ops; "
          f"{len(changed)} pages changed" + (": " + ", ".join(changed) if changed else ""))


if __name__ == "__main__":
    main()
