# Queries and writes

Every service method takes the Go package's per-request options as its
last positional argument: [QueryOptions][nomadpy.api.QueryOptions] (`q`)
on reads and [WriteOptions][nomadpy.api.WriteOptions] (`w`) on writes.
Methods that return metadata return a tuple of the result and a
[QueryMeta][nomadpy.api.QueryMeta] or [WriteMeta][nomadpy.api.WriteMeta].
A Go `Foo` / `FooOpts` pair is one Python method whose extra options are
keyword-only arguments.

```python
from datetime import timedelta
from nomadpy import Client, QueryOptions

client = Client()
jobs, meta = client.jobs.list(QueryOptions(namespace="*", prefix="web", per_page=20))
while meta.next_token:
    more, meta = client.jobs.list(QueryOptions(namespace="*", prefix="web", per_page=20, next_token=meta.next_token))
    jobs += more
```

## QueryOptions

| Field | On the wire |
|---|---|
| `region` | `region` query parameter |
| `namespace` | `namespace` query parameter |
| `allow_stale` | `stale` query parameter |
| `wait_index` | `index` query parameter |
| `wait_time` | `wait` query parameter, as milliseconds |
| `prefix` | `prefix` query parameter |
| `filter` | `filter` query parameter |
| `per_page` | `per_page` query parameter |
| `next_token` | `next_token` query parameter |
| `reverse` | `reverse=true` query parameter |
| `params` | Further query parameters, replacing any of the same name |
| `headers` | Further headers |
| `auth_token` | `X-Nomad-Token` header for this request |

A zero value is not sent. The Nomad API docs describe the parameters:
[blocking queries](https://developer.hashicorp.com/nomad/api-docs#blocking-queries),
[consistency modes](https://developer.hashicorp.com/nomad/api-docs#consistency-modes),
[filtering](https://developer.hashicorp.com/nomad/api-docs#filtering) and
[pagination](https://developer.hashicorp.com/nomad/api-docs#pagination).

## WriteOptions

| Field | On the wire |
|---|---|
| `region` | `region` query parameter |
| `namespace` | `namespace` query parameter |
| `auth_token` | `X-Nomad-Token` header for this request |
| `idempotency_token` | `idempotency_token` query parameter |
| `headers` | Further headers |

## Blocking queries

A blocking query is a read with `wait_index` set to the `last_index` of
the previous response. The server holds the request until the index
changes or `wait_time` elapses. nomadpy does no waiting of its own; the
caller loops.

```python
from datetime import timedelta
from nomadpy import Client, QueryOptions

client = Client()
index = 0
while True:
    allocs, meta = client.jobs.allocations("web", q=QueryOptions(wait_index=index, wait_time=timedelta(minutes=5)))
    if meta.last_index != index:
        index = meta.last_index
        print([(a.id, a.client_status) for a in allocs])
```

## Metadata

`QueryMeta` is decoded from the response headers: `last_index` from
`X-Nomad-Index`, `last_contact` from `X-Nomad-LastContact`, `known_leader`
from `X-Nomad-KnownLeader`, `next_token` from `X-Nomad-NextToken`.
`request_time` is the round trip measured by the client. `WriteMeta`
carries `last_index` and `request_time`.

## Streams

The event stream, allocation logs and the filesystem stream are generators
over [Client.stream_json][nomadpy.api.Client.stream_json]. Each yields the
decoded JSON values as they arrive; closing the generator closes the
connection. The `timeout` argument bounds each wait for more bytes.

## Allocation exec

[Allocations.exec][nomadpy.allocations.Allocations.exec] and
[Jobs.action_exec][nomadpy.jobs.Jobs.action_exec] run a command in a task
over the exec WebSocket and return its exit code. They need the `exec`
extra, which installs the `websockets` package; without it the call raises
`ImportError`. The connection goes through the server, with the same
address, token, TLS and query options as every other call.

```python
import io

out = io.BytesIO()
code = client.allocations.exec(alloc_id, "web", ["sh", "-c", "cat /etc/hostname"], stdout=out, timeout=30)
```

`stdin`, `stdout` and `stderr` are binary file objects. The task reads
`stdin` until EOF, and sees EOF at once when none is given. With `tty`,
terminal sizes taken from `resize` are sent to the task, and EOF on `stdin`
hangs the terminal up, so give a `stdin` that stays open until the command
exits. A connection the
server closes before the command exits raises `ConnectionError` with the
server's reason, and a handshake it refuses raises
`UnexpectedResponseError` with the status.
