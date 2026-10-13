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
// which only has to decode into the method's result type; it is empty for
// calls that decode nothing.
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

// queryOpts returns a fresh value each time: methods such as PrefixList mutate the options they are given.
func queryOpts() *api.QueryOptions {
	return &api.QueryOptions{
		Region: "r1", Namespace: "ns1", AllowStale: true, WaitIndex: 12, WaitTime: 1500 * time.Millisecond,
		Prefix: "p", Filter: "f == 1", PerPage: 5, NextToken: "nt", Reverse: true,
		Params: map[string]string{"x": "y"}, Headers: map[string]string{"H": "v"}, AuthToken: "tok1",
	}
}

var writeOpts = &api.WriteOptions{
	Region: "r1", Namespace: "ns1", AuthToken: "tok1", IdempotencyToken: "idem", Headers: map[string]string{"H": "v"},
}

var job = &api.Job{ID: new("j1"), Name: new("j1")}

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
	{"jobs.list_query_opts", `[]`, func(c *api.Client) error { _, _, err := c.Jobs().List(queryOpts()); return err }},
	{"jobs.list_meta", `[]`, func(c *api.Client) error {
		_, _, err := c.Jobs().ListOptions(&api.JobListOptions{Fields: &api.JobListFields{Meta: true}}, nil)
		return err
	}},
	{"jobs.prefix_list", `[]`, func(c *api.Client) error { _, _, err := c.Jobs().PrefixList("pre"); return err }},
	{"jobs.info", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().Info("j 1/x", nil); return err }},
	{"jobs.scale", `{}`, func(c *api.Client) error {
		_, _, err := c.Jobs().Scale("j1", "g", new(2), "msg", true, map[string]any{"k": "v"}, writeOpts)
		return err
	}},
	{"jobs.scale_status", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().ScaleStatus("j1", nil); return err }},
	{"jobs.versions", `{}`, func(c *api.Client) error { _, _, _, err := c.Jobs().Versions("j1", true, nil); return err }},
	{"jobs.versions_opts", `{}`, func(c *api.Client) error {
		_, _, _, err := c.Jobs().VersionsOpts("j1", &api.VersionsOptions{Diffs: false, DiffTag: "t", DiffVersion: new(uint64(3))}, nil)
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
		_, _, err := c.Jobs().Revert("j1", 4, new(uint64(5)), nil, "", "")
		return err
	}},
	{"jobs.stable", `{}`, func(c *api.Client) error { _, _, err := c.Jobs().Stable("j1", 4, true, nil); return err }},
	{"jobs.services", `[]`, func(c *api.Client) error { _, _, err := c.Jobs().Services("j1", nil); return err }},
	{"jobs.tag_version", `{}`, func(c *api.Client) error {
		_, err := c.Jobs().TagVersionOpts("j1", "golden", &api.TagVersionRequest{Version: 4, Latest: true, Description: "d"}, nil)
		return err
	}},
	{"jobs.untag_version", `{}`, func(c *api.Client) error { _, err := c.Jobs().UntagVersion("j1", "golden", nil); return err }},

	{"acl_policies.list", `[]`, func(c *api.Client) error { _, _, err := c.ACLPolicies().List(nil); return err }},
	{"acl_policies.upsert", `{}`, func(c *api.Client) error {
		_, err := c.ACLPolicies().Upsert(&api.ACLPolicy{Name: "p1", Description: "d", Rules: `namespace "default" { policy = "read" }`, JobACL: &api.JobACL{Namespace: "ns", JobID: "j"}}, writeOpts)
		return err
	}},
	{"acl_policies.delete", `{}`, func(c *api.Client) error { _, err := c.ACLPolicies().Delete("p1", nil); return err }},
	{"acl_policies.info", `{}`, func(c *api.Client) error { _, _, err := c.ACLPolicies().Info("p1", nil); return err }},
	{"acl_policies.self", `[]`, func(c *api.Client) error { _, _, err := c.ACLPolicies().Self(nil); return err }},
	{"acl_tokens.bootstrap", `{}`, func(c *api.Client) error { _, _, err := c.ACLTokens().Bootstrap(nil); return err }},
	{"acl_tokens.bootstrap_opts", `{}`, func(c *api.Client) error { _, _, err := c.ACLTokens().BootstrapOpts("secret", writeOpts); return err }},
	{"acl_tokens.list", `[]`, func(c *api.Client) error { _, _, err := c.ACLTokens().List(nil); return err }},
	{"acl_tokens.create", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLTokens().Create(&api.ACLToken{Name: "t", Type: "client", Policies: []string{"p1"}, Roles: []*api.ACLTokenRoleLink{{ID: "r1"}}, Global: true, ExpirationTTL: 90 * time.Minute}, nil)
		return err
	}},
	{"acl_tokens.upload", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLTokens().Upload(&api.ACLToken{AccessorID: "acc", SecretID: "sec", Name: "t", Type: "client", Policies: []string{"p1"}}, nil)
		return err
	}},
	{"acl_tokens.update", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLTokens().Update(&api.ACLToken{AccessorID: "acc", Name: "t2"}, nil)
		return err
	}},
	{"acl_tokens.delete", `{}`, func(c *api.Client) error { _, err := c.ACLTokens().Delete("acc", nil); return err }},
	{"acl_tokens.info", `{}`, func(c *api.Client) error { _, _, err := c.ACLTokens().Info("acc", nil); return err }},
	{"acl_tokens.self", `{}`, func(c *api.Client) error { _, _, err := c.ACLTokens().Self(nil); return err }},
	{"acl_tokens.upsert_one_time_token", `{"OneTimeToken":{}}`, func(c *api.Client) error { _, _, err := c.ACLTokens().UpsertOneTimeToken(nil); return err }},
	{"acl_tokens.exchange_one_time_token", `{"Token":{}}`, func(c *api.Client) error { _, _, err := c.ACLTokens().ExchangeOneTimeToken("ott", nil); return err }},
	{"acl_roles.list", `[]`, func(c *api.Client) error { _, _, err := c.ACLRoles().List(nil); return err }},
	{"acl_roles.create", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLRoles().Create(&api.ACLRole{Name: "r", Description: "d", Policies: []*api.ACLRolePolicyLink{{Name: "p1"}}}, nil)
		return err
	}},
	{"acl_roles.update", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLRoles().Update(&api.ACLRole{ID: "rid", Name: "r2"}, nil)
		return err
	}},
	{"acl_roles.delete", `{}`, func(c *api.Client) error { _, err := c.ACLRoles().Delete("rid", nil); return err }},
	{"acl_roles.get", `{}`, func(c *api.Client) error { _, _, err := c.ACLRoles().Get("rid", nil); return err }},
	{"acl_roles.get_by_name", `{}`, func(c *api.Client) error { _, _, err := c.ACLRoles().GetByName("r", nil); return err }},
	{"acl_auth_methods.list", `[]`, func(c *api.Client) error { _, _, err := c.ACLAuthMethods().List(nil); return err }},
	{"acl_auth_methods.create", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLAuthMethods().Create(&api.ACLAuthMethod{
			Name: "m", Type: "JWT", TokenLocality: "global", TokenNameFormat: "${auth_method_type}-${value.sub}", MaxTokenTTL: time.Hour, Default: true,
			Config: &api.ACLAuthMethodConfig{JWKSURL: "https://idp.example/jwks", BoundAudiences: []string{"nomad"}, ClaimMappings: map[string]string{"sub": "user"},
				ExpirationLeeway: 90 * time.Second, ClockSkewLeeway: 1500 * time.Millisecond,
				OIDCClientAssertion: &api.OIDCClientAssertion{Audience: []string{"a"}, KeySource: api.OIDCKeySourceNomad, PrivateKey: &api.OIDCClientAssertionKey{KeyIDHeader: api.OIDCClientAssertionHeaderKid, KeyID: "k"}}},
		}, nil)
		return err
	}},
	{"acl_auth_methods.update", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLAuthMethods().Update(&api.ACLAuthMethod{Name: "m", Type: "JWT"}, nil)
		return err
	}},
	{"acl_auth_methods.delete", `{}`, func(c *api.Client) error { _, err := c.ACLAuthMethods().Delete("m", nil); return err }},
	{"acl_auth_methods.get", `{}`, func(c *api.Client) error { _, _, err := c.ACLAuthMethods().Get("m", nil); return err }},
	{"acl_binding_rules.list", `[]`, func(c *api.Client) error { _, _, err := c.ACLBindingRules().List(nil); return err }},
	{"acl_binding_rules.create", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLBindingRules().Create(&api.ACLBindingRule{Description: "d", AuthMethod: "m", Selector: "value.user == \"a\"", BindType: "policy", BindName: "p1"}, nil)
		return err
	}},
	{"acl_binding_rules.update", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLBindingRules().Update(&api.ACLBindingRule{ID: "bid", AuthMethod: "m", BindType: "role", BindName: "r"}, nil)
		return err
	}},
	{"acl_binding_rules.delete", `{}`, func(c *api.Client) error { _, err := c.ACLBindingRules().Delete("bid", nil); return err }},
	{"acl_binding_rules.get", `{}`, func(c *api.Client) error { _, _, err := c.ACLBindingRules().Get("bid", nil); return err }},
	{"acl_auth.get_auth_url", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLAuth().GetAuthURL(&api.ACLOIDCAuthURLRequest{AuthMethodName: "m", RedirectURI: "http://127.0.0.1/cb", ClientNonce: "n"}, nil)
		return err
	}},
	{"acl_auth.complete_auth", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLAuth().CompleteAuth(&api.ACLOIDCCompleteAuthRequest{AuthMethodName: "m", ClientNonce: "n", State: "s", Code: "c", Iss: "i", RedirectURI: "http://127.0.0.1/cb"}, nil)
		return err
	}},
	{"acl_auth.login", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLAuth().Login(&api.ACLLoginRequest{AuthMethodName: "m", LoginToken: "jwt"}, nil)
		return err
	}},
	{"acl_identity.create_client_introduction_token", `{}`, func(c *api.Client) error {
		_, _, err := c.ACLIdentity().CreateClientIntroductionToken(&api.ACLIdentityClientIntroductionTokenRequest{TTL: 5 * time.Minute, NodeName: "n", NodePool: "p"}, writeOpts)
		return err
	}},

	{"allocations.list", `[]`, func(c *api.Client) error { _, _, err := c.Allocations().List(nil); return err }},
	{"allocations.prefix_list", `[]`, func(c *api.Client) error { _, _, err := c.Allocations().PrefixList("pre"); return err }},
	{"allocations.info", `{}`, func(c *api.Client) error { _, _, err := c.Allocations().Info("a1", nil); return err }},
	{"allocations.stats", `{}`, func(c *api.Client) error {
		_, err := c.Allocations().Stats(&api.Allocation{ID: "a1"}, queryOpts())
		return err
	}},
	{"allocations.checks", `{}`, func(c *api.Client) error { _, err := c.Allocations().Checks("a1", nil); return err }},
	{"allocations.gc", `{}`, func(c *api.Client) error { return c.Allocations().GC(&api.Allocation{ID: "a1"}, queryOpts()) }},
	{"allocations.restart", `{}`, func(c *api.Client) error { return c.Allocations().Restart(&api.Allocation{ID: "a1"}, "t", nil) }},
	{"allocations.restart_all_tasks", `{}`, func(c *api.Client) error { return c.Allocations().RestartAllTasks(&api.Allocation{ID: "a1"}, nil) }},
	{"allocations.stop", `{}`, func(c *api.Client) error {
		_, err := c.Allocations().Stop(&api.Allocation{ID: "a1"}, queryOpts())
		return err
	}},
	{"allocations.signal", `{}`, func(c *api.Client) error {
		return c.Allocations().Signal(&api.Allocation{ID: "a1"}, nil, "t", "SIGHUP")
	}},
	{"allocations.set_pause_state", `{}`, func(c *api.Client) error {
		return c.Allocations().SetPauseState(&api.Allocation{ID: "a1"}, nil, "t", "pause")
	}},
	{"allocations.get_pause_state", `{}`, func(c *api.Client) error {
		_, _, err := c.Allocations().GetPauseState(&api.Allocation{ID: "a1"}, nil, "t")
		return err
	}},
	{"allocations.services", `[]`, func(c *api.Client) error { _, _, err := c.Allocations().Services("a1", nil); return err }},

	{"nodes.list", `[]`, func(c *api.Client) error { _, _, err := c.Nodes().List(nil); return err }},
	{"nodes.prefix_list", `[]`, func(c *api.Client) error { _, _, err := c.Nodes().PrefixListOpts("pre", queryOpts()); return err }},
	{"nodes.info", `{}`, func(c *api.Client) error { _, _, err := c.Nodes().Info("n1", nil); return err }},
	{"nodes.update_drain", `{}`, func(c *api.Client) error {
		_, err := c.Nodes().UpdateDrainOpts("n1", &api.DrainOptions{DrainSpec: &api.DrainSpec{Deadline: time.Hour, IgnoreSystemJobs: true}, MarkEligible: true, Meta: map[string]string{"k": "v"}}, writeOpts)
		return err
	}},
	{"nodes.update_drain_stop", `{}`, func(c *api.Client) error { _, err := c.Nodes().UpdateDrain("n1", nil, true, nil); return err }},
	{"nodes.toggle_eligibility", `{}`, func(c *api.Client) error { _, err := c.Nodes().ToggleEligibility("n1", false, nil); return err }},
	{"nodes.allocations", `[]`, func(c *api.Client) error { _, _, err := c.Nodes().Allocations("n1", nil); return err }},
	{"nodes.csi_volumes", `[]`, func(c *api.Client) error { _, err := c.Nodes().CSIVolumes("n1", nil); return err }},
	{"nodes.force_evaluate", `{}`, func(c *api.Client) error { _, _, err := c.Nodes().ForceEvaluate("n1", nil); return err }},
	{"nodes.stats", `{}`, func(c *api.Client) error { _, err := c.Nodes().Stats("n1", nil); return err }},
	{"nodes.gc", ``, func(c *api.Client) error { return c.Nodes().GC("n1", nil) }},
	{"nodes.gc_alloc", ``, func(c *api.Client) error { return c.Nodes().GcAlloc("a1", nil) }},
	{"nodes.purge", `{}`, func(c *api.Client) error { _, _, err := c.Nodes().Purge("n1", nil); return err }},
	{"node_meta.apply", `{}`, func(c *api.Client) error {
		_, err := c.Nodes().Meta().Apply(&api.NodeMetaApplyRequest{NodeID: "n1", Meta: map[string]*string{"k": new("v"), "gone": nil}}, nil)
		return err
	}},
	{"node_meta.read", `{}`, func(c *api.Client) error { _, err := c.Nodes().Meta().Read("n1", nil); return err }},
	{"node_identity.get", `{}`, func(c *api.Client) error {
		_, err := c.Nodes().Identity().Get(&api.NodeIdentityGetRequest{NodeID: "n1"}, nil)
		return err
	}},
	{"node_identity.renew", `{}`, func(c *api.Client) error {
		_, err := c.Nodes().Identity().Renew(&api.NodeIdentityRenewRequest{NodeID: "n1"}, nil)
		return err
	}},

	{"variables.create", `{}`, func(c *api.Client) error {
		_, _, err := c.Variables().Create(&api.Variable{Path: "/nomadpy/v1/", Namespace: "ns1", Items: api.VariableItems{"k": "v"}}, writeOpts)
		return err
	}},
	{"variables.checked_create", `{}`, func(c *api.Client) error {
		_, _, err := c.Variables().CheckedCreate(&api.Variable{Path: "nomadpy/v1", Items: api.VariableItems{"k": "v"}}, nil)
		return err
	}},
	{"variables.read", `{}`, func(c *api.Client) error { _, _, err := c.Variables().Read(" nomadpy/v1 ", queryOpts()); return err }},
	{"variables.peek", `{}`, func(c *api.Client) error { _, _, err := c.Variables().Peek("nomadpy/v1", nil); return err }},
	{"variables.update", `{}`, func(c *api.Client) error {
		_, _, err := c.Variables().Update(&api.Variable{Path: "nomadpy/v1", ModifyIndex: 9, Items: api.VariableItems{"k": "v2"}, Lock: &api.VariableLock{ID: "lid"}}, nil)
		return err
	}},
	{"variables.checked_update", `{}`, func(c *api.Client) error {
		_, _, err := c.Variables().CheckedUpdate(&api.Variable{Path: "nomadpy/v1", ModifyIndex: 9, Items: api.VariableItems{"k": "v2"}}, nil)
		return err
	}},
	{"variables.delete", `{}`, func(c *api.Client) error { _, err := c.Variables().Delete("nomadpy/v1", writeOpts); return err }},
	{"variables.checked_delete", `{}`, func(c *api.Client) error { _, err := c.Variables().CheckedDelete("nomadpy/v1", 9, nil); return err }},
	{"variables.list", `[]`, func(c *api.Client) error { _, _, err := c.Variables().List(nil); return err }},
	{"variables.prefix_list", `[]`, func(c *api.Client) error { _, _, err := c.Variables().PrefixList("nomadpy/", nil); return err }},
	{"variables.get_items", `{}`, func(c *api.Client) error { _, _, err := c.Variables().GetItems("nomadpy/v1", nil); return err }},
	{"variables.renew_lock", `{}`, func(c *api.Client) error {
		_, _, err := c.Variables().RenewLock(&api.Variable{Path: "nomadpy/v1", Lock: &api.VariableLock{ID: "lid"}}, nil)
		return err
	}},
	{"variables.release_lock", `{}`, func(c *api.Client) error {
		_, _, err := c.Variables().ReleaseLock(&api.Variable{Path: "nomadpy/v1", Lock: &api.VariableLock{ID: "lid"}}, nil)
		return err
	}},
	{"variables.acquire_lock", `{}`, func(c *api.Client) error {
		_, _, err := c.Variables().AcquireLock(&api.Variable{Path: "nomadpy/v1", Items: api.VariableItems{"k": "v"}, Lock: &api.VariableLock{TTL: "15s", LockDelay: "5s"}}, nil)
		return err
	}},

	{"agent.self", `{}`, func(c *api.Client) error { _, err := c.Agent().Self(); return err }},
	{"agent.join", `{}`, func(c *api.Client) error { _, err := c.Agent().Join("10.0.0.1:4648", "10.0.0.2:4648"); return err }},
	{"agent.members", `{}`, func(c *api.Client) error { _, err := c.Agent().MembersOpts(queryOpts()); return err }},
	{"agent.force_leave", `{}`, func(c *api.Client) error {
		return c.Agent().ForceLeaveWithOptions("n1", api.ForceLeaveOpts{Prune: true})
	}},
	{"agent.servers", `[]`, func(c *api.Client) error { _, err := c.Agent().Servers(); return err }},
	{"agent.set_servers", `{}`, func(c *api.Client) error { return c.Agent().SetServers([]string{"10.0.0.1:4647", "10.0.0.2:4647"}) }},
	{"agent.list_keys", `{}`, func(c *api.Client) error { _, err := c.Agent().ListKeys(); return err }},
	{"agent.reload", `{}`, func(c *api.Client) error { return c.Agent().Reload(nil, writeOpts) }},
	{"agent.install_key", `{}`, func(c *api.Client) error { _, err := c.Agent().InstallKey("k1"); return err }},
	{"agent.use_key", `{}`, func(c *api.Client) error { _, err := c.Agent().UseKey("k1"); return err }},
	{"agent.remove_key", `{}`, func(c *api.Client) error { _, err := c.Agent().RemoveKey("k1"); return err }},
	{"agent.health", `{}`, func(c *api.Client) error { _, err := c.Agent().Health(); return err }},
	{"agent.host", `{}`, func(c *api.Client) error { _, err := c.Agent().Host("s1", "n1", nil); return err }},
	{"agent.get_scheduler_worker_config", `{}`, func(c *api.Client) error { _, err := c.Agent().GetSchedulerWorkerConfig(nil); return err }},
	{"agent.set_scheduler_worker_config", `{}`, func(c *api.Client) error {
		_, err := c.Agent().SetSchedulerWorkerConfig(api.SchedulerWorkerPoolArgs{NumSchedulers: 2, EnabledSchedulers: []string{"service", "batch"}}, writeOpts)
		return err
	}},
	{"agent.get_scheduler_workers_info", `{}`, func(c *api.Client) error { _, err := c.Agent().GetSchedulerWorkersInfo(nil); return err }},
	{"operator.raft_get_configuration", `{}`, func(c *api.Client) error { _, err := c.Operator().RaftGetConfiguration(queryOpts()); return err }},
	{"operator.raft_remove_peer_by_address", `{}`, func(c *api.Client) error { return c.Operator().RaftRemovePeerByAddress("10.0.0.1:4647", writeOpts) }},
	{"operator.raft_remove_peer_by_id", `{}`, func(c *api.Client) error { return c.Operator().RaftRemovePeerByID("id1", nil) }},
	{"operator.raft_transfer_leadership_by_address", `{}`, func(c *api.Client) error { return c.Operator().RaftTransferLeadershipByAddress("10.0.0.1:4647", nil) }},
	{"operator.raft_transfer_leadership_by_id", `{}`, func(c *api.Client) error { return c.Operator().RaftTransferLeadershipByID("id1", writeOpts) }},
	{"operator.scheduler_get_configuration", `{}`, func(c *api.Client) error { _, _, err := c.Operator().SchedulerGetConfiguration(nil); return err }},
	{"operator.scheduler_set_configuration", `{}`, func(c *api.Client) error {
		_, _, err := c.Operator().SchedulerSetConfiguration(&api.SchedulerConfiguration{SchedulerAlgorithm: api.SchedulerAlgorithmSpread, PreemptionConfig: api.PreemptionConfig{ServiceSchedulerEnabled: true}, PauseEvalBroker: true, ModifyIndex: 3}, nil)
		return err
	}},
	{"operator.scheduler_cas_configuration", `{}`, func(c *api.Client) error {
		_, _, err := c.Operator().SchedulerCASConfiguration(&api.SchedulerConfiguration{SchedulerAlgorithm: api.SchedulerAlgorithmBinpack, ModifyIndex: 3}, writeOpts)
		return err
	}},
	{"operator.apply_license", `{}`, func(c *api.Client) error {
		_, err := c.Operator().ApplyLicense("02MV4UU43BK5", &api.ApplyLicenseOptions{Force: true}, writeOpts)
		return err
	}},
	{"operator.license_get", `{}`, func(c *api.Client) error { _, _, err := c.Operator().LicenseGet(queryOpts()); return err }},
	{"operator.upgrade_check_vault_workload_identity", `{}`, func(c *api.Client) error {
		_, _, err := c.Operator().UpgradeCheckVaultWorkloadIdentity(nil)
		return err
	}},
	{"operator.utilization", `{}`, func(c *api.Client) error {
		_, _, err := c.Operator().Utilization(&api.OperatorUtilizationOptions{TodayOnly: true}, writeOpts)
		return err
	}},
	{"operator.autopilot_get_configuration", `{}`, func(c *api.Client) error { _, _, err := c.Operator().AutopilotGetConfiguration(nil); return err }},
	{"operator.autopilot_set_configuration", `true`, func(c *api.Client) error {
		_, err := c.Operator().AutopilotSetConfiguration(&api.AutopilotConfiguration{CleanupDeadServers: true, LastContactThreshold: 200 * time.Millisecond, MaxTrailingLogs: 250, MinQuorum: 3, ServerStabilizationTime: 10 * time.Second, EnableRedundancyZones: true, ModifyIndex: 4}, nil)
		return err
	}},
	{"operator.autopilot_cas_configuration", `true`, func(c *api.Client) error {
		_, _, err := c.Operator().AutopilotCASConfiguration(&api.AutopilotConfiguration{CleanupDeadServers: true, ModifyIndex: 4}, writeOpts)
		return err
	}},
	{"operator.autopilot_server_health", `{}`, func(c *api.Client) error { _, _, err := c.Operator().AutopilotServerHealth(nil); return err }},
	{"operator.metrics", `{}`, func(c *api.Client) error {
		q := queryOpts()
		q.Params["format"] = "prometheus"
		_, err := c.Operator().Metrics(q)
		return err
	}},
	{"operator.metrics_summary", `{}`, func(c *api.Client) error { _, _, err := c.Operator().MetricsSummary(nil); return err }},

	{"quotas.list", `[]`, func(c *api.Client) error { _, _, err := c.Quotas().List(nil); return err }},
	{"quotas.prefix_list", `[]`, func(c *api.Client) error { _, _, err := c.Quotas().PrefixList("pre", nil); return err }},
	{"quotas.list_usage", `[]`, func(c *api.Client) error { _, _, err := c.Quotas().ListUsage(nil); return err }},
	{"quotas.prefix_list_usage", `[]`, func(c *api.Client) error { _, _, err := c.Quotas().PrefixListUsage("pre", queryOpts()); return err }},
	{"quotas.info", `{}`, func(c *api.Client) error { _, _, err := c.Quotas().Info("q1", nil); return err }},
	{"quotas.usage", `{}`, func(c *api.Client) error { _, _, err := c.Quotas().Usage("q1", nil); return err }},
	{"quotas.register", `{}`, func(c *api.Client) error {
		_, err := c.Quotas().Register(&api.QuotaSpec{Name: "q1", Description: "d", Limits: []*api.QuotaLimit{{
			Region: "global", VariablesLimit: new(5),
			RegionLimit: &api.QuotaResources{CPU: new(1000), MemoryMB: new(1024), Storage: &api.QuotaStorageResources{VariablesMB: 10, HostVolumesMB: 20},
				NodePools: []*api.NodePoolLimit{{NodePool: "default", Cores: new(2)}}},
		}}}, writeOpts)
		return err
	}},
	{"quotas.delete", `{}`, func(c *api.Client) error { _, err := c.Quotas().Delete("q1", nil); return err }},
	{"sentinel_policies.list", `[]`, func(c *api.Client) error { _, _, err := c.SentinelPolicies().List(nil); return err }},
	{"sentinel_policies.upsert", `{}`, func(c *api.Client) error {
		_, err := c.SentinelPolicies().Upsert(&api.SentinelPolicy{Name: "s1", Description: "d", Scope: "submit-job", EnforcementLevel: "advisory", Policy: "main = rule { true }"}, writeOpts)
		return err
	}},
	{"sentinel_policies.delete", `{}`, func(c *api.Client) error { _, err := c.SentinelPolicies().Delete("s1", nil); return err }},
	{"sentinel_policies.info", `{}`, func(c *api.Client) error { _, _, err := c.SentinelPolicies().Info("s1", nil); return err }},

	{"namespaces.list", `[]`, func(c *api.Client) error { _, _, err := c.Namespaces().List(nil); return err }},
	{"namespaces.prefix_list", `[]`, func(c *api.Client) error { _, _, err := c.Namespaces().PrefixList("pre", queryOpts()); return err }},
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
