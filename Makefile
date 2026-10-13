.PHONY: test oracle bump

test:
	.venv/bin/pytest

# Regenerate the Go oracle fixtures from the pinned github.com/hashicorp/nomad/api.
oracle:
	cd oracle && go mod download && go run . surface fixtures/surface.json && go run . wire fixtures/wire.json

# Move the pin to the current upstream main, then regenerate. The drift tests
# then show what the port must catch up on.
bump:
	cd oracle && go get github.com/hashicorp/nomad/api@main && go mod tidy
	$(MAKE) oracle
