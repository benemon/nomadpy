# Errors and editions

## UnexpectedResponseError

A response whose status is not one the method expects raises
[UnexpectedResponseError][nomadpy.error_unexpected_response.UnexpectedResponseError]
with `status_code`, `status_text`, `body` (the response body as text) and
`expected` (the statuses the method accepts). Most methods expect `200`.
Connection failures raise `urllib.error.URLError`. A client certificate
without its key, or the reverse, raises `ValueError` when the client is built.

```python
from nomadpy import Client, UnexpectedResponseError

client = Client()
try:
    client.jobs.info("missing")
except UnexpectedResponseError as e:
    print(e.status_code, e.body)  # 404 job not found
```

[Client.request][nomadpy.api.Client.request] is the general form: any
status in `expected` is returned with its decoded body instead of raised.

## ErrCASConflict

The checked variable operations (`checked_create`, `checked_update`,
`checked_delete`) raise
[ErrCASConflict][nomadpy.variables.ErrCASConflict] when the server's
modify index differs from `check_index`; `conflict` is the variable the
server holds.

## Editions

Community and Enterprise surfaces are implemented identically. There is no
client-side gating or licence detection: an Enterprise call against a
Community server is an ordinary failed request and raises
`UnexpectedResponseError` like any other non-2xx response. Enterprise
endpoints and fields are marked in the docstrings and in the
[Go and HTTP mapping](reference/mapping/index.md) as the
[Nomad API docs](https://developer.hashicorp.com/nomad/api-docs) mark them.

Enterprise-only surfaces as of the current API docs:

- Endpoint groups: quotas, Sentinel policies, recommendations, `/v1/operator/license`, `/v1/operator/utilization`, allocation task pause.
- Fields on Community resources: namespace `Quota` and `NodePoolConfiguration`; node pool `SchedulerConfiguration`; job `Multiregion`; vertical scaling policies; autopilot redundancy-zone and upgrade-migration settings.

Quotas and Sentinel additionally require the Governance & Policy module on
the licence, and Sentinel requires ACLs to be enabled on the server.

### Observed Community responses

Nomad Community 2.0.5 answers Enterprise calls as follows. The integration
tests assert these responses.

| Request | Community response |
|---|---|
| `GET /v1/quotas`, `/v1/sentinel/policies`, `/v1/recommendations` | 501, body `Nomad Enterprise only endpoint` |
| `GET /v1/operator/license` | 204, empty body; `license_get` returns `None` |
| Namespace with `Quota` set | 500, body names the non-existent quota |
| Node pool with `SchedulerConfiguration` | 500, body `Feature "Node Pools Governance" is unlicensed` |
| Allocation task pause endpoints | 500, body `Enterprise only` |
| `POST /v1/operator/utilization` | 501, body `Nomad Enterprise only endpoint` |
| `PUT /v1/operator/license` | 405 `Invalid method` on both editions in 2.0.5; licences are server configuration |
