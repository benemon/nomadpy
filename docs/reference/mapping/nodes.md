# Nodes

[Nodes][nomadpy.nodes.Nodes] in `nomadpy.nodes`.

| Python | Go | HTTP | API docs |
|---|---|---|---|
| [allocations][nomadpy.nodes.Nodes.allocations] | Allocations | `GET /v1/node/n1/allocations` | [nodes](https://developer.hashicorp.com/nomad/api-docs/nodes) |
| [csi_volumes][nomadpy.nodes.Nodes.csi_volumes] | CSIVolumes | `GET /v1/volumes` | [nodes](https://developer.hashicorp.com/nomad/api-docs/nodes) |
| [force_evaluate][nomadpy.nodes.Nodes.force_evaluate] | ForceEvaluate | `PUT /v1/node/n1/evaluate` | [nodes](https://developer.hashicorp.com/nomad/api-docs/nodes) |
| [gc][nomadpy.nodes.Nodes.gc] | GC | `GET /v1/client/gc` | [client](https://developer.hashicorp.com/nomad/api-docs/client) |
| [gc_alloc][nomadpy.nodes.Nodes.gc_alloc] | GcAlloc | `GET /v1/client/allocation/a1/gc` | [client](https://developer.hashicorp.com/nomad/api-docs/client) |
| [info][nomadpy.nodes.Nodes.info] | Info | `GET /v1/node/n1` | [nodes](https://developer.hashicorp.com/nomad/api-docs/nodes) |
| [list][nomadpy.nodes.Nodes.list] | List | `GET /v1/nodes` | [nodes](https://developer.hashicorp.com/nomad/api-docs/nodes) |
| [prefix_list][nomadpy.nodes.Nodes.prefix_list] | PrefixList, PrefixListOpts | `GET /v1/nodes` | [nodes](https://developer.hashicorp.com/nomad/api-docs/nodes) |
| [purge][nomadpy.nodes.Nodes.purge] | Purge | `PUT /v1/node/n1/purge` | [nodes](https://developer.hashicorp.com/nomad/api-docs/nodes) |
| [stats][nomadpy.nodes.Nodes.stats] | Stats | `GET /v1/client/stats` | [client](https://developer.hashicorp.com/nomad/api-docs/client) |
| [toggle_eligibility][nomadpy.nodes.Nodes.toggle_eligibility] | ToggleEligibility | `PUT /v1/node/n1/eligibility` | [nodes](https://developer.hashicorp.com/nomad/api-docs/nodes) |
| [update_drain][nomadpy.nodes.Nodes.update_drain] | UpdateDrain, UpdateDrainOpts | `PUT /v1/node/n1/drain` | [nodes](https://developer.hashicorp.com/nomad/api-docs/nodes) |
