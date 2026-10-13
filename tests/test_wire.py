"""Replays the Go client's recorded requests through nomadpy and asserts the wire form matches.

oracle/fixtures/wire.json holds one request per op, as the Go client sent it
against a recorder with the same config this test uses. Each op here makes
the same call with the same arguments. Query strings, paths and headers must
match exactly. Bodies match after the zero-value rule: Go serialises every
struct field, so a key Go sent with a zero value (null, "", 0, false, empty
list or object) may be absent from the Python body, but anything Python
sends must exist in the Go body with the same value.
"""

import json
from datetime import timedelta
from pathlib import Path

import pytest

from nomadpy import Client, Config, QueryOptions, WriteOptions

WIRE = json.loads((Path(__file__).resolve().parent.parent / "oracle/fixtures/wire.json").read_text())

QUERY_OPTS = QueryOptions(region="r1", namespace="ns1", allow_stale=True, wait_index=12, wait_time=timedelta(milliseconds=1500),
                          prefix="p", filter="f == 1", per_page=5, next_token="nt", reverse=True,
                          params={"x": "y"}, headers={"H": "v"}, auth_token="tok1")
WRITE_OPTS = WriteOptions(region="r1", namespace="ns1", auth_token="tok1", idempotency_token="idem", headers={"H": "v"})
JOB = {"ID": "j1", "Name": "j1"}

OPS = {
    "status.leader": lambda c: c.status.leader(),
    "status.region_leader": lambda c: c.status.region_leader("eu"),
    "status.peers": lambda c: c.status.peers(),
    "regions.list": lambda c: c.regions.list(),

    "jobs.parse_hcl": lambda c: c.jobs.parse_hcl("job {}", canonicalize=True, variables="n = 3"),
    "jobs.validate": lambda c: c.jobs.validate(JOB, WRITE_OPTS),
    "jobs.register": lambda c: c.jobs.register(JOB),
    "jobs.register_opts": lambda c: c.jobs.register(
        JOB, WRITE_OPTS, enforce_index=True, modify_index=7, policy_override=True, preserve_counts=True,
        preserve_resources=True, eval_priority=50, submission={"Source": "job {}", "Format": "hcl2"}),
    "jobs.list": lambda c: c.jobs.list(),
    "jobs.list_query_opts": lambda c: c.jobs.list(QUERY_OPTS),
    "jobs.list_meta": lambda c: c.jobs.list(meta=True),
    "jobs.prefix_list": lambda c: c.jobs.prefix_list("pre"),
    "jobs.info": lambda c: c.jobs.info("j 1/x"),
    "jobs.scale": lambda c: c.jobs.scale("j1", "g", 2, "msg", True, {"k": "v"}, WRITE_OPTS),
    "jobs.scale_status": lambda c: c.jobs.scale_status("j1"),
    "jobs.versions": lambda c: c.jobs.versions("j1", diffs=True),
    "jobs.versions_opts": lambda c: c.jobs.versions("j1", diffs=False, diff_tag="t", diff_version=3),
    "jobs.submission": lambda c: c.jobs.submission("j1", 2),
    "jobs.allocations": lambda c: c.jobs.allocations("j1", all_allocs=True),
    "jobs.deployments": lambda c: c.jobs.deployments("j1", all=True),
    "jobs.latest_deployment": lambda c: c.jobs.latest_deployment("j1"),
    "jobs.evaluations": lambda c: c.jobs.evaluations("j1"),
    "jobs.deregister": lambda c: c.jobs.deregister("j1", purge=True, w=WRITE_OPTS, global_=True, eval_priority=9, no_shutdown_delay=True),
    "jobs.force_evaluate": lambda c: c.jobs.force_evaluate("j1", force_reschedule=True),
    "jobs.periodic_force": lambda c: c.jobs.periodic_force("j1"),
    "jobs.plan": lambda c: c.jobs.plan(JOB, diff=True, policy_override=True),
    "jobs.summary": lambda c: c.jobs.summary("j1"),
    "jobs.dispatch": lambda c: c.jobs.dispatch("j1", {"k": "v"}, b"\x00hello", "pfx", priority=3),
    "jobs.revert": lambda c: c.jobs.revert("j1", 4, 5),
    "jobs.stable": lambda c: c.jobs.stable("j1", 4, True),
    "jobs.services": lambda c: c.jobs.services("j1"),
    "jobs.tag_version": lambda c: c.jobs.tag_version("j1", "golden", 4, "d", latest=True),
    "jobs.untag_version": lambda c: c.jobs.untag_version("j1", "golden"),

    "evaluations.list": lambda c: c.evaluations.list(),
    "evaluations.prefix_list": lambda c: c.evaluations.prefix_list("pre"),
    "evaluations.count": lambda c: c.evaluations.count(),
    "evaluations.info": lambda c: c.evaluations.info("e1"),
    "evaluations.delete": lambda c: c.evaluations.delete(["e1", "e2"], WRITE_OPTS, filter="f"),
    "evaluations.allocations": lambda c: c.evaluations.allocations("e1"),

    "deployments.list": lambda c: c.deployments.list(),
    "deployments.prefix_list": lambda c: c.deployments.prefix_list("pre"),
    "deployments.info": lambda c: c.deployments.info("d1"),
    "deployments.allocations": lambda c: c.deployments.allocations("d1"),
    "deployments.fail": lambda c: c.deployments.fail("d1"),
    "deployments.pause": lambda c: c.deployments.pause("d1", True),
    "deployments.promote_all": lambda c: c.deployments.promote_all("d1"),
    "deployments.promote_groups": lambda c: c.deployments.promote_groups("d1", ["g1", "g2"]),
    "deployments.unblock": lambda c: c.deployments.unblock("d1"),
    "deployments.set_alloc_health": lambda c: c.deployments.set_alloc_health("d1", ["a1"], ["a2"], WRITE_OPTS),
}

# The recorder answers what Go's did, except where the Python method flattens a response field.
RESPONSES = {
    "evaluations.count": {"Count": 0},
    "evaluations.delete": {"Count": 0},
    "jobs.deregister": {"EvalID": ""},
    "jobs.force_evaluate": {"EvalID": ""},
    "jobs.periodic_force": {"EvalID": ""},
    "jobs.versions": {"Versions": []},
    "jobs.versions_opts": {"Versions": []},
}


def is_zero(value) -> bool:
    return value is None or value == "" or value == 0 or value is False or value == [] or value == {}


def body_problems(go, py, path="body"):
    if isinstance(go, dict) and isinstance(py, dict):
        problems = []
        for key, value in go.items():
            if key in py:
                problems += body_problems(value, py[key], f"{path}.{key}")
            elif not is_zero(value):
                problems.append(f"{path}.{key}: Go sent {value!r}, Python omitted it")
        for key in py.keys() - go.keys():
            problems.append(f"{path}.{key}: Python sent {py[key]!r}, Go has no such key")
        return problems
    if go != py:
        return [f"{path}: Go sent {go!r}, Python sent {py!r}"]
    return []


def test_every_recorded_op_is_replayed():
    assert {r["op"] for r in WIRE["requests"]} == set(OPS)


@pytest.mark.parametrize("expected", WIRE["requests"], ids=lambda r: r["op"])
def test_wire(recorder, expected):
    recorder.response = RESPONSES.get(expected["op"], json.loads(expected["response"]))
    client = Client(Config(address=recorder.address, region="r0", namespace="ns0", secret_id="tok0", headers={"X-Custom": "1"}))
    OPS[expected["op"]](client)
    got = recorder.last
    assert got["method"] == expected["method"]
    assert got["path"] == expected["path"]
    assert got["query"] == expected["query"]
    headers = {k: v for k, v in got["headers"].items() if k.startswith("X-") or k == "Authorization"}
    assert headers == expected["headers"]
    if expected["body"] is None:
        assert got["body"] is None
    else:
        problems = body_problems(expected["body"], got["body"])
        assert not problems, "\n".join(problems)
