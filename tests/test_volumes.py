import pytest

from nomadpy import CSIVolume, CSIVolumeCapability, HostVolume, HostVolumeCapability, UnexpectedResponseError
from nomadpy.host_volumes import (
    HOST_VOLUME_ACCESS_MODE_SINGLE_NODE_WRITER,
    HOST_VOLUME_ATTACHMENT_MODE_FILESYSTEM,
    HOST_VOLUME_STATE_READY,
)


def test_csi_without_plugins(client):
    """A dev agent has no CSI plugin, so the CSI surface can only be exercised for its empty and error paths."""
    assert client.csi_volumes.list()[0] == []
    assert client.csi_volumes.plugin_list("none")[0] == []
    assert client.csi_plugins.list()[0] == []
    nodes, _ = client.nodes.list()
    assert client.nodes.csi_volumes(nodes[0].id) == []
    with pytest.raises(UnexpectedResponseError) as e:
        client.csi_volumes.info("no-such-volume")
    assert e.value.status_code == 404
    with pytest.raises(UnexpectedResponseError) as e:
        client.csi_plugins.info("no-such-plugin")
    assert e.value.status_code == 404
    with pytest.raises(UnexpectedResponseError) as e:
        client.csi_volumes.register(CSIVolume(id="nomadpy-csi", name="v", plugin_id="no-such-plugin", external_id="x",
                                              requested_capabilities=[CSIVolumeCapability(access_mode="single-node-writer", attachment_mode="file-system")]))
    assert e.value.status_code == 500 and e.value.body
    with pytest.raises(UnexpectedResponseError):
        client.csi_volumes.list_external("no-such-plugin")
    with pytest.raises(UnexpectedResponseError):
        client.csi_volumes.list_snapshots("no-such-plugin")


def test_dynamic_host_volume(client):
    nodes, _ = client.nodes.list()
    volume = HostVolume(name="nomadpy-hv", plugin_id="mkdir", node_pool="default", parameters={"mode": "0700"},
                        requested_capabilities=[HostVolumeCapability(attachment_mode=HOST_VOLUME_ATTACHMENT_MODE_FILESYSTEM,
                                                                     access_mode=HOST_VOLUME_ACCESS_MODE_SINGLE_NODE_WRITER)])
    created, wm = client.host_volumes.create(volume)
    assert created.volume.id and created.volume.node_id == nodes[0].id and wm.last_index > 0
    try:
        got, _ = client.host_volumes.get(created.volume.id)
        assert got.name == "nomadpy-hv" and got.host_path and got.state in (HOST_VOLUME_STATE_READY, "pending")
        stubs, _ = client.host_volumes.list(node_id=nodes[0].id)
        assert created.volume.id in [s.id for s in stubs]
        stubs, _ = client.host_volumes.list(node_pool="no-such-pool")
        assert stubs == []
        claims, _ = client.task_group_host_volume_claims.list(volume_name="nomadpy-hv")
        assert claims == []
    finally:
        client.host_volumes.delete(created.volume.id)
    with pytest.raises(UnexpectedResponseError) as e:
        client.host_volumes.get(created.volume.id)
    assert e.value.status_code == 404


def test_register_static_host_volume(client, tmp_path):
    nodes, _ = client.nodes.list()
    registered, _ = client.host_volumes.register(HostVolume(name="nomadpy-static", node_id=nodes[0].id, host_path=str(tmp_path), capacity_bytes=1024))
    assert registered.volume.id and registered.volume.host_path == str(tmp_path)
    client.host_volumes.delete(registered.volume.id, force=True)
    with pytest.raises(UnexpectedResponseError):
        client.task_group_host_volume_claims.delete("00000000-0000-0000-0000-000000000000")
