# nomadpy

Python client for the HashiCorp Nomad HTTP API, Community and Enterprise.
It is a port of the Go `api` package from `github.com/hashicorp/nomad`:
one Python module per Go file, the same resource names, the same method
set, with method and argument names in snake_case. It targets Nomad 2.0.x,
needs Python 3.11 or later and uses only the standard library, except for
allocation exec, which runs over a WebSocket and needs the `exec` extra.

```
pip install nomadpy
pip install 'nomadpy[exec]'   # with allocation exec
```

```python
from nomadpy import Client

client = Client()  # reads the NOMAD_* variables the Nomad CLI reads
print(client.status.leader())

jobs, meta = client.jobs.list()
for job in jobs:
    print(job.id, job.status)
```

Services hang off the client (`client.jobs`, `client.namespaces`) and
return the Go package's `QueryMeta` or `WriteMeta` alongside the result
wherever the Go method does. Response types are dataclasses whose JSON keys
are the Go field names.

This site documents what nomadpy owns: its configuration, its request
options, its error and edition behaviour, and its API. The endpoints
themselves, their parameters and their responses are documented in the
[Nomad API docs](https://developer.hashicorp.com/nomad/api-docs); the
[Go and HTTP mapping](reference/mapping/index.md) links each method to its
page there.

- [Configuration](configuration.md): `Config`, `default_config` and the `NOMAD_*` variables.
- [Queries and writes](queries.md): `QueryOptions`, `WriteOptions`, blocking queries and the returned metadata.
- [Errors and editions](errors.md): `UnexpectedResponseError`, `ErrCASConflict` and what a Community server answers to Enterprise calls.
- [API reference](reference/api/acl.md): every module, rendered from the source.
- [Contributing](contributing.md): test lanes, the drift guard and the generators.
