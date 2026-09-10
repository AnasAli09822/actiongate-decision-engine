from __future__ import annotations

import pytest

from app.audit import init_db
from app.engine.service import evaluate
from app.scenarios import build_scenarios


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    import app.audit as audit

    db_path = tmp_path / "actiongate.db"
    monkeypatch.setattr(audit, "DB_PATH", db_path)
    init_db()
    yield


def scenario_by_id(scenario_id: str):
    return next(s for s in build_scenarios() if s.id == scenario_id)


def test_string_boolean_chargeback_is_rejected_instead_of_treated_as_false():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    chargeback = next(e for e in payload.context.evidence if e.claim == "chargeback_open")
    chargeback.value = "true"
    result = evaluate(payload)
    assert chargeback.id in result.evidence_rejected
    assert "evidence:chargeback_open" in result.missing_information
    assert result.decision.value == "ask"


def test_string_boolean_rollback_is_rejected_instead_of_treated_as_truthy():
    payload = scenario_by_id("deploy-tests-running").request.model_copy(deep=True)
    rollback = next(e for e in payload.context.evidence if e.claim == "rollback_available")
    rollback.value = "false"
    result = evaluate(payload)
    assert rollback.id in result.evidence_rejected
    assert "evidence:rollback_available" in result.missing_information
    assert result.decision.value == "ask"


def test_enum_claims_are_normalized_before_policy_evaluation():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    customer_risk = next(e for e in payload.context.evidence if e.claim == "customer_risk")
    customer_risk.value = " HIGH "
    result = evaluate(payload)
    assert result.resolved_facts["customer_risk"] == "high"
    assert result.decision.value == "escalate"
    assert "HIGH_RISK_CUSTOMER" in result.reason_codes


def test_invalid_enum_claim_is_rejected():
    payload = scenario_by_id("deploy-tests-running").request.model_copy(deep=True)
    ci = next(e for e in payload.context.evidence if e.claim == "ci_status")
    ci.value = "green"
    result = evaluate(payload)
    assert ci.id in result.evidence_rejected
    assert "evidence:ci_status" in result.missing_information
    assert result.decision.value == "ask"


def test_actor_cannot_cross_domain_authority_boundary():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    payload.context.actor = "support-agent-7"
    result = evaluate(payload)
    assert result.decision.value == "refuse"
    assert "ACTOR_NOT_AUTHORIZED_FOR_ACTION" in result.reason_codes
    assert "ACTOR_AUTHORIZATION_DENIED" in result.risk_factors


def test_unknown_actor_is_refused_even_when_evidence_is_strong():
    payload = scenario_by_id("ticket-clear-route").request.model_copy(deep=True)
    payload.context.actor = "unregistered-agent"
    result = evaluate(payload)
    assert result.decision.value == "refuse"
    assert "UNKNOWN_ACTOR" in result.reason_codes


def test_refund_rejects_string_amount_instead_of_coercing_financial_input():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = "120"
    result = evaluate(payload)
    assert result.decision.value == "refuse"
    assert "INVALID_REFUND_AMOUNT" in result.reason_codes


@pytest.mark.parametrize("amount", [float("nan"), float("inf"), float("-inf")])
def test_refund_rejects_non_finite_amounts(amount):
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = amount
    result = evaluate(payload)
    assert result.decision.value == "refuse"
    assert "NON_FINITE_REFUND_AMOUNT" in result.reason_codes
