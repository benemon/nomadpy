# Variables

[Variables][nomadpy.variables.Variables] in `nomadpy.variables`.

| Python | Go | HTTP | API docs |
|---|---|---|---|
| [acquire_lock][nomadpy.variables.Variables.acquire_lock] | AcquireLock | `PUT /v1/var/nomadpy/v1` | [variables/locks](https://developer.hashicorp.com/nomad/api-docs/variables/locks) |
| [checked_create][nomadpy.variables.Variables.checked_create] | CheckedCreate | `PUT /v1/var/nomadpy/v1` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
| [checked_delete][nomadpy.variables.Variables.checked_delete] | CheckedDelete | `DELETE /v1/var/nomadpy/v1` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
| [checked_update][nomadpy.variables.Variables.checked_update] | CheckedUpdate | `PUT /v1/var/nomadpy/v1` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
| [create][nomadpy.variables.Variables.create] | Create | `PUT /v1/var/nomadpy/v1` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
| [delete][nomadpy.variables.Variables.delete] | Delete | `DELETE /v1/var/nomadpy/v1` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
| [get_items][nomadpy.variables.Variables.get_items] | GetItems, GetVariableItems | `GET /v1/var/nomadpy/v1` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
| [list][nomadpy.variables.Variables.list] | List | `GET /v1/vars` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
| [peek][nomadpy.variables.Variables.peek] | Peek | `GET /v1/var/nomadpy/v1` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
| [prefix_list][nomadpy.variables.Variables.prefix_list] | PrefixList | `GET /v1/vars` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
| [read][nomadpy.variables.Variables.read] | Read | `GET /v1/var/nomadpy/v1` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
| [release_lock][nomadpy.variables.Variables.release_lock] | ReleaseLock | `PUT /v1/var/nomadpy/v1` | [variables/locks](https://developer.hashicorp.com/nomad/api-docs/variables/locks) |
| [renew_lock][nomadpy.variables.Variables.renew_lock] | RenewLock | `PUT /v1/var/nomadpy/v1` | [variables/locks](https://developer.hashicorp.com/nomad/api-docs/variables/locks) |
| [update][nomadpy.variables.Variables.update] | Update | `PUT /v1/var/nomadpy/v1` | [variables/variables](https://developer.hashicorp.com/nomad/api-docs/variables/variables) |
