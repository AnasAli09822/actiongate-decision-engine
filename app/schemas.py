from __future__ import annotations

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Domain(str, Enum):
    TICKET_TRIAGE = "ticket_triage"
    REFUND_APPROVAL = "refund_approval"
    CODE_DEPLOY = "code_deploy"


class Decision(str, Enum):
    EXECUTE = "execute"
    ASK = "ask"
    DEFER = "defer"
    ESCALATE = "escalate"
    REFUSE = "refuse"


class CostLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceItem(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=100)
    kind: str = Field(min_length=1, max_length=100)
    claim: str = Field(min_length=1, max_length=200)
    value: Any
    observed_at: datetime
    reference: str | None = Field(default=None, max_length=300)

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime) -> datetime:
        normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if normalized.astimezone(timezone.utc) > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("observed_at cannot be more than five minutes in the future")
        return normalized


class ProposedAction(StrictModel):
    domain: Domain
    type: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=120)
    parameters: dict[str, Any] = Field(default_factory=dict)


class DecisionContext(StrictModel):
    actor: str = Field(min_length=1, max_length=120)
    environment: str = Field(default="production", min_length=1, max_length=40)
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=50)


class DecisionRequest(StrictModel):
    action: ProposedAction
    context: DecisionContext

    @model_validator(mode="after")
    def validate_identity(self) -> "DecisionRequest":
        if not self.context.actor.strip():
            raise ValueError("actor cannot be empty")
        if not self.action.target.strip():
            raise ValueError("target cannot be empty")
        evidence_ids = [item.id for item in self.context.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence ids must be unique within a decision request")
        return self


class Reversibility(StrictModel):
    score: float = Field(ge=0.0, le=1.0)
    label: str


class SignalSnapshot(StrictModel):
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    reversibility: Reversibility
    cost_of_error: CostLevel
    missing_information: list[str]
    evidence_conflicts: list[str]
    authoritative_evidence_conflicts: list[str]
    risk_factors: list[str]


class DecisionResponse(StrictModel):
    decision_id: str
    decision: Decision
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    evidence_used: list[str]
    evidence_rejected: list[str]
    evidence_conflicts: list[str]
    resolved_facts: dict[str, Any]
    missing_information: list[str]
    reversibility: Reversibility
    cost_of_error: CostLevel
    risk_factors: list[str]
    reason_codes: list[str]
    rationale: str
    next_step: str
    policy_version: str
    created_at: str


class Scenario(StrictModel):
    id: str
    title: str
    description: str
    expected_decision: Decision
    request: DecisionRequest
    deliberate_failure: bool = False
