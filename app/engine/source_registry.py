from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math


@dataclass(frozen=True)
class SourceProfile:
    reliability: float
    authority: float
    allowed_pairs: frozenset[tuple[str, str]]
    freshness_half_life_seconds: int
    max_age_seconds: int


SOURCE_PROFILES: dict[str, SourceProfile] = {
    "support_platform": SourceProfile(
        reliability=0.97,
        authority=0.90,
        allowed_pairs=frozenset(
            {
                ("ticket_content", "ticket_topic"),
                ("ticket_content", "safety_related"),
                ("ticket_content", "vip_customer"),
            }
        ),
        freshness_half_life_seconds=7 * 24 * 3600,
        max_age_seconds=30 * 24 * 3600,
    ),
    "crm_note": SourceProfile(
        reliability=0.80,
        authority=0.55,
        allowed_pairs=frozenset(
            {
                ("ticket_content", "ticket_topic"),
                ("order_record", "duplicate_charge"),
            }
        ),
        freshness_half_life_seconds=7 * 24 * 3600,
        max_age_seconds=90 * 24 * 3600,
    ),
    "payments_ledger": SourceProfile(
        reliability=0.995,
        authority=1.00,
        allowed_pairs=frozenset(
            {
                ("payment_ledger", "payment_settled"),
                ("payment_ledger", "duplicate_charge"),
                ("payment_ledger", "chargeback_open"),
            }
        ),
        freshness_half_life_seconds=90 * 24 * 3600,
        max_age_seconds=365 * 24 * 3600,
    ),
    "orders_service": SourceProfile(
        reliability=0.99,
        authority=0.95,
        allowed_pairs=frozenset({("order_record", "order_exists")}),
        freshness_half_life_seconds=30 * 24 * 3600,
        max_age_seconds=180 * 24 * 3600,
    ),
    "ci_pipeline": SourceProfile(
        reliability=0.995,
        authority=1.00,
        allowed_pairs=frozenset({("ci_results", "ci_status")}),
        freshness_half_life_seconds=12 * 3600,
        max_age_seconds=7 * 24 * 3600,
    ),
    "deployment_service": SourceProfile(
        reliability=0.995,
        authority=0.98,
        allowed_pairs=frozenset(
            {
                ("deployment_manifest", "target_environment"),
                ("deployment_manifest", "rollback_available"),
                ("release_metadata", "change_risk"),
                ("release_metadata", "database_migration"),
                ("release_metadata", "backup_available"),
            }
        ),
        freshness_half_life_seconds=7 * 24 * 3600,
        max_age_seconds=30 * 24 * 3600,
    ),
    "incident_service": SourceProfile(
        reliability=0.99,
        authority=0.95,
        allowed_pairs=frozenset(
            {
                ("incident_status", "incident_active"),
                ("incident_status", "approved_hotfix"),
            }
        ),
        freshness_half_life_seconds=3600,
        max_age_seconds=24 * 3600,
    ),
    "risk_service": SourceProfile(
        reliability=0.97,
        authority=0.90,
        allowed_pairs=frozenset(
            {
                ("risk_record", "customer_risk"),
                ("risk_record", "legal_hold"),
            }
        ),
        freshness_half_life_seconds=12 * 3600,
        max_age_seconds=7 * 24 * 3600,
    ),
}


def source_profile(source: str, kind: str, claim: str) -> SourceProfile | None:
    profile = SOURCE_PROFILES.get(source)
    if profile is None or (kind, claim) not in profile.allowed_pairs:
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
