"""Exec sessions over the allocation exec and job action WebSocket endpoints, the port of allocations_exec.go.

The session needs the websockets package, installed by the `exec` extra. It
is imported when a session starts, so the rest of the package carries no
dependency. The Go session dials the allocation's node first and falls back
to the server; this one always goes through the server, like every other
call in the package.
"""

from __future__ import annotations

import base64
import json
import threading
from collections.abc import Iterable
from typing import TYPE_CHECKING, BinaryIO

from .allocations import ExecStreamingInput, ExecStreamingIOOperation, ExecStreamingOutput, TerminalSize
from .api import QueryOptions, UnexpectedResponseError

if TYPE_CHECKING:
    from .api import Client

HEARTBEAT_INTERVAL = 10.0
STDIN_CHUNK = 2048


def exec_params(task: str, tty: bool, command: list[str]) -> list[tuple[str, str]]:
    # Go marshals the command without spaces; the server decodes either form, the wire fixture holds Go's.
    return [("tty", "true" if tty else "false"), ("task", task), ("command", json.dumps(command, separators=(",", ":")))]


def run(client: Client, endpoint: str, q: QueryOptions | None, stdin: BinaryIO | None, stdout: BinaryIO | None, stderr: BinaryIO | None,
        resize: Iterable[TerminalSize] | None, timeout: float | None) -> int:
    """run drives one session to the command's exit and returns its exit code.

    stdin is pumped to the task in a thread until EOF, then closed; without
    one the task sees EOF at once. Output frames go to stdout and stderr as
    bytes. `timeout` bounds the handshake and each wait for a frame. A
    connection that closes before the exit frame raises ConnectionError with
    the server's close reason; a handshake the server refuses raises
    UnexpectedResponseError with its status.
    """
    try:
        from websockets.exceptions import InvalidStatus
        from websockets.sync.client import connect
    except ImportError:
        raise ImportError("allocation exec needs the websockets package: pip install 'nomadpy[exec]'") from None
    url, headers, ssl_context, server_name = client.websocket_target(endpoint, q)
    try:
        with connect(url, ssl=ssl_context, server_hostname=server_name or None, additional_headers=headers, open_timeout=timeout) as conn:
            return _session(conn, stdin, stdout, stderr, resize, timeout)
    except InvalidStatus as e:
        body = (e.response.body or b"").decode(errors="replace").strip()
        raise UnexpectedResponseError(e.response.status_code, e.response.reason_phrase, body, (101,)) from e


def _session(conn, stdin, stdout, stderr, resize, timeout) -> int:
    from websockets.exceptions import ConnectionClosed

    closed = threading.Event()
    lock = threading.Lock()

    def send(frame: ExecStreamingInput) -> None:
        with lock:
            conn.send(json.dumps(frame.to_json()))

    def pump_stdin() -> None:
        try:
            while not closed.is_set():
                data = stdin.read(STDIN_CHUNK) if stdin is not None else b""
                if not data:
                    send(ExecStreamingInput(stdin=ExecStreamingIOOperation(close=True)))
                    return
                send(ExecStreamingInput(stdin=ExecStreamingIOOperation(data=base64.b64encode(data).decode())))
        except ConnectionClosed:
            return

    def heartbeat() -> None:
        try:
            while not closed.wait(HEARTBEAT_INTERVAL):
                send(ExecStreamingInput())
        except ConnectionClosed:
            return

    def pump_resize() -> None:
        try:
            for size in resize:
                if closed.is_set():
                    return
                send(ExecStreamingInput(tty_size=size))
        except ConnectionClosed:
            return

    # Daemon threads: a stdin read may block past the command's exit and has nothing left to deliver.
    pumps = [pump_stdin, heartbeat] + ([pump_resize] if resize is not None else [])
    for target in pumps:
        threading.Thread(target=target, daemon=True).start()
    try:
        while True:
            try:
                message = conn.recv(timeout=timeout)
            except ConnectionClosed as e:
                reason = e.rcvd.reason if e.rcvd is not None else ""
                raise ConnectionError(reason or "websocket closed before the command exited") from e
            frame = ExecStreamingOutput.from_json(json.loads(message))
            if frame.stdout is not None:
                if frame.stdout.data and stdout is not None:
                    stdout.write(base64.b64decode(frame.stdout.data))
            elif frame.stderr is not None:
                if frame.stderr.data and stderr is not None:
                    stderr.write(base64.b64decode(frame.stderr.data))
            elif frame.exited and frame.result is not None:
                return frame.result.exit_code
    finally:
        closed.set()
