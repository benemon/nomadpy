# Configuration

`Client()` with no argument calls [default_config][nomadpy.api.default_config],
which starts from `http://127.0.0.1:4646` and reads the environment. A
[Config][nomadpy.api.Config] passed in is used as given; an empty `address`
falls back to `NOMAD_ADDR`, then to the default.

```python
from datetime import timedelta
from nomadpy import Client, Config, TLSConfig

config = Config(
    address="https://nomad.example.com:4646",
    namespace="platform",
    secret_id="...",
    wait_time=timedelta(minutes=1),
    tls_config=TLSConfig(ca_cert="/etc/nomad/ca.pem"),
)
client = Client(config)
```

## Environment variables

The variables are the ones the Nomad CLI reads, with the same meaning; the
[CLI documentation](https://developer.hashicorp.com/nomad/commands#environment-variables)
describes each. The table gives the `Config` field each one sets.

| Variable | Field |
|---|---|
| `NOMAD_ADDR` | `address` |
| `NOMAD_REGION` | `region` |
| `NOMAD_NAMESPACE` | `namespace` |
| `NOMAD_TOKEN` | `secret_id` |
| `NOMAD_HTTP_AUTH` | `http_auth`, split at the first `:` into username and password |
| `NOMAD_CACERT` | `tls_config.ca_cert` |
| `NOMAD_CAPATH` | `tls_config.ca_path` |
| `NOMAD_CLIENT_CERT` | `tls_config.client_cert` |
| `NOMAD_CLIENT_KEY` | `tls_config.client_key` |
| `NOMAD_TLS_SERVER_NAME` | `tls_config.tls_server_name` |
| `NOMAD_SKIP_VERIFY` | `tls_config.insecure` |

`NOMAD_SKIP_VERIFY` accepts the spellings Go's `strconv.ParseBool` accepts
(`1`, `t`, `T`, `TRUE`, `true`, `True` and their false counterparts) and
ignores any other value.

## Config fields

| Field | Effect |
|---|---|
| `address` | Scheme, host and port of every request. `http` and `https` only. Userinfo in the URL (`https://user:pass@host`) is sent as HTTP basic authentication and never echoed in errors. |
| `region` | `region` query parameter on every request unless the request's options set one. |
| `namespace` | `namespace` query parameter on every request unless the request's options set one. |
| `secret_id` | `X-Nomad-Token` header unless the request's options set `auth_token`. |
| `http_auth` | `Authorization: Basic` header, when the address carries no userinfo. |
| `wait_time` | `wait` query parameter on every request, as milliseconds. |
| `tls_config` | See below. |
| `headers` | Sent on every request; the request's options may add to them. |

`set_region`, `set_namespace` and `set_secret_id` change the client's
config in place.

## TLS

`tls_config` builds the `ssl.SSLContext` for `https` addresses. `ca_cert`
and `ca_path` are passed to `ssl.create_default_context`. `client_cert` and
`client_key` must be given together; one without the other raises
`ValueError`. `tls_server_name` verifies the server certificate against
that name instead of the URL host, as Go's `tls.Config.ServerName` does.
`insecure` disables hostname checking and certificate verification.
