from __future__ import annotations

from app.engine.evidence import EvidenceAnalysis
from app.engine.types import DomainAssessment
from app.schemas import CostLevel, DecisionRequest

POLICY_VERSION = "ticket-triage-v2.1"
REQUIRED_CLAIMS = ["ticket_topic"]


def required_claims(request: DecisionRequest) -> list[str]:
    claims = REQUIRED_CLAIMS.copy()
    if request.action.type == "close_ticket":
        claims.extend(["vip_customer", "safety_related"])
    return claims


def assess(request: DecisionRequest, evidence: EvidenceAnalysis) -> DomainAssessment:
    action = request.action
    attrs = request.context.attributes
    policy_claims = required_claims(request)

    if action.type not in {"route_ticket", "close_ticket"}:
        return DomainAssessment(
            base_risk=0.90,
            reversibility_score=0.20,
            cost_of_error=CostLevel.HIGH,
            refusal_reasons=["UNSUPPORTED_TICKET_ACTION"],
            required_claims=policy_claims,
            risk_factors=["UNSUPPORTED_ACTION"],
        )

    missing: list[str] = []
    if not attrs.get("ticket_text"):
        missing.append("ticket_text")
    if action.type == "route_ticket" and not action.parameters.get("destination"):
        missing.append("destination")

    risk = 0.12 if action.type == "route_ticket" else 0.34
    reversibility = 0.95 if action.type == "route_ticket" else 0.65
    cost = CostLevel.LOW if action.type == "route_ticket" else CostLevel.MEDIUM
    escalation: list[str] = []
    reasons: list[str] = []
    risk_factors: list[str] = []

    vip_customer = evidence.facts.get("vip_customer", attrs.get("vip_customer"))
    safety_related = evidence.facts.get("safety_related", attrs.get("safety_related"))

    if vip_customer and action.type == "close_ticket":
        risk += 0.18
        escalation.append("VIP_TICKET_CLOSE_REQUIRES_REVIEW")
        risk_factors.append("VIP_CUSTOMER")

    if safety_related:
        risk += 0.25
        escalation.append("SAFETY_RELATED_TICKET_REQUIRES_REVIEW")
        risk_factors.append("SAFETY_RELATED")

    if action.type == "route_ticket":
        proposed_destination = str(action.parameters.get("destination", "")).strip().lower()
        evidence_topic = str(evidence.facts.get("ticket_topic", "")).strip().lower()
        if proposed_destination and evidence_topic and proposed_destination != evidence_topic:
            missing.append("confirm_destination_due_to_topic_mismatch")
            reasons.append("PROPOSED_ROUTE_CONFLICTS_WITH_TICKET_EVIDENCE")
            risk_factors.append("ROUTE_EVIDENCE_MISMATCH")

    return DomainAssessment(
        base_risk=min(risk, 1.0),
        reversibility_score=reversibility,
        cost_of_error=cost,
        required_claims=policy_claims,
        missing_information=list(dict.fromkeys(missing)),
        escalation_reasons=list(dict.fromkeys(escalation)),
        reason_codes=list(dict.fromkeys(reasons)),
        risk_factors=list(dict.fromkeys(risk_factors)),
        facts=evidence.facts,
    )
