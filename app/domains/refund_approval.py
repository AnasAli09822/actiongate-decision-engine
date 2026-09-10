from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.engine.evidence import EvidenceAnalysis
from app.engine.types import DomainAssessment
from app.schemas import CostLevel, DecisionRequest

POLICY_VERSION = "refund-approval-v2.2"
REQUIRED_CLAIMS = ["payment_settled", "order_exists", "chargeback_open", "legal_hold", "customer_risk"]
AUTO_EXECUTE_LIMIT = Decimal("500.00")
MANUAL_REVIEW_LIMIT = Decimal("5000.00")


def required_claims(request: DecisionRequest) -> list[str]:
    claims = REQUIRED_CLAIMS.copy()
    reason = str(request.action.parameters.get("reason", "")).strip().lower()
    if reason == "duplicate_charge":
        claims.append("duplicate_charge")
    return claims


def assess(request: DecisionRequest, evidence: EvidenceAnalysis) -> DomainAssessment:
    action = request.action
    params = action.parameters
    policy_claims = required_claims(request)

    if action.type != "refund":
        return DomainAssessment(
            base_risk=0.95,
            reversibility_score=0.10,
            cost_of_error=CostLevel.HIGH,
            refusal_reasons=["UNSUPPORTED_REFUND_ACTION"],
            required_claims=policy_claims,
            risk_factors=["UNSUPPORTED_ACTION"],
        )

    missing: list[str] = []
    reasons: list[str] = []
    escalation: list[str] = []
    risk_factors: list[str] = ["FINANCIAL_ACTION"]

    amount = params.get("amount")
    reason = params.get("reason")
    currency = str(params.get("currency", "")).strip().upper()

    if amount is None:
        missing.append("amount")
    if not reason:
        missing.append("reason")
    if not currency:
        missing.append("currency")

    numeric_amount = Decimal("0")
    if amount is not None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            return DomainAssessment(
                base_risk=1.0,
                reversibility_score=0.10,
                cost_of_error=CostLevel.HIGH,
                refusal_reasons=["INVALID_REFUND_AMOUNT"],
                required_claims=policy_claims,
                risk_factors=risk_factors + ["INVALID_FINANCIAL_AMOUNT"],
            )
        try:
            numeric_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            return DomainAssessment(
                base_risk=1.0,
                reversibility_score=0.10,
                cost_of_error=CostLevel.HIGH,
                refusal_reasons=["INVALID_REFUND_AMOUNT"],
                required_claims=policy_claims,
                risk_factors=risk_factors + ["INVALID_FINANCIAL_AMOUNT"],
            )
        if not numeric_amount.is_finite():
            return DomainAssessment(
                base_risk=1.0,
                reversibility_score=0.10,
                cost_of_error=CostLevel.HIGH,
                refusal_reasons=["NON_FINITE_REFUND_AMOUNT"],
                required_claims=policy_claims,
                risk_factors=risk_factors + ["INVALID_FINANCIAL_AMOUNT"],
            )

    if numeric_amount <= 0 and amount is not None:
        return DomainAssessment(
            base_risk=1.0,
            reversibility_score=0.10,
            cost_of_error=CostLevel.HIGH,
            refusal_reasons=["NON_POSITIVE_REFUND_AMOUNT"],
            required_claims=policy_claims,
            risk_factors=risk_factors + ["INVALID_FINANCIAL_AMOUNT"],
        )

    if evidence.facts.get("order_exists") is False:
        return DomainAssessment(
            base_risk=0.98,
            reversibility_score=0.10,
            cost_of_error=CostLevel.HIGH,
            refusal_reasons=["ORDER_NOT_FOUND_IN_AUTHORITATIVE_RECORD"],
            required_claims=policy_claims,
            risk_factors=risk_factors + ["MISSING_AUTHORITATIVE_ORDER"],
            facts=evidence.facts,
        )

    chargeback_open = evidence.facts.get("chargeback_open")
    legal_hold = evidence.facts.get("legal_hold")
    payment_settled = evidence.facts.get("payment_settled")

    if chargeback_open is True:
        return DomainAssessment(
            base_risk=0.92,
            reversibility_score=0.10,
            cost_of_error=CostLevel.HIGH,
            required_claims=policy_claims,
            refusal_reasons=["OPEN_CHARGEBACK_BLOCKS_REFUND"],
            risk_factors=risk_factors + ["OPEN_CHARGEBACK"],
            facts=evidence.facts,
        )

    if legal_hold is True:
        return DomainAssessment(
            base_risk=0.98,
            reversibility_score=0.05,
            cost_of_error=CostLevel.CRITICAL,
            required_claims=policy_claims,
            refusal_reasons=["LEGAL_HOLD_BLOCKS_REFUND"],
            risk_factors=risk_factors + ["LEGAL_HOLD"],
            facts=evidence.facts,
        )

    if payment_settled is False:
        return DomainAssessment(
            base_risk=0.48,
            reversibility_score=0.20,
            cost_of_error=CostLevel.MEDIUM,
            required_claims=policy_claims,
            missing_information=missing,
            defer_reasons=["PAYMENT_SETTLEMENT_PENDING"],
            risk_factors=risk_factors + ["SETTLEMENT_PENDING"],
            facts=evidence.facts,
        )

    reason_normalized = str(reason or "").strip().lower()
    if reason_normalized == "duplicate_charge" and evidence.facts.get("duplicate_charge") is False:
        escalation.append("REFUND_REASON_NOT_SUPPORTED_BY_LEDGER")
        reasons.append("PROPOSED_ACTION_CONFLICTS_WITH_RESOLVED_EVIDENCE")
        risk_factors.append("REFUND_REASON_EVIDENCE_MISMATCH")

    amount_factor = min(float(numeric_amount / MANUAL_REVIEW_LIMIT), 1.0) * 0.42
    base_risk = 0.28 + amount_factor

    if numeric_amount > AUTO_EXECUTE_LIMIT:
        escalation.append("AUTO_REFUND_LIMIT_EXCEEDED")
        risk_factors.append("AUTONOMOUS_LIMIT_EXCEEDED")
    if numeric_amount > MANUAL_REVIEW_LIMIT:
        escalation.append("SENIOR_FINANCE_REVIEW_REQUIRED")
        risk_factors.append("HIGH_FINANCIAL_EXPOSURE")

    customer_risk = evidence.facts.get("customer_risk")
    if customer_risk == "high":
        base_risk += 0.18
        escalation.append("HIGH_RISK_CUSTOMER")
        risk_factors.append("HIGH_RISK_CUSTOMER")

    return DomainAssessment(
        base_risk=min(base_risk, 1.0),
        reversibility_score=0.25,
        cost_of_error=CostLevel.HIGH if numeric_amount > AUTO_EXECUTE_LIMIT else CostLevel.MEDIUM,
        required_claims=policy_claims,
        missing_information=list(dict.fromkeys(missing)),
        escalation_reasons=list(dict.fromkeys(escalation)),
        reason_codes=list(dict.fromkeys(reasons)),
        risk_factors=list(dict.fromkeys(risk_factors)),
        facts=evidence.facts,
    )
