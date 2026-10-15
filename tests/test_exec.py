import io
import os

import pytest
from jobspecs import register_and_wait

from nomadpy import QueryOptions, TerminalSize, UnexpectedResponseError


def running_alloc(client, job_id):
    (alloc,), _ = client.allocations.list(QueryOptions(filter=f'JobID == "{job_id}"'))
    return alloc


def test_exec(client):
    register_and_wait(client, "nomadpy-exec")
    try:
        alloc = running_alloc(client, "nomadpy-exec")
        out, err = io.BytesIO(), io.BytesIO()
        assert client.allocations.exec(alloc.id, "t", ["sh", "-c", "echo hello; echo oops >&2; exit 3"], stdout=out, stderr=err, timeout=30) == 3
        assert out.getvalue() == b"hello\n" and err.getvalue() == b"oops\n"

        out = io.BytesIO()
        assert client.allocations.exec(alloc.id, "t", ["cat"], stdin=io.BytesIO(b"round trip"), stdout=out, timeout=30) == 0
        assert out.getvalue() == b"round trip"

        # A pseudo-terminal hangs up on EOF, so stdin is a pipe nobody writes to until the command has exited.
        read_end, write_end = os.pipe()
        held_open = os.fdopen(read_end, "rb", buffering=0)
        out = io.BytesIO()
        code = client.allocations.exec(alloc.id, "t", ["sh", "-c", "sleep 1; stty size"], tty=True, stdin=held_open,
                                       resize=[TerminalSize(height=24, width=80)], stdout=out, timeout=30)
        os.close(write_end)
        held_open.close()
        assert code == 0 and b"24 80" in out.getvalue()

        with pytest.raises(TimeoutError):
            client.allocations.exec(alloc.id, "t", ["sleep", "60"], timeout=2)

        with pytest.raises((UnexpectedResponseError, ConnectionError)):
            client.allocations.exec(alloc.id, "no-such-task", ["true"], timeout=30)
    finally:
        client.jobs.deregister("nomadpy-exec", purge=True)


def test_action_exec(client):
    register_and_wait(client, "nomadpy-action", actions=True)
    try:
        alloc = running_alloc(client, "nomadpy-action")
        out = io.BytesIO()
        code = client.jobs.action_exec(alloc.id, alloc.task_group, "nomadpy-action", "t", ["sh", "-c", "echo acted"], "say", stdout=out, timeout=30)
        assert code == 0 and out.getvalue() == b"acted\n"
    finally:
        client.jobs.deregister("nomadpy-action", purge=True)
