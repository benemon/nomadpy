# nomadpy

[![ci](https://github.com/benemon/nomadpy/actions/workflows/ci.yml/badge.svg)](https://github.com/benemon/nomadpy/actions/workflows/ci.yml) [![codeql](https://github.com/benemon/nomadpy/actions/workflows/codeql.yml/badge.svg)](https://github.com/benemon/nomadpy/actions/workflows/codeql.yml) [![release](https://github.com/benemon/nomadpy/actions/workflows/release.yml/badge.svg)](https://github.com/benemon/nomadpy/actions/workflows/release.yml) [![Dependabot Updates](https://github.com/benemon/nomadpy/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/benemon/nomadpy/actions/workflows/dependabot/dependabot-updates) [![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/benemon/nomadpy/badge)](https://scorecard.dev/viewer/?uri=github.com/benemon/nomadpy) [![PyPI](https://img.shields.io/pypi/v/nomadpy)](https://pypi.org/project/nomadpy/)

Python client for the HashiCorp Nomad HTTP API, Community and Enterprise.
A port of the Go `api` package from `github.com/hashicorp/nomad`.
Documentation: https://benemon.github.io/nomadpy/

```python
from nomadpy import Client

client = Client()  # reads the NOMAD_* variables the Nomad CLI reads
print(client.status.leader())
```

The variables and their meaning are documented with the Nomad CLI:
https://developer.hashicorp.com/nomad/commands#environment-variables

## Tests

Integration tests start dev agents from binaries named explicitly. There
are no defaults: a lane whose variables are unset is skipped.

| Variable | Lane |
|---|---|
| `NOMADPY_TEST_CE_BIN` | Community binary |
| `NOMADPY_TEST_ENT_BIN` and `NOMAD_LICENSE_PATH` | Enterprise binary and its licence |

```
pip install -e '.[dev]'
NOMADPY_TEST_CE_BIN=$(which nomad) pytest
```

### Enterprise lane

Prerequisites: an Enterprise licence file, and `openssl` on the path for the
TLS tests.

1. Download `nomad_<version>+ent_<os>_<arch>.zip` and `nomad_<version>+ent_SHA256SUMS`
   from https://releases.hashicorp.com/nomad/ and verify the zip against the
   checksum file before unpacking it.
2. Export `NOMADPY_TEST_ENT_BIN` as the path of the unpacked binary and
   `NOMAD_LICENSE_PATH` as the path of the licence file.
3. Run `pytest`. The quota and Sentinel tests skip themselves when the
   licence lacks the Governance & Policy module.

CI runs both lanes when the `NOMAD_LICENSE` repository secret is set.
Without it, for example on a fork, the Enterprise tests skip and the run is
still green, so a green run alone does not prove the Enterprise lane ran.

## Drift guard

`oracle/` holds a Go program that reads the pinned
`github.com/hashicorp/nomad/api` module and writes two fixtures:
`surface.json`, the exported methods, struct fields, named types and
constants of every Go file, and `wire.json`, the HTTP requests the real Go
client sends for a fixed table of calls. `tests/test_drift.py` holds the
Python package to the surface, and `tests/test_wire.py` replays the calls
and compares the requests. Every declared gap is listed in
`oracle/ledger.json` with a reason or a bead id. A few shapes are exempt by
rule rather than by ledger; the docstring of `tests/test_drift.py` lists
them. Anything else that differs is drift and fails.

The model dataclasses are generated from `surface.json` by
`oracle/gen_models.py` into the regions each module marks. Fixtures and
models are committed, so the tests need only Python. Go is needed to
regenerate:

```
make oracle   # regenerate the fixtures from the pinned version
make models   # regenerate the model dataclasses from the surface
make bump     # move the pin to upstream main, then regenerate the fixtures
```

After a bump, the failing drift tests are the list of what the port must
catch up on.

## Releases

A release is a tag `v<version>` matching `project.version` in
`pyproject.toml`. The release workflow refuses a tag that does not match,
requires a green test run for the tagged commit, builds the sdist and wheel,
publishes them to PyPI through trusted publishing from the `pypi`
environment, and creates the GitHub release with generated notes.

Prerequisites, once: a PyPI project `nomadpy` with this repository's
`release.yml` registered as a trusted publisher for the `pypi` environment,
and that environment created in the repository settings.
