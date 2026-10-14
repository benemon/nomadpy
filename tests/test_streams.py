import time

import pytest
from jobspecs import DEADLINE, register_and_wait

from nomadpy import QueryOptions, UnexpectedResponseError
from nomadpy.event_stream import TOPIC_ALL, TOPIC_JOB, TOPIC_NODE


def test_event_stream_replays_buffered_events(client):
    register_and_wait(client, "nomadpy-events")
    try:
        # Index 1 is older than anything buffered, so the server replays its buffer and the first batch arrives at once.
        stream = client.event_stream.stream({TOPIC_JOB: ["nomadpy-events"]}, index=1, timeout=30)
        batch = next(stream)
        stream.close()
        assert batch.index > 0 and not batch.is_heartbeat()
        event = batch.events[0]
        assert event.topic == TOPIC_JOB and event.key == "nomadpy-events" and event.type == "JobRegistered"
        job = event.job()
        assert job.id == "nomadpy-events" and job.task_groups[0].tasks[0].driver == "raw_exec"
        _, deleted = event.deregistered_job()
        assert deleted is False

        stream = client.event_stream.stream({TOPIC_NODE: []}, index=1, timeout=30)
        node_batch = next(stream)
        stream.close()
        assert node_batch.events[0].topic == TOPIC_NODE and node_batch.events[0].node().id
    finally:
        client.jobs.deregister("nomadpy-events", purge=True)

    stream = client.event_stream.stream({TOPIC_ALL: []}, index=1, timeout=30)
    seen = set()
    deadline = time.monotonic() + DEADLINE
    for batch in stream:
        seen |= {(e.topic, e.type) for e in batch.events}
        if (TOPIC_JOB, "JobDeregistered") in seen or time.monotonic() > deadline:
            break
    stream.close()
    assert (TOPIC_JOB, "JobDeregistered") in seen


def test_event_stream_timeout(client):
    stream = client.event_stream.stream({TOPIC_JOB: ["no-such-job"]}, index=0, timeout=2)
    with pytest.raises(TimeoutError):
        next(stream)
    stream.close()


def test_alloc_fs(client):
    register_and_wait(client, "nomadpy-fs", command="echo hello; sleep 600")
    try:
        (alloc,), _ = client.allocations.list(QueryOptions(filter='JobID == "nomadpy-fs"'))
        entries, qm = client.alloc_fs.list(alloc.id, "/")
        assert {e.name for e in entries} >= {"alloc", "t"} and all(e.is_dir for e in entries)
        logs, _ = client.alloc_fs.list(alloc.id, "alloc/logs")
        assert "t.stdout.0" in [e.name for e in logs]
        info, _ = client.alloc_fs.stat(alloc.id, "alloc/logs/t.stdout.0")
        assert info.name == "t.stdout.0" and not info.is_dir and info.mod_time

        deadline = time.monotonic() + DEADLINE
        while time.monotonic() < deadline and client.alloc_fs.cat(alloc.id, "alloc/logs/t.stdout.0") != b"hello\n":
            time.sleep(0.5)
        assert client.alloc_fs.cat(alloc.id, "alloc/logs/t.stdout.0") == b"hello\n"
        assert client.alloc_fs.read_at(alloc.id, "alloc/logs/t.stdout.0", 1, 3) == b"ell"

        frames = list(client.alloc_fs.logs(alloc.id, False, "t", "stdout", "start", 0, timeout=30))
        assert b"".join(f.data_bytes for f in frames) == b"hello\n"
        assert frames[0].file.endswith("t.stdout.0")

        stream = client.alloc_fs.stream(alloc.id, "alloc/logs/t.stdout.0", "start", 0, timeout=30)
        first = next(stream)
        stream.close()
        assert first.data_bytes == b"hello\n" and first.offset == 6

        with pytest.raises(UnexpectedResponseError) as e:
            client.alloc_fs.stat(alloc.id, "no/such/file")
        assert e.value.status_code in (404, 500)
    finally:
        client.jobs.deregister("nomadpy-fs", purge=True)
