from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClaimValueResult:
    valid: bool
    value: Any = None
    rejection_reason: str | None = None


BOOLEAN_CLAIMS = frozenset(
    {
        "safety_related",
        "vip_customer",
        "payment_settled",
        "duplicate_charge",
        "chargeback_open",
        "order_exists",
        "rollback_available",
        "database_migration",
        "backup_available",
        "incident_active",
        "approved_hotfix",
        "legal_hold",
    }
)

ENUM_CLAIMS: dict[str, frozenset[str]] = {
    "ci_status": frozenset({"passed", "failed", "running", "pending"}),
    "change_risk": frozenset({"low", "medium", "high", "critical"}),
    "customer_risk": frozenset({"low", "medium", "high"}),
}

TEXT_CLAIMS = frozenset({"ticket_topic", "target_environment"})


def validate_claim_value(claim: str, value: Any) -> ClaimValueResult:
    if claim in BOOLEAN_CLAIMS:
        if type(value) is not bool:
            return ClaimValueResult(False, rejection_reason="INVALID_BOOLEAN_CLAIM_VALUE")
        return ClaimValueResult(True, value=value)

    allowed = ENUM_CLAIMS.get(claim)
    if allowed is not None:
        if not isinstance(value, str):
            return ClaimValueResult(False, rejection_reason="INVALID_ENUM_CLAIM_VALUE")
        normalized = value.strip().lower()
        if normalized not in allowed:
            return ClaimValueResult(False, rejection_reason="INVALID_ENUM_CLAIM_VALUE")
        return ClaimValueResult(True, value=normalized)

    if claim in TEXT_CLAIMS:
        if not isinstance(value, str):
            return ClaimValueResult(False, rejection_reason="INVALID_TEXT_CLAIM_VALUE")
        normalized = value.strip().lower()
        if not normalized or len(normalized) > 120:
            return ClaimValueResult(False, rejection_reason="INVALID_TEXT_CLAIM_VALUE")
        return ClaimValueResult(True, value=normalized)

    return ClaimValueResult(False, rejection_reason="UNRECOGNIZED_CLAIM_CONTRACT")
