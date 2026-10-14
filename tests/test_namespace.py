import pytest

from nomadpy import Namespace, NamespaceCapabilities, NamespaceNodePoolConfiguration, QueryOptions, UnexpectedResponseError


def test_register_info_list_delete(client):
    ns = Namespace(name="nomadpy-ns1", description="d", meta={"team": "a"},
                   capabilities=NamespaceCapabilities(enabled_task_drivers=["raw_exec"]))
    wm = client.namespaces.register(ns)
    assert wm.last_index > 0

    got, qm = client.namespaces.info("nomadpy-ns1")
    assert got.name == "nomadpy-ns1"
    assert got.description == "d"
    assert got.meta == {"team": "a"}
    assert got.capabilities.enabled_task_drivers == ["raw_exec"]
    assert got.capabilities.disabled_task_drivers is None
    assert got.create_index > 0 and qm.last_index >= got.modify_index

    namespaces, _ = client.namespaces.list()
    names = [n.name for n in namespaces]
    assert "nomadpy-ns1" in names and "default" in names
    assert [n.create_index for n in namespaces] == sorted((n.create_index for n in namespaces), reverse=True)

    by_prefix, _ = client.namespaces.prefix_list("nomadpy-ns")
    assert [n.name for n in by_prefix] == ["nomadpy-ns1"]
    by_prefix, _ = client.namespaces.prefix_list("nomadpy-ns", QueryOptions(allow_stale=True))
    assert [n.name for n in by_prefix] == ["nomadpy-ns1"]

    ns.description = "updated"
    client.namespaces.register(ns)
    got, _ = client.namespaces.info("nomadpy-ns1")
    assert got.description == "updated"

    client.namespaces.delete("nomadpy-ns1")
    with pytest.raises(UnexpectedResponseError) as e:
        client.namespaces.info("nomadpy-ns1")
    assert e.value.status_code == 404


def test_round_trip_to_json():
    ns = Namespace(name="nomadpy-ns2", node_pool_configuration=None)
    assert ns.to_json()["Name"] == "nomadpy-ns2"
    assert ns.to_json()["NodePoolConfiguration"] is None
    assert Namespace.from_json(ns.to_json()) == ns


def test_quota_on_community(client):
    with pytest.raises(UnexpectedResponseError) as e:
        client.namespaces.register(Namespace(name="nomadpy-ns3", quota="nope"))
    assert e.value.status_code == 500
    assert 'quota "nope"' in e.value.body


def test_node_pool_configuration_on_community(client):
    with pytest.raises(UnexpectedResponseError) as e:
        client.namespaces.register(Namespace(name="nomadpy-ns4", node_pool_configuration=NamespaceNodePoolConfiguration(default="all")))
    assert e.value.status_code == 500


def test_node_pool_configuration_on_enterprise(ent_client):
    ent_client.namespaces.register(Namespace(name="nomadpy-ns5", node_pool_configuration=NamespaceNodePoolConfiguration(default="all")))
    got, _ = ent_client.namespaces.info("nomadpy-ns5")
    assert got.node_pool_configuration.default == "all"
    ent_client.namespaces.delete("nomadpy-ns5")
