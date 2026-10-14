"""Recommendations are Enterprise (Dynamic Application Sizing)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .models import Model

if TYPE_CHECKING:
    from .api import Client, QueryMeta, QueryOptions, WriteMeta, WriteOptions


@dataclass
class Recommendation(Model):
    id: str = field(default="", metadata={"json": "ID"})
    region: str = ""
    namespace: str = ""
    job_id: str = field(default="", metadata={"json": "JobID"})
    job_version: int = 0
    group: str = ""
    task: str = ""
    resource: str = ""
    value: int = 0
    current: int = 0
    meta: dict[str, Any] | None = None
    stats: dict[str, float] | None = None
    enforce_version: bool = False
    submit_time: int = 0
    create_index: int = 0
    modify_index: int = 0


@dataclass
class SingleRecommendationApplyResult(Model):
    namespace: str = ""
    job_id: str = field(default="", metadata={"json": "JobID"})
    job_modify_index: int = 0
    eval_id: str = field(default="", metadata={"json": "EvalID"})
    eval_create_index: int = 0
    warnings: str = ""
    recommendations: list[str] | None = None


@dataclass
class SingleRecommendationApplyError(Model):
    namespace: str = ""
    job_id: str = field(default="", metadata={"json": "JobID"})
    recommendations: list[str] | None = None
    error: str = ""


@dataclass
class RecommendationApplyResponse(Model):
    updated_jobs: list[SingleRecommendationApplyResult] | None = None
    errors: list[SingleRecommendationApplyError] | None = None


class Recommendations:
    """Recommendations queries the recommendation endpoints (Enterprise)."""

    def __init__(self, client: Client):
        self._client = client

    def list(self, q: QueryOptions | None = None) -> tuple[list[Recommendation], QueryMeta]:
        resp, qm = self._client.query("/v1/recommendations", q)
        return [Recommendation.from_json(r) for r in resp], qm

    def info(self, id: str, q: QueryOptions | None = None) -> tuple[Recommendation, QueryMeta]:
        resp, qm = self._client.query("/v1/recommendation/" + quote(id, safe=""), q)
        return Recommendation.from_json(resp), qm

    def upsert(self, rec: Recommendation, w: WriteOptions | None = None) -> tuple[Recommendation, WriteMeta]:
        resp, wm = self._client.put("/v1/recommendation", rec.to_json(), w)
        return Recommendation.from_json(resp), wm

    def delete(self, ids: list[str], w: WriteOptions | None = None) -> WriteMeta:
        _, wm = self._client.put("/v1/recommendations/apply", {"Apply": [], "Dismiss": ids, "PolicyOverride": False}, w)
        return wm

    def apply(self, ids: list[str], policy_override: bool = False) -> tuple[RecommendationApplyResponse, WriteMeta]:
        resp, wm = self._client.put("/v1/recommendations/apply", {"Apply": ids, "Dismiss": None, "PolicyOverride": policy_override})
        return RecommendationApplyResponse.from_json(resp), wm
