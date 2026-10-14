import time

import pytest

from nomadpy import UnexpectedResponseError
from nomadpy.keyring import (
    ENCRYPTION_ALGORITHM_AES256_GCM,
    ROOT_KEY_STATE_ACTIVE,
    ROOT_KEY_STATE_PREPUBLISHED,
)


# Rotating and deleting root keys invalidates identities signed by the old key, so these tests get their own agent.
def test_list_rotate_delete(disposable_client):
    client = disposable_client
    keys, qm = client.keyring.list()
    assert len(keys) == 1 and qm.last_index >= 0
    original = keys[0]
    assert original.state == ROOT_KEY_STATE_ACTIVE and original.algorithm == ENCRYPTION_ALGORITHM_AES256_GCM
    assert original.key_id and original.create_time > 0

    rotated, wm = client.keyring.rotate()
    assert rotated.key_id != original.key_id and rotated.state == ROOT_KEY_STATE_ACTIVE and wm.last_index > 0
    states = {k.key_id: k.state for k in client.keyring.list()[0]}
    assert states[rotated.key_id] == ROOT_KEY_STATE_ACTIVE and states[original.key_id] != ROOT_KEY_STATE_ACTIVE

    with pytest.raises(UnexpectedResponseError) as e:
        client.keyring.delete(rotated.key_id)
    assert e.value.status_code == 500
    client.keyring.delete(original.key_id, force=True)
    assert original.key_id not in {k.key_id for k in client.keyring.list()[0]}


def test_prepublish(disposable_client):
    client = disposable_client
    future = int((time.time() + 3600) * 1e9)
    key, _ = client.keyring.rotate(publish_time=future)
    assert key.state == ROOT_KEY_STATE_PREPUBLISHED and key.publish_time == future
    client.keyring.delete(key.key_id, force=True)
