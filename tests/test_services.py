
from jobspecs import register_and_wait

from nomadpy.search import CONTEXT_ALL, CONTEXT_JOBS, CONTEXT_NODES


def test_service_registrations(client):
    register_and_wait(client, "nomadpy-services", nomad_service=True)
    try:
        listed, qm = client.services.list()
        assert qm.last_index > 0
        default = next(ns for ns in listed if ns.namespace == "default")
        stub = next(s for s in default.services if s.service_name == "nomadpy-services-svc")
        assert stub.tags == ["nomadpy"]

        regs, _ = client.services.get("nomadpy-services-svc")
        assert len(regs) == 1
        reg = regs[0]
        assert reg.job_id == "nomadpy-services" and reg.alloc_id and reg.port > 0 and reg.address
        by_job, _ = client.jobs.services("nomadpy-services")
        assert by_job == regs
        by_alloc, _ = client.allocations.services(reg.alloc_id)
        assert by_alloc == regs

        wm = client.services.delete("nomadpy-services-svc", reg.id)
        assert wm.last_index > 0
        assert client.services.get("nomadpy-services-svc")[0] == []
    finally:
        client.jobs.deregister("nomadpy-services", purge=True)


def test_search(client):
    register_and_wait(client, "nomadpy-search")
    try:
        resp, qm = client.search.prefix_search("nomadpy-sea", CONTEXT_JOBS)
        assert resp.matches[CONTEXT_JOBS] == ["nomadpy-search"] and resp.truncations[CONTEXT_JOBS] is False
        assert qm.last_index > 0
        resp, _ = client.search.prefix_search("nomadpy-sea", CONTEXT_ALL)
        assert resp.matches[CONTEXT_JOBS] == ["nomadpy-search"]
        nodes, _ = client.nodes.list()
        resp, _ = client.search.prefix_search(nodes[0].id[:8], CONTEXT_NODES)
        assert resp.matches[CONTEXT_NODES] == [nodes[0].id]

        fuzzy, _ = client.search.fuzzy_search("search", CONTEXT_ALL)
        assert [m.id for m in fuzzy.matches[CONTEXT_JOBS]] == ["nomadpy-search"]
        assert fuzzy.matches[CONTEXT_JOBS][0].scope == ["default", "nomadpy-search"]
    finally:
        client.jobs.deregister("nomadpy-search", purge=True)


def test_system(client):
    client.system.garbage_collect()
    client.system.reconcile_summaries()
