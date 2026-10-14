from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions

OIDC_KEY_SOURCE_NOMAD = "nomad"
OIDC_KEY_SOURCE_PRIVATE_KEY = "private_key"
OIDC_KEY_SOURCE_CLIENT_SECRET = "client_secret"

OIDC_CLIENT_ASSERTION_HEADER_KID = "kid"
OIDC_CLIENT_ASSERTION_HEADER_X5T = "x5t"
OIDC_CLIENT_ASSERTION_HEADER_X5T_S256 = "x5t#S256"

ACL_AUTH_METHOD_TOKEN_LOCALITY_LOCAL = "local"
ACL_AUTH_METHOD_TOKEN_LOCALITY_GLOBAL = "global"
ACL_AUTH_METHOD_TYPE_OIDC = "OIDC"
ACL_AUTH_METHOD_TYPE_JWT = "JWT"

ACL_BINDING_RULE_BIND_TYPE_ROLE = "role"
ACL_BINDING_RULE_BIND_TYPE_POLICY = "policy"
ACL_BINDING_RULE_BIND_TYPE_MANAGEMENT = "management"


@dataclass
class JobACL(Model):
    namespace: str = ""
    job_id: str = field(default="", metadata={"json": "JobID"})
    group: str = ""
    task: str = ""


@dataclass
class ACLPolicyListStub(Model):
    name: str = ""
    description: str = ""
    job_acl: JobACL | None = field(default=None, metadata={"json": "JobACL"})
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ACLPolicy(Model):
    name: str = ""
    description: str = ""
    rules: str = ""
    job_acl: JobACL | None = field(default=None, metadata={"json": "JobACL"})
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ACLTokenRoleLink(Model):
    id: str = field(default="", metadata={"json": "ID"})
    name: str = ""


@dataclass
class ACLToken(Model):
    accessor_id: str = field(default="", metadata={"json": "AccessorID"})
    secret_id: str = field(default="", metadata={"json": "SecretID"})
    name: str = ""
    type: str = ""
    policies: list[str] | None = None
    roles: list[ACLTokenRoleLink] | None = None
    global_: bool = field(default=False, metadata={"json": "Global"})
    create_time: str = field(default="", metadata={"time": True})
    expiration_time: str | None = field(default=None, metadata={"omitempty": True, "time": True})
    expiration_ttl: int = field(default=0, metadata={"json": "ExpirationTTL", "duration": "string", "omitempty": True})
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ACLTokenListStub(Model):
    accessor_id: str = field(default="", metadata={"json": "AccessorID"})
    name: str = ""
    type: str = ""
    policies: list[str] | None = None
    roles: list[ACLTokenRoleLink] | None = None
    global_: bool = field(default=False, metadata={"json": "Global"})
    create_time: str = field(default="", metadata={"time": True})
    expiration_time: str | None = field(default=None, metadata={"omitempty": True, "time": True})
    create_index: int = 0
    modify_index: int = 0


@dataclass
class OneTimeToken(Model):
    one_time_secret_id: str = field(default="", metadata={"json": "OneTimeSecretID"})
    accessor_id: str = field(default="", metadata={"json": "AccessorID"})
    expires_at: str = field(default="", metadata={"time": True})
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ACLRolePolicyLink(Model):
    name: str = ""


@dataclass
class ACLRole(Model):
    id: str = field(default="", metadata={"json": "ID"})
    name: str = ""
    description: str = ""
    policies: list[ACLRolePolicyLink] | None = None
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ACLRoleListStub(Model):
    id: str = field(default="", metadata={"json": "ID"})
    name: str = ""
    description: str = ""
    policies: list[ACLRolePolicyLink] | None = None
    create_index: int = 0
    modify_index: int = 0


@dataclass
class OIDCClientAssertionKey(Model):
    pem_key: str = ""
    pem_key_file: str = ""
    key_id_header: str = field(default="", metadata={"json": "KeyIDHeader"})
    key_id: str = field(default="", metadata={"json": "KeyID"})
    pem_cert: str = ""
    pem_cert_file: str = ""


@dataclass
class OIDCClientAssertion(Model):
    audience: list[str] | None = None
    key_source: str = ""
    key_algorithm: str = ""
    private_key: OIDCClientAssertionKey | None = None
    extra_headers: dict[str, str] | None = None


@dataclass
class ACLAuthMethodConfig(Model):
    jwt_validation_pub_keys: list[str] | None = field(default=None, metadata={"json": "JWTValidationPubKeys"})
    jwks_url: str = field(default="", metadata={"json": "JWKSURL"})
    oidc_discovery_url: str = field(default="", metadata={"json": "OIDCDiscoveryURL"})
    oidc_client_id: str = field(default="", metadata={"json": "OIDCClientID"})
    oidc_client_secret: str = field(default="", metadata={"json": "OIDCClientSecret"})
    oidc_client_assertion: OIDCClientAssertion | None = field(default=None, metadata={"json": "OIDCClientAssertion"})
    oidc_enable_pkce: bool = field(default=False, metadata={"json": "OIDCEnablePKCE"})
    oidc_disable_user_info: bool = field(default=False, metadata={"json": "OIDCDisableUserInfo"})
    oidc_scopes: list[str] | None = field(default=None, metadata={"json": "OIDCScopes"})
    bound_audiences: list[str] | None = None
    bound_issuer: list[str] | None = None
    allowed_redirect_uris: list[str] | None = field(default=None, metadata={"json": "AllowedRedirectURIs"})
    discovery_ca_pem: list[str] | None = None
    jwks_ca_cert: str = field(default="", metadata={"json": "JWKSCACert"})
    signing_algs: list[str] | None = None
    expiration_leeway: int = field(default=0, metadata={"duration": "string"})
    not_before_leeway: int = field(default=0, metadata={"duration": "string"})
    clock_skew_leeway: int = field(default=0, metadata={"duration": "string"})
    claim_mappings: dict[str, str] | None = None
    list_claim_mappings: dict[str, str] | None = None
    verbose_logging: bool = False


@dataclass
class ACLAuthMethod(Model):
    name: str = ""
    type: str = ""
    token_locality: str = ""
    token_name_format: str = ""
    max_token_ttl: int = field(default=0, metadata={"json": "MaxTokenTTL", "duration": "string"})
    default: bool = False
    config: ACLAuthMethodConfig | None = None
    create_time: str = field(default="", metadata={"time": True})
    modify_time: str = field(default="", metadata={"time": True})
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ACLAuthMethodListStub(Model):
    name: str = ""
    type: str = ""
    default: bool = False
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ACLBindingRule(Model):
    id: str = field(default="", metadata={"json": "ID"})
    description: str = ""
    auth_method: str = ""
    selector: str = ""
    bind_type: str = ""
    bind_name: str = ""
    create_time: str = field(default="", metadata={"time": True})
    modify_time: str = field(default="", metadata={"time": True})
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ACLBindingRuleListStub(Model):
    id: str = field(default="", metadata={"json": "ID"})
    description: str = ""
    auth_method: str = ""
    create_index: int = 0
    modify_index: int = 0


@dataclass
class ACLOIDCAuthURLResponse(Model):
    auth_url: str = field(default="", metadata={"json": "AuthURL"})


@dataclass
class ACLIdentityClientIntroductionTokenResponse(Model):
    jwt: str = field(default="", metadata={"json": "JWT"})


class ACLPolicies:
    """ACLPolicies queries the ACL policy endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[ACLPolicyListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/acl/policies", q)
        return [ACLPolicyListStub.from_json(p) for p in resp], qm

    def upsert(self, policy: ACLPolicy, w: WriteOptions | None = None) -> WriteMeta:
        if not policy.name:
            raise ValueError("missing policy name")
        _, wm = self._client.put(f"/v1/acl/policy/{quote(policy.name, safe='')}", policy.to_json(), w)
        return wm

    def delete(self, policy_name: str, w: WriteOptions | None = None) -> WriteMeta:
        if not policy_name:
            raise ValueError("missing policy name")
        _, wm = self._client.delete(f"/v1/acl/policy/{quote(policy_name, safe='')}", None, w)
        return wm

    def info(self, policy_name: str, q: QueryOptions | None = None) -> tuple[ACLPolicy, QueryMeta]:
        if not policy_name:
            raise ValueError("missing policy name")
        resp, qm = self._client.query(f"/v1/acl/policy/{quote(policy_name, safe='')}", q)
        return ACLPolicy.from_json(resp), qm

    def self(self, q: QueryOptions | None = None) -> tuple[list[ACLPolicyListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/acl/policy/self", q)
        return [ACLPolicyListStub.from_json(p) for p in resp], qm


class ACLTokens:
    """ACLTokens queries the ACL token endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def bootstrap(self, w: WriteOptions | None = None, *, bootstrap_secret: str = "") -> tuple[ACLToken, WriteMeta]:
        body = {"BootstrapSecret": bootstrap_secret} if bootstrap_secret else None
        resp, wm = self._client.put("/v1/acl/bootstrap", body, w)
        return ACLToken.from_json(resp), wm

    def list(self, q: QueryOptions | None = None) -> tuple[list[ACLTokenListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/acl/tokens", q)
        return [ACLTokenListStub.from_json(t) for t in resp], qm

    def create(self, token: ACLToken, w: WriteOptions | None = None) -> tuple[ACLToken, WriteMeta]:
        if token.accessor_id:
            raise ValueError("cannot specify Accessor ID")
        resp, wm = self._client.put("/v1/acl/token", token.to_json(), w)
        return ACLToken.from_json(resp), wm

    def upload(self, token: ACLToken, w: WriteOptions | None = None) -> tuple[ACLToken, WriteMeta]:
        if not token.accessor_id:
            raise ValueError("missing Accessor ID")
        if not token.secret_id:
            raise ValueError("missing Secret ID")
        if token.type == "management":
            raise ValueError("cannot upload a management token")
        resp, wm = self._client.put(f"/v1/acl/token/{quote(token.accessor_id, safe='')}", token.to_json(), w)
        return ACLToken.from_json(resp), wm

    def update(self, token: ACLToken, w: WriteOptions | None = None) -> tuple[ACLToken, WriteMeta]:
        if not token.accessor_id:
            raise ValueError("missing Accessor ID")
        resp, wm = self._client.put(f"/v1/acl/token/{quote(token.accessor_id, safe='')}", token.to_json(), w)
        return ACLToken.from_json(resp), wm

    def delete(self, accessor_id: str, w: WriteOptions | None = None) -> WriteMeta:
        if not accessor_id:
            raise ValueError("missing accessor ID")
        _, wm = self._client.delete(f"/v1/acl/token/{quote(accessor_id, safe='')}", None, w)
        return wm

    def info(self, accessor_id: str, q: QueryOptions | None = None) -> tuple[ACLToken, QueryMeta]:
        if not accessor_id:
            raise ValueError("missing accessor ID")
        resp, qm = self._client.query(f"/v1/acl/token/{quote(accessor_id, safe='')}", q)
        return ACLToken.from_json(resp), qm

    def self(self, q: QueryOptions | None = None) -> tuple[ACLToken, QueryMeta]:
        resp, qm = self._client.query("/v1/acl/token/self", q)
        return ACLToken.from_json(resp), qm

    def upsert_one_time_token(self, w: WriteOptions | None = None) -> tuple[OneTimeToken, WriteMeta]:
        resp, wm = self._client.put("/v1/acl/token/onetime", None, w)
        return OneTimeToken.from_json(resp["OneTimeToken"]), wm

    def exchange_one_time_token(self, secret: str, w: WriteOptions | None = None) -> tuple[ACLToken, WriteMeta]:
        if not secret:
            raise ValueError("missing secret ID")
        resp, wm = self._client.put("/v1/acl/token/onetime/exchange", {"OneTimeSecretID": secret}, w)
        return ACLToken.from_json(resp["Token"]), wm


class ACLRoles:
    """ACLRoles queries the ACL role endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[ACLRoleListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/acl/roles", q)
        return [ACLRoleListStub.from_json(r) for r in resp], qm

    def create(self, role: ACLRole, w: WriteOptions | None = None) -> tuple[ACLRole, WriteMeta]:
        if role.id:
            raise ValueError("cannot specify ACL role ID")
        resp, wm = self._client.put("/v1/acl/role", role.to_json(), w)
        return ACLRole.from_json(resp), wm

    def update(self, role: ACLRole, w: WriteOptions | None = None) -> tuple[ACLRole, WriteMeta]:
        if not role.id:
            raise ValueError("missing ACL role ID")
        resp, wm = self._client.put(f"/v1/acl/role/{quote(role.id, safe='')}", role.to_json(), w)
        return ACLRole.from_json(resp), wm

    def delete(self, role_id: str, w: WriteOptions | None = None) -> WriteMeta:
        if not role_id:
            raise ValueError("missing ACL role ID")
        _, wm = self._client.delete(f"/v1/acl/role/{quote(role_id, safe='')}", None, w)
        return wm

    def get(self, role_id: str, q: QueryOptions | None = None) -> tuple[ACLRole, QueryMeta]:
        if not role_id:
            raise ValueError("missing ACL role ID")
        resp, qm = self._client.query(f"/v1/acl/role/{quote(role_id, safe='')}", q)
        return ACLRole.from_json(resp), qm

    def get_by_name(self, role_name: str, q: QueryOptions | None = None) -> tuple[ACLRole, QueryMeta]:
        if not role_name:
            raise ValueError("missing ACL role name")
        resp, qm = self._client.query(f"/v1/acl/role/name/{quote(role_name, safe='')}", q)
        return ACLRole.from_json(resp), qm


class ACLAuthMethods:
    """ACLAuthMethods queries the ACL auth method endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[ACLAuthMethodListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/acl/auth-methods", q)
        return [ACLAuthMethodListStub.from_json(m) for m in resp], qm

    def create(self, auth_method: ACLAuthMethod, w: WriteOptions | None = None) -> tuple[ACLAuthMethod, WriteMeta]:
        if not auth_method.name:
            raise ValueError("missing ACL auth-method name")
        resp, wm = self._client.put("/v1/acl/auth-method", auth_method.to_json(), w)
        return ACLAuthMethod.from_json(resp), wm

    def update(self, auth_method: ACLAuthMethod, w: WriteOptions | None = None) -> tuple[ACLAuthMethod, WriteMeta]:
        if not auth_method.name:
            raise ValueError("missing ACL auth-method name")
        resp, wm = self._client.put(f"/v1/acl/auth-method/{quote(auth_method.name, safe='')}", auth_method.to_json(), w)
        return ACLAuthMethod.from_json(resp), wm

    def delete(self, auth_method_name: str, w: WriteOptions | None = None) -> WriteMeta:
        if not auth_method_name:
            raise ValueError("missing ACL auth-method name")
        _, wm = self._client.delete(f"/v1/acl/auth-method/{quote(auth_method_name, safe='')}", None, w)
        return wm

    def get(self, auth_method_name: str, q: QueryOptions | None = None) -> tuple[ACLAuthMethod, QueryMeta]:
        if not auth_method_name:
            raise ValueError("missing ACL auth-method name")
        resp, qm = self._client.query(f"/v1/acl/auth-method/{quote(auth_method_name, safe='')}", q)
        return ACLAuthMethod.from_json(resp), qm


class ACLBindingRules:
    """ACLBindingRules queries the ACL binding rule endpoints."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[ACLBindingRuleListStub], QueryMeta]:
        resp, qm = self._client.query("/v1/acl/binding-rules", q)
        return [ACLBindingRuleListStub.from_json(r) for r in resp], qm

    def create(self, binding_rule: ACLBindingRule, w: WriteOptions | None = None) -> tuple[ACLBindingRule, WriteMeta]:
        resp, wm = self._client.put("/v1/acl/binding-rule", binding_rule.to_json(), w)
        return ACLBindingRule.from_json(resp), wm

    def update(self, binding_rule: ACLBindingRule, w: WriteOptions | None = None) -> tuple[ACLBindingRule, WriteMeta]:
        if not binding_rule.id:
            raise ValueError("missing ACL binding rule ID")
        resp, wm = self._client.put(f"/v1/acl/binding-rule/{quote(binding_rule.id, safe='')}", binding_rule.to_json(), w)
        return ACLBindingRule.from_json(resp), wm

    def delete(self, binding_rule_id: str, w: WriteOptions | None = None) -> WriteMeta:
        if not binding_rule_id:
            raise ValueError("missing ACL binding rule ID")
        _, wm = self._client.delete(f"/v1/acl/binding-rule/{quote(binding_rule_id, safe='')}", None, w)
        return wm

    def get(self, binding_rule_id: str, q: QueryOptions | None = None) -> tuple[ACLBindingRule, QueryMeta]:
        if not binding_rule_id:
            raise ValueError("missing ACL binding rule ID")
        resp, qm = self._client.query(f"/v1/acl/binding-rule/{quote(binding_rule_id, safe='')}", q)
        return ACLBindingRule.from_json(resp), qm


class ACLAuth:
    """ACLAuth logs in through ACL auth methods."""

    def __init__(self, client: Client):
        self._client = client

    def get_auth_url(self, auth_method_name: str, redirect_uri: str, client_nonce: str,
                     w: WriteOptions | None = None) -> tuple[ACLOIDCAuthURLResponse, WriteMeta]:
        req = {"AuthMethodName": auth_method_name, "RedirectURI": redirect_uri, "ClientNonce": client_nonce}
        resp, wm = self._client.put("/v1/acl/oidc/auth-url", req, w)
        return ACLOIDCAuthURLResponse.from_json(resp), wm

    def complete_auth(self, auth_method_name: str, client_nonce: str, state: str, code: str, iss: str = "",
                      redirect_uri: str = "", w: WriteOptions | None = None) -> tuple[ACLToken, WriteMeta]:
        req = {"AuthMethodName": auth_method_name, "ClientNonce": client_nonce, "State": state, "Code": code,
               "Iss": iss, "RedirectURI": redirect_uri}
        resp, wm = self._client.put("/v1/acl/oidc/complete-auth", req, w)
        return ACLToken.from_json(resp), wm

    def login(self, auth_method_name: str, login_token: str, w: WriteOptions | None = None) -> tuple[ACLToken, WriteMeta]:
        req = {"AuthMethodName": auth_method_name, "LoginToken": login_token}
        resp, wm = self._client.put("/v1/acl/login", req, w)
        return ACLToken.from_json(resp), wm


class ACLIdentity:
    """ACLIdentity mints identity tokens."""

    def __init__(self, client: Client):
        self._client = client

    def create_client_introduction_token(self, ttl: int = 0, node_name: str = "", node_pool: str = "",
                                         w: WriteOptions | None = None) -> tuple[ACLIdentityClientIntroductionTokenResponse, WriteMeta]:
        """create_client_introduction_token mints a client introduction JWT; ttl is nanoseconds."""
        req: dict[str, Any] = {"TTL": ttl, "NodeName": node_name, "NodePool": node_pool}
        resp, wm = self._client.put("/v1/acl/identity/client-introduction-token", req, w)
        return ACLIdentityClientIntroductionTokenResponse.from_json(resp), wm
