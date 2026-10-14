.PHONY: test oracle bump models docs

test:
	.venv/bin/pytest

oracle:
	cd oracle && go mod download && go run . surface fixtures/surface.json && go run . wire fixtures/wire.json

# Move the pin to the current upstream main, then regenerate. The drift tests
# then show what the port must catch up on.
bump:
	cd oracle && go get github.com/hashicorp/nomad/api@main && go mod tidy
	$(MAKE) oracle

# Regenerate the model dataclasses from the surface fixture in every module that carries a generation marker.
models:
	python3 oracle/gen_models.py oracle/fixtures/surface.json $$(grep -l '^# generated from surface.json' src/nomadpy/*.py)

# Regenerate the reference pages from the fixtures, then build the site; --strict fails on a broken docstring or dead link.
docs:
	python3 oracle/gen_docs.py
	.venv/bin/mkdocs build --strict
