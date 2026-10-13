# nomadpy

Python client for the HashiCorp Nomad HTTP API, Community and Enterprise.
A port of the Go `api` package from `github.com/hashicorp/nomad`.

```python
from nomadpy import Client

client = Client()  # reads NOMAD_ADDR, NOMAD_TOKEN, NOMAD_NAMESPACE, NOMAD_REGION
print(client.status.leader())
```

## Tests

Integration tests start dev agents from binaries named explicitly; there
are no defaults, and a lane whose variables are unset is skipped.

| Variable | Lane |
|---|---|
| `NOMADPY_TEST_CE_BIN` | Community binary |
| `NOMADPY_TEST_ENT_BIN` and `NOMAD_LICENSE_PATH` | Enterprise binary and its licence |

```
pip install -e .[dev]
NOMADPY_TEST_CE_BIN=$(which nomad) pytest
```

The Enterprise lane needs an Enterprise build (`nomad_<version>+ent` from
releases.hashicorp.com) and a licence file. The Governance & Policy tests
(quotas, Sentinel) skip themselves when the licence lacks that module. CI
runs both lanes from the `NOMAD_LICENSE` repository secret.

## Drift guard

`oracle/` is a Go program that reads the pinned `github.com/hashicorp/nomad/api`
module and writes two fixtures: `surface.json`, the exported methods, struct
fields and constants of every Go file, and `wire.json`, the HTTP requests the
real Go client sends for a fixed table of calls. `tests/test_drift.py` holds
the Python package to the surface and `tests/test_wire.py` replays the calls
and compares the requests. Every deliberate gap is listed with its reason in
`oracle/ledger.json`; anything else is drift and fails.

The fixtures are committed, so the tests need only Python. Go is needed to
regenerate them:

```
make oracle   # regenerate from the pinned version
make bump     # move the pin to upstream main, then regenerate
```

After a bump, the failing drift tests are the list of what the port must
catch up on.
