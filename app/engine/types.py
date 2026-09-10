from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas import CostLevel


@dataclass(frozen=True)
class DomainAssessment:
    base_risk: float
    reversibility_score: float
    cost_of_error: CostLevel
    required_claims: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    defer_reasons: list[str] = field(default_factory=list)
    escalation_reasons: list[str] = field(default_factory=list)
    refusal_reasons: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
