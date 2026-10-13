// Command oracle extracts two fixtures from the pinned github.com/hashicorp/nomad/api module:
//
//	surface.json  the exported methods, struct fields and constants of every Go file
//	wire.json     the HTTP requests the Go client sends for a fixed table of calls
//
// The Python drift and wire tests hold the port to these fixtures.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
)

const module = "github.com/hashicorp/nomad/api"

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: oracle (surface|wire) <output.json>")
		os.Exit(2)
	}
	var out any
	var err error
	switch os.Args[1] {
	case "surface":
		out, err = surface()
	case "wire":
		out, err = wire()
	default:
		fmt.Fprintln(os.Stderr, "unknown command", os.Args[1])
		os.Exit(2)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	data, err := json.MarshalIndent(out, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := os.WriteFile(os.Args[2], append(data, '\n'), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

type moduleInfo struct {
	Version string
	Dir     string
}

func pinnedModule() (moduleInfo, error) {
	var m moduleInfo
	out, err := exec.Command("go", "list", "-m", "-json", module).Output()
	if err != nil {
		return m, fmt.Errorf("go list: %w", err)
	}
	if err := json.Unmarshal(out, &m); err != nil {
		return m, err
	}
	if m.Dir == "" {
		return m, fmt.Errorf("%s is not downloaded; run go mod download", module)
	}
	return m, nil
}
