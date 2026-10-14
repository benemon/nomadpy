# Contributing

The Go client package `github.com/hashicorp/nomad/api` is the reference
implementation, ported file by file: one Python module per Go file, the
same resource names, the same method set. When the Go package and the HTTP
docs disagree, the Go package wins. The
[API docs](https://developer.hashicorp.com/nomad/api-docs) decide which
endpoints and fields are Enterprise.

```
git clone https://github.com/benemon/nomadpy
cd nomadpy
python -m venv .venv
.venv/bin/pip install -e '.[dev,docs]'
```

## Test lanes

Integration tests start dev agents from binaries named explicitly; the
HTTP layer is never mocked. There are no defaults: a lane whose variables
are unset is skipped.

| Variable | Lane |
|---|---|
| `NOMADPY_TEST_CE_BIN` | Community binary |
| `NOMADPY_TEST_ENT_BIN` and `NOMAD_LICENSE_PATH` | Enterprise binary and its licence |

```
NOMADPY_TEST_CE_BIN=$(which nomad) make test
```

`NOMAD_LICENSE_PATH` is Nomad's own variable, passed through to the agent.
The `NOMADPY_TEST_*` names belong to this project; no `NOMAD_`-prefixed
variable that Nomad itself does not define is added. The README describes
how to obtain and verify an Enterprise binary. The quota and Sentinel tests
skip themselves when the licence lacks the Governance & Policy module.

Unit tests cover model serialisation and request encoding; encoding is
asserted against a local recording HTTP server.

## Drift guard

`oracle/` holds a Go program that reads the pinned Go module and writes two
fixtures: `fixtures/surface.json`, the exported methods, struct fields,
named types and constants of every Go file, and `fixtures/wire.json`, the
HTTP requests the real Go client sends for a fixed table of calls.
`tests/test_drift.py` holds the Python package to the surface and
`tests/test_wire.py` replays the calls and compares the requests.
`oracle/ledger.json` is the only place a gap may be declared, always with a
reason or a bead id.

Porting a file: remove its ledger entry, add its calls to the op table in
`oracle/wire.go` and `tests/test_wire.py`, regenerate, and make the drift
tests pass without new ledger entries unless the gap is deliberate.

```
make oracle   # regenerate the fixtures from the pinned version
make models   # regenerate the model dataclasses from the surface
make bump     # move the pin to upstream main, then regenerate the fixtures
make docs     # regenerate the reference pages, then build the site with --strict
```

After a bump, the failing drift tests are the list of what the port must
catch up on. Go is needed to regenerate the fixtures; the fixtures, models
and reference pages are committed, so the tests and the docs build need
only Python.

## Generators

`oracle/gen_models.py` writes the region between a
`# generated from surface.json` marker and `# end generated` in each module
that carries one. That region is never hand-edited: change the generator or
the marker's `only` and `mixins` lists and regenerate. Methods on a
generated class live in a mixin class defined above the region.

`oracle/gen_docs.py` writes `docs/reference/api/`, one mkdocstrings page
per module, and `docs/reference/mapping/`, one table per service linking
each Python method to the Go methods it ports, the recorded request and
the Nomad API docs page. A `wire.json` op that matches no Python method
fails the generator; a cross-reference to a method that does not exist
fails the strict build.
