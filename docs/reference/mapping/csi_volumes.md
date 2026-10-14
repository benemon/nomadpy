# CSIVolumes

[CSIVolumes][nomadpy.csi.CSIVolumes] in `nomadpy.csi`.

| Python | Go | HTTP | API docs |
|---|---|---|---|
| [create][nomadpy.csi.CSIVolumes.create] | Create, CreateOpts | `PUT /v1/volume/csi/v1/create` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [create_snapshot][nomadpy.csi.CSIVolumes.create_snapshot] | CreateSnapshot | `PUT /v1/volumes/snapshot` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [delete][nomadpy.csi.CSIVolumes.delete] | Delete, DeleteOpts | `DELETE /v1/volume/csi/ext 1/delete` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [delete_snapshot][nomadpy.csi.CSIVolumes.delete_snapshot] | DeleteSnapshot | `DELETE /v1/volumes/snapshot` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [deregister][nomadpy.csi.CSIVolumes.deregister] | Deregister | `DELETE /v1/volume/csi/v 1` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [detach][nomadpy.csi.CSIVolumes.detach] | Detach | `DELETE /v1/volume/csi/v1/detach` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [info][nomadpy.csi.CSIVolumes.info] | Info | `GET /v1/volume/csi/v1` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [list][nomadpy.csi.CSIVolumes.list] | List | `GET /v1/volumes` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [list_external][nomadpy.csi.CSIVolumes.list_external] | ListExternal | `GET /v1/volumes/external` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [list_snapshots][nomadpy.csi.CSIVolumes.list_snapshots] | ListSnapshots, ListSnapshotsOpts | `GET /v1/volumes/snapshot` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [plugin_list][nomadpy.csi.CSIVolumes.plugin_list] | PluginList | `GET /v1/volumes` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
| [register][nomadpy.csi.CSIVolumes.register] | Register, RegisterOpts | `PUT /v1/volume/csi/v1` | [volumes](https://developer.hashicorp.com/nomad/api-docs/volumes) |
