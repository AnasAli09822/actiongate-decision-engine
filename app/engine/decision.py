from __future__ import annotations

from dataclasses import dataclass

from app.engine.types import DomainAssessment
from app.schemas import Decision, SignalSnapshot


@dataclass(frozen=True)
class DecisionResult:
    decision: Decision
    reason_codes: list[str]
    rationale: str
    next_step: str


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def decide(assessment: DomainAssessment, signals: SignalSnapshot) -> DecisionResult:
    reasons = list(assessment.reason_codes)

    if assessment.refusal_reasons:
        reasons.extend(assessment.refusal_reasons)
        return DecisionResult(
            Decision.REFUSE,
            _unique(reasons),
            "A hard policy boundary was triggered. Additional confidence or context cannot authorize this action.",
            "Do not execute this action. Change the proposal or satisfy the blocking policy outside this decision request.",
        )

    if signals.authoritative_evidence_conflicts:
        reasons.append("AUTHORITATIVE_EVIDENCE_CONFLICT")
        return DecisionResult(
            Decision.ESCALATE,
            _unique(reasons),
            "Material sources disagree and at least one conflicting source is authoritative. Autonomous execution is blocked.",
            "Route the case to an authorized reviewer with the conflicting evidence attached.",
        )

    if assessment.defer_reasons:
        reasons.extend(assessment.defer_reasons)
        return DecisionResult(
            Decision.DEFER,
            _unique(reasons),
            "A pending system state is expected to create or materially change the evidence. Waiting is safer than asking or guessing.",
            "Re-evaluate automatically when the pending system state reaches a terminal result.",
        )

    if signals.missing_information or signals.evidence_conflicts:
        if signals.evidence_conflicts:
            reasons.append("EVIDENCE_CONFLICT_REQUIRES_CLARIFICATION")
        if signals.missing_information:
            reasons.append("REQUIRED_INFORMATION_MISSING")
        return DecisionResult(
            Decision.ASK,
            _unique(reasons),
            "A specific fact is missing or unresolved and can be supplied now before a safe decision is made.",
            "Request only the listed missing facts, then re-run the same proposed action with the new evidence snapshot.",
        )

    if assessment.escalation_reasons:
        reasons.extend(assessment.escalation_reasons)
        return DecisionResult(
            Decision.ESCALATE,
            _unique(reasons),
            "The action may be legitimate, but its impact, authority boundary, or domain policy requires higher-authority review.",
            "Send the decision record to the designated reviewer; execution remains blocked until a separate authorized action is proposed.",
        )

    if signals.risk_score >= 0.78 or signals.confidence < 0.45:
        reasons.append("RISK_OR_CONFIDENCE_REQUIRES_REVIEW")
        return DecisionResult(
            Decision.ESCALATE,
            _unique(reasons),
            "Residual risk is too high, or evidence coherence is too weak, for autonomous execution.",
            "Escalate for review with the signal snapshot and evidence provenance attached.",
        )

    reasons.append("POLICY_AND_SIGNAL_CHECKS_PASSED")
    return DecisionResult(
        Decision.EXECUTE,
        _unique(reasons),
        "Required evidence is sufficient, no hard boundary is triggered, and residual risk is inside the autonomous execution envelope.",
        "The downstream executor may proceed with the exact proposed action and parameters.",
    )
