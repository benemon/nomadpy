import pytest

from nomadpy import (
    ACLAuthMethod,
    ACLAuthMethodConfig,
    ACLBindingRule,
    ACLPolicy,
    ACLRole,
    ACLRolePolicyLink,
    ACLToken,
    ACLTokenRoleLink,
    Client,
    Config,
    QueryOptions,
    UnexpectedResponseError,
)
from nomadpy.acl import ACL_AUTH_METHOD_TYPE_JWT, ACL_BINDING_RULE_BIND_TYPE_POLICY
from nomadpy.models import format_duration, parse_duration

READ_DEFAULT = 'namespace "default" { policy = "read" }'
HOUR = 3_600_000_000_000


def test_bootstrap_once(acl_client):
    me, _ = acl_client.acl_tokens.self()
    assert me.type == "management"
    assert me.secret_id == acl_client.config.secret_id
    with pytest.raises(UnexpectedResponseError) as e:
        acl_client.acl_tokens.bootstrap()
    assert e.value.status_code == 400
    assert "already" in e.value.body


def test_anonymous_is_denied(acl_agent):
    with pytest.raises(UnexpectedResponseError) as e:
        Client(Config(address=acl_agent)).acl_tokens.list()
    assert e.value.status_code == 403


def test_policies(acl_client):
    wm = acl_client.acl_policies.upsert(ACLPolicy(name="nomadpy-read", description="d", rules=READ_DEFAULT))
    assert wm.last_index > 0
    policy, qm = acl_client.acl_policies.info("nomadpy-read")
    assert policy.rules == READ_DEFAULT and policy.description == "d"
    assert policy.job_acl is None and policy.create_index > 0
    stubs, _ = acl_client.acl_policies.list()
    assert [s.name for s in stubs if s.name == "nomadpy-read"] == ["nomadpy-read"]

    token, _ = acl_client.acl_tokens.create(ACLToken(name="nomadpy-self", type="client", policies=["nomadpy-read"]))
    mine, _ = acl_client.acl_policies.self(QueryOptions(auth_token=token.secret_id))
    assert [s.name for s in mine] == ["nomadpy-read"]

    acl_client.acl_tokens.delete(token.accessor_id)
    acl_client.acl_policies.delete("nomadpy-read")
    with pytest.raises(UnexpectedResponseError) as e:
        acl_client.acl_policies.info("nomadpy-read")
    assert e.value.status_code == 404
    with pytest.raises(ValueError):
        acl_client.acl_policies.upsert(ACLPolicy(rules=READ_DEFAULT))


def test_tokens(acl_client):
    acl_client.acl_policies.upsert(ACLPolicy(name="nomadpy-tok", rules=READ_DEFAULT))
    token, wm = acl_client.acl_tokens.create(ACLToken(name="nomadpy-t1", type="client", policies=["nomadpy-tok"], expiration_ttl=HOUR))
    assert token.accessor_id and token.secret_id and wm.last_index > 0
    assert token.expiration_time is not None
    assert token.expiration_ttl == HOUR

    info, _ = acl_client.acl_tokens.info(token.accessor_id)
    assert info.name == "nomadpy-t1" and info.policies == ["nomadpy-tok"]
    stubs, _ = acl_client.acl_tokens.list()
    assert token.accessor_id in [s.accessor_id for s in stubs]

    me, _ = acl_client.acl_tokens.self(QueryOptions(auth_token=token.secret_id))
    assert me.accessor_id == token.accessor_id

    info.name = "nomadpy-t1-renamed"
    updated, _ = acl_client.acl_tokens.update(info)
    assert updated.name == "nomadpy-t1-renamed"

    acl_client.acl_tokens.delete(token.accessor_id)
    with pytest.raises(UnexpectedResponseError) as e:
        acl_client.acl_tokens.info(token.accessor_id)
    assert e.value.status_code == 404

    with pytest.raises(ValueError):
        acl_client.acl_tokens.create(ACLToken(accessor_id="x"))
    with pytest.raises(ValueError):
        acl_client.acl_tokens.upload(ACLToken(accessor_id="x", secret_id="y", type="management"))
    with pytest.raises(ValueError):
        acl_client.acl_tokens.update(ACLToken(name="no-accessor"))
    acl_client.acl_policies.delete("nomadpy-tok")


def test_upload_token(acl_client):
    acl_client.acl_policies.upsert(ACLPolicy(name="nomadpy-up", rules=READ_DEFAULT))
    fixed = ACLToken(accessor_id="0e1d2c3b-4a59-4687-9f6e-5d4c3b2a1f00", secret_id="f0e1d2c3-b4a5-4968-87f6-e5d4c3b2a1f0",
                     name="nomadpy-uploaded", type="client", policies=["nomadpy-up"])
    token, _ = acl_client.acl_tokens.upload(fixed)
    assert token.accessor_id == fixed.accessor_id and token.secret_id == fixed.secret_id
    acl_client.acl_tokens.delete(fixed.accessor_id)
    acl_client.acl_policies.delete("nomadpy-up")


def test_one_time_token(acl_client):
    ott, wm = acl_client.acl_tokens.upsert_one_time_token()
    assert ott.one_time_secret_id and ott.expires_at and wm.last_index > 0
    me, _ = acl_client.acl_tokens.self()
    assert ott.accessor_id == me.accessor_id
    anonymous = Client(Config(address=acl_client.config.address))
    token, _ = anonymous.acl_tokens.exchange_one_time_token(ott.one_time_secret_id)
    assert token.accessor_id == me.accessor_id
    with pytest.raises(ValueError):
        anonymous.acl_tokens.exchange_one_time_token("")


def test_roles(acl_client):
    acl_client.acl_policies.upsert(ACLPolicy(name="nomadpy-role-p", rules=READ_DEFAULT))
    role, wm = acl_client.acl_roles.create(ACLRole(name="nomadpy-role", description="d", policies=[ACLRolePolicyLink(name="nomadpy-role-p")]))
    assert role.id and wm.last_index > 0
    assert [p.name for p in role.policies] == ["nomadpy-role-p"]

    by_id, _ = acl_client.acl_roles.get(role.id)
    by_name, _ = acl_client.acl_roles.get_by_name("nomadpy-role")
    assert by_id == by_name
    stubs, _ = acl_client.acl_roles.list()
    assert role.id in [s.id for s in stubs]

    token, _ = acl_client.acl_tokens.create(ACLToken(name="nomadpy-role-t", type="client", roles=[ACLTokenRoleLink(id=role.id)]))
    assert token.roles[0].name == "nomadpy-role"
    mine, _ = acl_client.acl_policies.self(QueryOptions(auth_token=token.secret_id))
    assert [s.name for s in mine] == ["nomadpy-role-p"]
    acl_client.acl_tokens.delete(token.accessor_id)

    role.description = "updated"
    updated, _ = acl_client.acl_roles.update(role)
    assert updated.description == "updated"
    acl_client.acl_roles.delete(role.id)
    with pytest.raises(UnexpectedResponseError):
        acl_client.acl_roles.get(role.id)
    with pytest.raises(ValueError):
        acl_client.acl_roles.create(ACLRole(id="x"))
    with pytest.raises(ValueError):
        acl_client.acl_roles.update(ACLRole(name="x"))
    acl_client.acl_policies.delete("nomadpy-role-p")


def test_auth_methods_and_binding_rules(acl_client):
    method = ACLAuthMethod(
        name="nomadpy-jwt", type=ACL_AUTH_METHOD_TYPE_JWT, token_locality="global", max_token_ttl=HOUR, default=True,
        config=ACLAuthMethodConfig(jwks_url="https://idp.example/.well-known/jwks.json", bound_audiences=["nomad"],
                                   claim_mappings={"sub": "user"}, expiration_leeway=90_000_000_000, clock_skew_leeway=1_500_000_000))
    created, wm = acl_client.acl_auth_methods.create(method)
    assert created.name == "nomadpy-jwt" and wm.last_index > 0
    assert created.max_token_ttl == HOUR
    assert created.config.expiration_leeway == 90_000_000_000
    assert created.config.clock_skew_leeway == 1_500_000_000
    assert created.config.not_before_leeway == 0

    got, _ = acl_client.acl_auth_methods.get("nomadpy-jwt")
    assert got.config.bound_audiences == ["nomad"] and got.config.claim_mappings == {"sub": "user"}
    stubs, _ = acl_client.acl_auth_methods.list()
    assert [s.default for s in stubs if s.name == "nomadpy-jwt"] == [True]

    rule, _ = acl_client.acl_binding_rules.create(ACLBindingRule(
        description="d", auth_method="nomadpy-jwt", selector='value.user == "a"', bind_type=ACL_BINDING_RULE_BIND_TYPE_POLICY, bind_name="nomadpy-bound"))
    assert rule.id
    got_rule, _ = acl_client.acl_binding_rules.get(rule.id)
    assert got_rule.selector == 'value.user == "a"'
    rules, _ = acl_client.acl_binding_rules.list()
    assert rule.id in [r.id for r in rules]
    rule.description = "updated"
    updated_rule, _ = acl_client.acl_binding_rules.update(rule)
    assert updated_rule.description == "updated"

    with pytest.raises(UnexpectedResponseError) as e:
        acl_client.acl_auth.login("nomadpy-jwt", "not-a-jwt")
    assert e.value.status_code in (400, 401, 403, 500)
    with pytest.raises(UnexpectedResponseError):
        acl_client.acl_auth.get_auth_url("nomadpy-jwt", "http://127.0.0.1/cb", "nonce")

    acl_client.acl_binding_rules.delete(rule.id)
    got.description = "x"
    got.max_token_ttl = 2 * HOUR
    updated, _ = acl_client.acl_auth_methods.update(got)
    assert updated.max_token_ttl == 2 * HOUR
    acl_client.acl_auth_methods.delete("nomadpy-jwt")
    with pytest.raises(UnexpectedResponseError):
        acl_client.acl_auth_methods.get("nomadpy-jwt")
    with pytest.raises(ValueError):
        acl_client.acl_auth_methods.create(ACLAuthMethod(type="JWT"))
    with pytest.raises(ValueError):
        acl_client.acl_binding_rules.update(ACLBindingRule(auth_method="m"))


def test_client_introduction_token(acl_client):
    resp, wm = acl_client.acl_identity.create_client_introduction_token(ttl=300_000_000_000, node_name="n1", node_pool="default")
    assert resp.jwt.count(".") == 2 and wm.last_index >= 0


@pytest.mark.parametrize("ns,text", [
    (0, "0s"), (1, "1ns"), (1_500, "1.5µs"), (500_000_000, "500ms"), (1_000_000_000, "1s"), (1_500_000_000, "1.5s"),
    (90_000_000_000, "1m30s"), (HOUR, "1h0m0s"), (HOUR + 1_000_000, "1h0m0.001s"), (-HOUR, "-1h0m0s"),
])
def test_format_duration_matches_go(ns, text):
    assert format_duration(ns) == text
    assert parse_duration(text) == ns


@pytest.mark.parametrize("text,ns", [("1h30m", 5_400_000_000_000), ("1.5h", 5_400_000_000_000), ("300ms", 300_000_000), ("0", 0), ("2us", 2_000)])
def test_parse_duration(text, ns):
    assert parse_duration(text) == ns


def test_parse_duration_rejects_garbage():
    with pytest.raises(ValueError):
        parse_duration("1 hour")
