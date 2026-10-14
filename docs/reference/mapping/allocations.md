# Allocations

[Allocations][nomadpy.allocations.Allocations] in `nomadpy.allocations`.

| Python | Go | HTTP | API docs |
|---|---|---|---|
| [checks][nomadpy.allocations.Allocations.checks] | Checks | `GET /v1/client/allocation/a1/checks` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) |
| [gc][nomadpy.allocations.Allocations.gc] | GC | `GET /v1/client/allocation/a1/gc` | [client](https://developer.hashicorp.com/nomad/api-docs/client) |
| [get_pause_state][nomadpy.allocations.Allocations.get_pause_state] | GetPauseState | `GET /v1/client/allocation/a1/pause` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) Enterprise |
| [info][nomadpy.allocations.Allocations.info] | Info | `GET /v1/allocation/a1` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) |
| [list][nomadpy.allocations.Allocations.list] | List | `GET /v1/allocations` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) |
| [prefix_list][nomadpy.allocations.Allocations.prefix_list] | PrefixList | `GET /v1/allocations` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) |
| [restart][nomadpy.allocations.Allocations.restart] | Restart | `PUT /v1/client/allocation/a1/restart` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) |
| [restart_all_tasks][nomadpy.allocations.Allocations.restart_all_tasks] | RestartAllTasks | `PUT /v1/client/allocation/a1/restart` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) |
| [services][nomadpy.allocations.Allocations.services] | Services | `GET /v1/allocation/a1/services` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) |
| [set_pause_state][nomadpy.allocations.Allocations.set_pause_state] | SetPauseState | `PUT /v1/client/allocation/a1/pause` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) Enterprise |
| [signal][nomadpy.allocations.Allocations.signal] | Signal | `PUT /v1/client/allocation/a1/signal` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) |
| [stats][nomadpy.allocations.Allocations.stats] | Stats | `GET /v1/client/allocation/a1/stats` | [client](https://developer.hashicorp.com/nomad/api-docs/client) |
| [stop][nomadpy.allocations.Allocations.stop] | Stop | `PUT /v1/allocation/a1/stop` | [allocations](https://developer.hashicorp.com/nomad/api-docs/allocations) |
