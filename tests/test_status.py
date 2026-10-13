def test_leader_and_peers(client):
    leader = client.status.leader()
    assert leader.startswith("127.0.0.1:")
    assert client.status.region_leader("global") == leader
    assert client.status.peers() == [leader]
