from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math


@dataclass(frozen=True)
class SourceProfile:
    reliability: float
    authority: float
    allowed_kinds: frozenset[str]
    freshness_half_life_seconds: int
    max_age_seconds: int


SOURCE_PROFILES: dict[str, SourceProfile] = {
    "support_platform": SourceProfile(
        reliability=0.97,
        authority=0.90,
        allowed_kinds=frozenset({"ticket_content"}),
        freshness_half_life_seconds=7 * 24 * 3600,
        max_age_seconds=30 * 24 * 3600,
    ),
    "crm_note": SourceProfile(
        reliability=0.80,
        authority=0.55,
        allowed_kinds=frozenset({"ticket_content", "order_record"}),
        freshness_half_life_seconds=7 * 24 * 3600,
        max_age_seconds=90 * 24 * 3600,
    ),
    "payments_ledger": SourceProfile(
        reliability=0.995,
        authority=1.00,
        allowed_kinds=frozenset({"payment_ledger"}),
        freshness_half_life_seconds=90 * 24 * 3600,
        max_age_seconds=365 * 24 * 3600,
    ),
    "orders_service": SourceProfile(
        reliability=0.99,
        authority=0.95,
        allowed_kinds=frozenset({"order_record"}),
        freshness_half_life_seconds=30 * 24 * 3600,
        max_age_seconds=180 * 24 * 3600,
    ),
    "ci_pipeline": SourceProfile(
        reliability=0.995,
        authority=1.00,
        allowed_kinds=frozenset({"ci_results"}),
        freshness_half_life_seconds=12 * 3600,
        max_age_seconds=7 * 24 * 3600,
    ),
    "deployment_service": SourceProfile(
        reliability=0.995,
        authority=0.98,
        allowed_kinds=frozenset({"deployment_manifest", "release_metadata"}),
        freshness_half_life_seconds=7 * 24 * 3600,
        max_age_seconds=30 * 24 * 3600,
    ),
    "incident_service": SourceProfile(
        reliability=0.99,
        authority=0.95,
        allowed_kinds=frozenset({"incident_status"}),
        freshness_half_life_seconds=3600,
        max_age_seconds=24 * 3600,
    ),
    "risk_service": SourceProfile(
        reliability=0.97,
        authority=0.90,
        allowed_kinds=frozenset({"risk_record"}),
        freshness_half_life_seconds=12 * 3600,
        max_age_seconds=7 * 24 * 3600,
    ),
}


def source_profile(source: str, kind: str) -> SourceProfile | None:
    profile = SOURCE_PROFILES.get(source)
    if profile is None or kind not in profile.allowed_kinds:
        return None
    return profile


def freshness_score(observed_at: datetime, profile: SourceProfile) -> float:
    now = datetime.now(timezone.utc)
    value = observed_at if observed_at.tzinfo else observed_at.replace(tzinfo=timezone.utc)
    age_seconds = max(0.0, (now - value.astimezone(timezone.utc)).total_seconds())
    if age_seconds > profile.max_age_seconds:
        return 0.0
    score = math.pow(0.5, age_seconds / profile.freshness_half_life_seconds)
    return round(max(0.0, min(1.0, score)), 4)
