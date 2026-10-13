package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"sort"
	"strings"
	"time"

	"github.com/hashicorp/nomad/api"
)

// Request is one HTTP request as the Go client sent it. Only headers the
// client sets deliberately are kept; transport headers differ by language.
type Request struct {
	Op      string              `json:"op"`
	Method  string              `json:"method"`
	Path    string              `json:"path"`
	Query   map[string][]string `json:"query"`
	Headers map[string]string   `json:"headers"`
	Body    any                 `json:"body"`
	// Response is what the recorder answered; the Python replay returns the same so results decode.
	Response string `json:"response"`
}

type Wire struct {
	Module   string    `json:"module"`
	Version  string    `json:"version"`
	Requests []Request `json:"requests"`
}

// op is one Go client call. response is the body the recorder answers with,
// which only has to decode into the method's result type.
type op struct {
	name     string
	response string
	call     func(*api.Client) error
}

func wire() (any, error) {
	m, err := pinnedModule()
	if err != nil {
		return nil, err
	}
	var current *op
	var captured []Request
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, _ := io.ReadAll(r.Body)
		req := capture(current.name, r, body)
		req.Response = current.response
		captured = append(captured, req)
		w.Header().Set("X-Nomad-Index", "42")
		w.Header().Set("X-Nomad-LastContact", "7")
		w.Header().Set("X-Nomad-KnownLeader", "true")
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		io.WriteString(w, current.response)
	}))
	defer server.Close()

	config := api.DefaultConfig()
	config.Address = server.URL
	config.Region = "r0"
	config.Namespace = "ns0"
	config.SecretID = "tok0"
	config.Headers = http.Header{"X-Custom": []string{"1"}}
	client, err := api.NewClient(config)
	if err != nil {
		return nil, err
	}
	for i := range ops {
		current = &ops[i]
		if err := current.call(client); err != nil {
			return nil, fmt.Errorf("%s: %w", current.name, err)
		}
	}
	return Wire{Module: module, Version: m.Version, Requests: captured}, nil
}

func capture(name string, r *http.Request, body []byte) Request {
	query := map[string][]string{}
	for k, v := range r.URL.Query() {
		sort.Strings(v)
		query[k] = v
	}
	headers := map[string]string{}
	for k, v := range r.Header {
		if strings.HasPrefix(k, "X-") || k == "Authorization" {
			headers[k] = v[0]
		}
	}
	var decoded any
	if len(body) > 0 {
		if err := json.Unmarshal(body, &decoded); err != nil {
			decoded = string(body)
		}
	}
	return Request{Op: name, Method: r.Method, Path: r.URL.Path, Query: query, Headers: headers, Body: decoded}
}

func ptr[T any](v T) *T { return &v }

var queryOpts = &api.QueryOptions{
	Region: "r1", Namespace: "ns1", AllowStale: true, WaitIndex: 12, WaitTime: 1500 * time.Millisecond,
	Prefix: "p", Filter: "f == 1", PerPage: 5, NextToken: "nt", Reverse: true,
	Params: map[string]string{"x": "y"}, Headers: map[string]string{"H": "v"}, AuthToken: "tok1",
}

var writeOpts = &api.WriteOptions{
	Region: "r1", Namespace: "ns1", AuthToken: "tok1", IdempotencyToken: "idem", Headers: map[string]string{"H": "v"},
}

var job = &api.Job{ID: ptr("j1"), Name: ptr("j1")}

var ops = []op{
	{"status.leader", `""`, func(c *api.Client) error { _, err := c.Status().Leader(); return err }},
	{"status.region_leader", `""`, func(c *api.Client) error { _, err := c.Status().RegionLeader("eu"); return err }},
	{"status.peers", `[]`, func(c *api.Client) error { _, err := c.Status().Peers(); return err }},
	{"regions.list", `[]`, func(c *api.Client) error { _, err := c.Regions().List(); return err }},

	{"jobs.parse_hcl", `{}`, func(c *api.Client) error {
		_, err := c.Jobs().ParseHCLOpts(&api.JobsParseRequest{JobHCL: "job {}", Canonicalize: true, Variables: "n = 3"})
		return err
	}},
	{"jobs.validate", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().Validate(job, writeOpts); return err }},
	{"jobs.register", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().Register(job, nil); return err }},
	{"jobs.register_opts", `{}`, func(c *api.Client) error {
		_, _, err := c.Jobs().RegisterOpts(job, &api.RegisterOptions{
			EnforceIndex: true, ModifyIndex: 7, PolicyOverride: true, PreserveCounts: true, PreserveResources: true,
			EvalPriority: 50, Submission: &api.JobSubmission{Source: "job {}", Format: "hcl2"},
		}, writeOpts)
		return err
	}},
	{"jobs.list", `[]`, func(c *api.Client) error { _, _, err := c.Jobs().List(nil); return err }},
	{"jobs.list_query_opts", `[]`, func(c *api.Client) error { _, _, err := c.Jobs().List(queryOpts); return err }},
	{"jobs.list_meta", `[]`, func(c *api.Client) error {
		_, _, err := c.Jobs().ListOptions(&api.JobListOptions{Fields: &api.JobListFields{Meta: true}}, nil)
		return err
	}},
	{"jobs.prefix_list", `[]`, func(c *api.Client) error { _, _, err := c.Jobs().PrefixList("pre"); return err }},
	{"jobs.info", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().Info("j 1/x", nil); return err }},
	{"jobs.scale", `{}`, func(c *api.Client) error {
		_, _, err := c.Jobs().Scale("j1", "g", ptr(2), "msg", true, map[string]any{"k": "v"}, writeOpts)
		return err
	}},
	{"jobs.scale_status", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().ScaleStatus("j1", nil); return err }},
	{"jobs.versions", `{}`, func(c *api.Client) error { _, _, _, err := c.Jobs().Versions("j1", true, nil); return err }},
	{"jobs.versions_opts", `{}`, func(c *api.Client) error {
		_, _, _, err := c.Jobs().VersionsOpts("j1", &api.VersionsOptions{Diffs: false, DiffTag: "t", DiffVersion: ptr(uint64(3))}, nil)
		return err
	}},
	{"jobs.submission", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().Submission("j1", 2, nil); return err }},
	{"jobs.allocations", `[]`, func(c *api.Client) error { _, _, err := c.Jobs().Allocations("j1", true, nil); return err }},
	{"jobs.deployments", `[]`, func(c *api.Client) error { _, _, err := c.Jobs().Deployments("j1", true, nil); return err }},
	{"jobs.latest_deployment", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().LatestDeployment("j1", nil); return err }},
	{"jobs.evaluations", `[]`, func(c *api.Client) error { _, _, err := c.Jobs().Evaluations("j1", nil); return err }},
	{"jobs.deregister", `{}`, func(c *api.Client) error {
		_, _, err := c.Jobs().DeregisterOpts("j1", &api.DeregisterOptions{Purge: true, Global: true, EvalPriority: 9, NoShutdownDelay: true}, writeOpts)
		return err
	}},
	{"jobs.force_evaluate", `{}`, func(c *api.Client) error {
		_, _, err := c.Jobs().EvaluateWithOpts("j1", api.EvalOptions{ForceReschedule: true}, nil)
		return err
	}},
	{"jobs.periodic_force", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().PeriodicForce("j1", nil); return err }},
	{"jobs.plan", `{}`, func(c *api.Client) error {
		_, _, err := c.Jobs().PlanOpts(job, &api.PlanOptions{Diff: true, PolicyOverride: true}, nil)
		return err
	}},
	{"jobs.summary", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().Summary("j1", nil); return err }},
	{"jobs.dispatch", `{}`, func(c *api.Client) error {
		_, _, err := c.Jobs().DispatchOpts(&api.DispatchOptions{JobID: "j1", Meta: map[string]string{"k": "v"}, Payload: []byte("\x00hello"), IdPrefixTemplate: "pfx", Priority: 3}, nil)
		return err
	}},
	{"jobs.revert", `{}`, func(c *api.Client) error {
		_, _, err := c.Jobs().Revert("j1", 4, ptr(uint64(5)), nil, "", "")
		return err
	}},
	{"jobs.stable", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().Stable("j1", 4, true, nil); return err }},
	{"jobs.services", `[]`, func(c *api.Client) error { _, _, err := c.Jobs().Services("j1", nil); return err }},
	{"jobs.tag_version", `{}`, func(c *api.Client) error {
		_, err := c.Jobs().TagVersionOpts("j1", "golden", &api.TagVersionRequest{Version: 4, Latest: true, Description: "d"}, nil)
		return err
	}},
	{"jobs.untag_version", `{}`, func(c *api.Client) error { _, err := c.Jobs().UntagVersion("j1", "golden", nil); return err }},

	{"namespaces.list", `[]`, func(c *api.Client) error { _, _, err := c.Namespaces().List(nil); return err }},
	{"namespaces.prefix_list", `[]`, func(c *api.Client) error { _, _, err := c.Namespaces().PrefixList("pre", queryOpts); return err }},
	{"namespaces.info", `{}`, func(c *api.Client) error { _, _, err := c.Namespaces().Info("n1", nil); return err }},
	{"namespaces.register", `{}`, func(c *api.Client) error {
		_, err := c.Namespaces().Register(&api.Namespace{
			Name: "n1", Description: "d", Quota: "q", Meta: map[string]string{"k": "v"},
			Capabilities:          &api.NamespaceCapabilities{EnabledTaskDrivers: []string{"raw_exec"}, DisabledNetworkModes: []string{"host"}},
			NodePoolConfiguration: &api.NamespaceNodePoolConfiguration{Default: "p", Allowed: []string{"a"}, Denied: []string{"b"}},
			VaultConfiguration:    &api.NamespaceVaultConfiguration{Default: "v"},
			ConsulConfiguration:   &api.NamespaceConsulConfiguration{Default: "c"},
			RequiredExtraClaims:   map[string]string{"r": "1"}, OptionalExtraClaims: map[string]string{"o": "2"},
		}, writeOpts)
		return err
	}},
	{"namespaces.delete", `{}`, func(c *api.Client) error { _, err := c.Namespaces().Delete("n1", writeOpts); return err }},

	{"evaluations.list", `[]`, func(c *api.Client) error { _, _, err := c.Evaluations().List(nil); return err }},
	{"evaluations.prefix_list", `[]`, func(c *api.Client) error { _, _, err := c.Evaluations().PrefixList("pre"); return err }},
	{"evaluations.count", `{}`, func(c *api.Client) error { _, _, err := c.Evaluations().Count(nil); return err }},
	{"evaluations.info", `{}`, func(c *api.Client) error { _, _, err := c.Evaluations().Info("e1", nil); return err }},
	{"evaluations.delete", `{}`, func(c *api.Client) error {
		_, _, err := c.Evaluations().DeleteOpts(&api.EvalDeleteRequest{EvalIDs: []string{"e1", "e2"}, Filter: "f"}, writeOpts)
		return err
	}},
	{"evaluations.allocations", `[]`, func(c *api.Client) error { _, _, err := c.Evaluations().Allocations("e1", nil); return err }},

	{"deployments.list", `[]`, func(c *api.Client) error { _, _, err := c.Deployments().List(nil); return err }},
	{"deployments.prefix_list", `[]`, func(c *api.Client) error { _, _, err := c.Deployments().PrefixList("pre"); return err }},
	{"deployments.info", `{}`, func(c *api.Client) error { _, _, err := c.Deployments().Info("d1", nil); return err }},
	{"deployments.allocations", `[]`, func(c *api.Client) error { _, _, err := c.Deployments().Allocations("d1", nil); return err }},
	{"deployments.fail", `{}`, func(c *api.Client) error { _, _, err := c.Deployments().Fail("d1", nil); return err }},
	{"deployments.pause", `{}`, func(c *api.Client) error { _, _, err := c.Deployments().Pause("d1", true, nil); return err }},
	{"deployments.promote_all", `{}`, func(c *api.Client) error { _, _, err := c.Deployments().PromoteAll("d1", nil); return err }},
	{"deployments.promote_groups", `{}`, func(c *api.Client) error {
		_, _, err := c.Deployments().PromoteGroups("d1", []string{"g1", "g2"}, nil)
		return err
	}},
	{"deployments.unblock", `{}`, func(c *api.Client) error { _, _, err := c.Deployments().Unblock("d1", nil); return err }},
	{"deployments.set_alloc_health", `{}`, func(c *api.Client) error {
		_, _, err := c.Deployments().SetAllocHealth("d1", []string{"a1"}, []string{"a2"}, writeOpts)
		return err
	}},
}
