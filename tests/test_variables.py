import pytest

from nomadpy import ErrCASConflict, QueryOptions, UnexpectedResponseError, Variable, VariableLock, WriteOptions


def test_create_read_update_delete(client):
    created, wm = client.variables.create(Variable(path="/nomadpy/app/config/", items={"user": "a", "pass": "b"}))
    assert created.path == "nomadpy/app/config" and created.namespace == "default"
    assert created.items == {"user": "a", "pass": "b"}
    assert created.modify_index > 0 and wm.last_index == created.modify_index

    got, qm = client.variables.read("nomadpy/app/config")
    assert got == created and qm.last_index >= created.modify_index
    items, _ = client.variables.get_items("nomadpy/app/config")
    assert items == {"user": "a", "pass": "b"}

    got.items["user"] = "c"
    updated, _ = client.variables.update(got)
    assert updated.items["user"] == "c" and updated.modify_index > created.modify_index

    metas, _ = client.variables.list()
    assert "nomadpy/app/config" in [m.path for m in metas]
    assert all(not hasattr(m, "items") for m in metas)
    by_prefix, _ = client.variables.prefix_list("nomadpy/app")
    assert [m.path for m in by_prefix] == ["nomadpy/app/config"]

    wm = client.variables.delete("nomadpy/app/config")
    assert wm.last_index > 0
    peeked, _ = client.variables.peek("nomadpy/app/config")
    assert peeked is None
    with pytest.raises(LookupError):
        client.variables.read("nomadpy/app/config")
    with pytest.raises(LookupError):
        client.variables.get_items("nomadpy/app/config")


def test_checked_operations(client):
    v, _ = client.variables.checked_create(Variable(path="nomadpy/cas", items={"k": "1"}))
    assert v.modify_index > 0
    with pytest.raises(ErrCASConflict) as e:
        client.variables.checked_create(Variable(path="nomadpy/cas", items={"k": "2"}))
    assert e.value.check_index == 0 and e.value.conflict.items == {"k": "1"}

    stale = Variable(path="nomadpy/cas", modify_index=v.modify_index - 1, items={"k": "3"})
    with pytest.raises(ErrCASConflict) as e:
        client.variables.checked_update(stale)
    assert e.value.check_index == stale.modify_index and e.value.conflict.modify_index == v.modify_index

    v.items["k"] = "4"
    updated, _ = client.variables.checked_update(v)
    assert updated.items == {"k": "4"}

    with pytest.raises(ErrCASConflict):
        client.variables.checked_delete("nomadpy/cas", v.modify_index)
    client.variables.checked_delete("nomadpy/cas", updated.modify_index)
    assert client.variables.peek("nomadpy/cas")[0] is None


def test_locks(client):
    locked, _ = client.variables.acquire_lock(Variable(path="nomadpy/lock", items={"k": "v"}, lock=VariableLock(ttl="15s", lock_delay="5s")))
    assert locked.lock_id() and locked.lock.ttl == "15s"

    with pytest.raises(UnexpectedResponseError) as e:
        client.variables.update(Variable(path="nomadpy/lock", items={"k": "stolen"}))
    assert e.value.status_code == 409

    meta, _ = client.variables.renew_lock(Variable(path="nomadpy/lock", lock=VariableLock(id=locked.lock_id())))
    assert meta.lock.id == locked.lock_id()

    released, _ = client.variables.release_lock(Variable(path="nomadpy/lock", lock=VariableLock(id=locked.lock_id())))
    assert released.lock is None
    client.variables.delete("nomadpy/lock")


def test_namespace_scoping(client):
    client.put("/v1/namespace/nomadpy-vars", {"Name": "nomadpy-vars"})
    client.variables.create(Variable(path="nomadpy/scoped", namespace="nomadpy-vars", items={"k": "v"}), WriteOptions(namespace="nomadpy-vars"))
    assert client.variables.peek("nomadpy/scoped")[0] is None
    got, _ = client.variables.read("nomadpy/scoped", QueryOptions(namespace="nomadpy-vars"))
    assert got.namespace == "nomadpy-vars"
    client.variables.delete("nomadpy/scoped", WriteOptions(namespace="nomadpy-vars"))
    client.delete("/v1/namespace/nomadpy-vars")


def test_model_helpers():
    v = Variable(path="p", namespace="n", items={"a": "b"}, lock=VariableLock(id="x"))
    assert v.metadata().path == "p" and v.metadata().lock is None
    assert v.lock_id() == "x"
    assert not v.is_zero_value()
    assert Variable().is_zero_value()
    assert "Lock" not in Variable(path="p").to_json()
