from __future__ import annotations

from app.engine.evidence import EvidenceAnalysis
from app.engine.types import DomainAssessment
from app.schemas import Reversibility, SignalSnapshot


def _label_reversibility(score: float) -> str:
    if score >= 0.80:
        return "high"
    if score >= 0.45:
        return "partial"
    return "low"


def compute_signals(assessment: DomainAssessment, evidence: EvidenceAnalysis) -> SignalSnapshot:
    missing = list(
        dict.fromkeys(
            assessment.missing_information
            + [f"evidence:{kind}" for kind in evidence.missing_required_kinds]
        )
    )

    missing_penalty = min(0.45, 0.12 * len(missing))
    conflict_penalty = min(0.40, 0.20 * len(evidence.conflicts))
    confidence = max(
        0.0,
        min(1.0, 0.35 + (0.65 * evidence.strength) - missing_penalty - conflict_penalty),
    )

    irreversibility = 1.0 - assessment.reversibility_score
    risk_factors = list(assessment.risk_factors)
    risk_adjustment = 0.20 * irreversibility
    if irreversibility >= 0.55:
        risk_factors.append("LOW_REVERSIBILITY")
    if evidence.conflicts:
        risk_factors.append("EVIDENCE_CONFLICT")
    if missing:
        risk_factors.append("MISSING_INFORMATION")

    risk = min(
        1.0,
        assessment.base_risk
        + risk_adjustment
        + (0.12 * len(evidence.conflicts))
        + (0.06 * len(missing)),
    )

    return SignalSnapshot(
        confidence=round(confidence, 3),
        risk_score=round(risk, 3),
        evidence_strength=evidence.strength,
        reversibility=Reversibility(
            score=round(assessment.reversibility_score, 3),
            label=_label_reversibility(assessment.reversibility_score),
        ),
        cost_of_error=assessment.cost_of_error,
        missing_information=missing,
        evidence_conflicts=evidence.conflicts,
        authoritative_evidence_conflicts=evidence.authoritative_conflicts,
        risk_factors=list(dict.fromkeys(risk_factors)),
    )
