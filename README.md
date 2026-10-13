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
