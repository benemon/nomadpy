# Agent

[Agent][nomadpy.agent.Agent] in `nomadpy.agent`.

| Python | Go | HTTP | API docs |
|---|---|---|---|
| [datacenter][nomadpy.agent.Agent.datacenter] | Datacenter |  | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [force_leave][nomadpy.agent.Agent.force_leave] | ForceLeave, ForceLeaveWithOptions | `PUT /v1/agent/force-leave` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [get_scheduler_worker_config][nomadpy.agent.Agent.get_scheduler_worker_config] | GetSchedulerWorkerConfig | `GET /v1/agent/schedulers/config` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [get_scheduler_workers_info][nomadpy.agent.Agent.get_scheduler_workers_info] | GetSchedulerWorkersInfo | `GET /v1/agent/schedulers` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [health][nomadpy.agent.Agent.health] | Health | `GET /v1/agent/health` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [host][nomadpy.agent.Agent.host] | Host | `GET /v1/agent/host` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [install_key][nomadpy.agent.Agent.install_key] | InstallKey | `PUT /v1/agent/keyring/install` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [join][nomadpy.agent.Agent.join] | Join | `PUT /v1/agent/join` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [list_keys][nomadpy.agent.Agent.list_keys] | ListKeys | `GET /v1/agent/keyring/list` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [members][nomadpy.agent.Agent.members] | Members, MembersOpts | `GET /v1/agent/members` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [node_name][nomadpy.agent.Agent.node_name] | NodeName |  | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [region][nomadpy.agent.Agent.region] | Region |  | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [reload][nomadpy.agent.Agent.reload] | Reload | `PUT /v1/agent/reload` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [remove_key][nomadpy.agent.Agent.remove_key] | RemoveKey | `PUT /v1/agent/keyring/remove` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [self][nomadpy.agent.Agent.self] | Self | `GET /v1/agent/self` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [servers][nomadpy.agent.Agent.servers] | Servers | `GET /v1/agent/servers` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [set_scheduler_worker_config][nomadpy.agent.Agent.set_scheduler_worker_config] | SetSchedulerWorkerConfig | `PUT /v1/agent/schedulers/config` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [set_servers][nomadpy.agent.Agent.set_servers] | SetServers | `PUT /v1/agent/servers` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
| [use_key][nomadpy.agent.Agent.use_key] | UseKey | `PUT /v1/agent/keyring/use` | [agent](https://developer.hashicorp.com/nomad/api-docs/agent) |
