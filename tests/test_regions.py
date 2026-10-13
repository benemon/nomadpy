def test_list(client):
    assert client.regions.list() == ["global"]
