from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.audit import append_event
from app.domains import DOMAIN_MODULES
from app.engine.decision import decide
from app.engine.evidence import analyze_evidence
from app.engine.signals import compute_signals
from app.schemas import DecisionRequest, DecisionResponse


def evaluate(request: DecisionRequest) -> DecisionResponse:
    decision_id = f"dec_{uuid4().hex[:12]}"
    module = DOMAIN_MODULES[request.action.domain]
    policy_version = module.POLICY_VERSION

    append_event(
        decision_id,
        "input_received",
        {
            "request": request.model_dump(mode="json"),
            "policy_version": policy_version,
        },
    )

    required_claims = module.required_claims(request)
    evidence = analyze_evidence(request.context.evidence, required_claims)
    append_event(
        decision_id,
        "evidence_analyzed",
        {
            "strength": evidence.strength,
            "used_ids": evidence.used_ids,
            "rejected_ids": evidence.rejected_ids,
            "conflicts": evidence.conflicts,
            "authoritative_conflicts": evidence.authoritative_conflicts,
            "missing_required_claims": evidence.missing_required_claims,
            "resolved_facts": evidence.facts,
            "fact_sources": evidence.fact_sources,
            "source_assessments": [entry.__dict__ for entry in evidence.evaluated],
        },
    )

    assessment = module.assess(request, evidence)
    append_event(
        decision_id,
        "domain_assessed",
        {
            "base_risk": assessment.base_risk,
            "reversibility_score": assessment.reversibility_score,
            "cost_of_error": assessment.cost_of_error.value,
            "missing_information": assessment.missing_information,
            "defer_reasons": assessment.defer_reasons,
            "escalation_reasons": assessment.escalation_reasons,
            "refusal_reasons": assessment.refusal_reasons,
            "required_claims": assessment.required_claims,
            "reason_codes": assessment.reason_codes,
            "risk_factors": assessment.risk_factors,
        },
    )

    signals = compute_signals(assessment, evidence)
    append_event(decision_id, "signals_computed", signals.model_dump(mode="json"))

    result = decide(assessment, signals)
    created_at = datetime.now(timezone.utc).isoformat()
    response = DecisionResponse(
        decision_id=decision_id,
        decision=result.decision,
        confidence=signals.confidence,
        risk_score=signals.risk_score,
        evidence_strength=signals.evidence_strength,
        evidence_used=evidence.used_ids,
        evidence_rejected=evidence.rejected_ids,
        evidence_conflicts=evidence.conflicts,
        resolved_facts=evidence.facts,
        missing_information=signals.missing_information,
        reversibility=signals.reversibility,
        cost_of_error=signals.cost_of_error,
        risk_factors=signals.risk_factors,
        reason_codes=result.reason_codes,
        rationale=result.rationale,
        next_step=result.next_step,
        policy_version=policy_version,
        created_at=created_at,
    )

    append_event(decision_id, "decision_emitted", response.model_dump(mode="json"))
    return response
