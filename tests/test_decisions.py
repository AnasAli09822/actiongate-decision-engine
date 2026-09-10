from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.audit import get_audit, init_db
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


@pytest.mark.parametrize("scenario", build_scenarios(), ids=lambda s: s.id)
def test_built_in_scenarios_match_expected_decisions(scenario):
    result = evaluate(scenario.request)
    assert result.decision == scenario.expected_decision


def test_all_five_outcomes_are_demonstrated():
    outcomes = {evaluate(s.request).decision.value for s in build_scenarios()}
    assert {"execute", "ask", "defer", "escalate", "refuse"}.issubset(outcomes)


def test_deliberate_failure_escalates_on_authoritative_conflict():
    scenario = next(s for s in build_scenarios() if s.deliberate_failure)
    result = evaluate(scenario.request)
    assert result.decision.value == "escalate"
    assert "AUTHORITATIVE_EVIDENCE_CONFLICT" in result.reason_codes
    assert "duplicate_charge" in result.evidence_conflicts


def test_hard_refusal_cannot_be_overridden_by_other_good_signals():
    result = evaluate(scenario_by_id("deploy-failed-tests").request)
    assert result.decision.value == "refuse"
    assert "TESTS_FAILED" in result.reason_codes


def test_refund_reason_must_be_supported_by_resolved_ledger_fact():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    duplicate = next(e for e in payload.context.evidence if e.claim == "duplicate_charge")
    duplicate.value = False
    result = evaluate(payload)
    assert result.decision.value == "escalate"
    assert "REFUND_REASON_NOT_SUPPORTED_BY_LEDGER" in result.reason_codes


def test_refund_for_nonexistent_order_is_refused():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    order = next(e for e in payload.context.evidence if e.claim == "order_exists")
    order.value = False
    result = evaluate(payload)
    assert result.decision.value == "refuse"
    assert "ORDER_NOT_FOUND_IN_AUTHORITATIVE_RECORD" in result.reason_codes


def test_non_positive_refund_is_refused():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 0
    result = evaluate(payload)
    assert result.decision.value == "refuse"
    assert "NON_POSITIVE_REFUND_AMOUNT" in result.reason_codes


def test_refund_pending_settlement_defers():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    settled = next(e for e in payload.context.evidence if e.claim == "payment_settled")
    settled.value = False
    result = evaluate(payload)
    assert result.decision.value == "defer"
    assert "PAYMENT_SETTLEMENT_PENDING" in result.reason_codes


def test_high_value_refund_escalates_even_with_strong_evidence():
    result = evaluate(scenario_by_id("refund-high-value").request)
    assert result.decision.value == "escalate"
    assert "AUTO_REFUND_LIMIT_EXCEEDED" in result.reason_codes


def test_small_supported_refund_executes():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    result = evaluate(payload)
    assert result.decision.value == "execute"


def test_deploy_uses_ci_evidence_over_context_claim():
    payload = scenario_by_id("deploy-tests-running").request.model_copy(deep=True)
    payload.context.attributes["tests_status"] = "passed"
    ci = next(e for e in payload.context.evidence if e.claim == "ci_status")
    ci.value = "failed"
    result = evaluate(payload)
    assert result.decision.value == "refuse"
    assert "TESTS_FAILED" in result.reason_codes


def test_deploy_manifest_target_mismatch_is_refused():
    payload = scenario_by_id("deploy-tests-running").request.model_copy(deep=True)
    ci = next(e for e in payload.context.evidence if e.claim == "ci_status")
    target = next(e for e in payload.context.evidence if e.claim == "target_environment")
    ci.value = "passed"
    target.value = "staging"
    result = evaluate(payload)
    assert result.decision.value == "refuse"
    assert "DEPLOYMENT_MANIFEST_TARGET_MISMATCH" in result.reason_codes


def test_irreversible_database_migration_without_backup_is_refused():
    payload = scenario_by_id("deploy-tests-running").request.model_copy(deep=True)
    ci = next(e for e in payload.context.evidence if e.claim == "ci_status")
    rollback = next(e for e in payload.context.evidence if e.claim == "rollback_available")
    ci.value = "passed"
    rollback.value = False
    migration = next(e for e in payload.context.evidence if e.claim == "database_migration")
    migration.value = True
    template = next(e for e in payload.context.evidence if e.claim == "change_risk")
    backup = template.model_copy(deep=True)
    backup.id = "ev_manifest_backup"
    backup.claim = "backup_available"
    backup.value = False
    payload.context.evidence.append(backup)
    result = evaluate(payload)
    assert result.decision.value == "refuse"
    assert "IRREVERSIBLE_MIGRATION_WITHOUT_BACKUP" in result.reason_codes


def test_ticket_route_conflicting_with_ticket_topic_asks():
    payload = scenario_by_id("ticket-clear-route").request.model_copy(deep=True)
    payload.action.parameters["destination"] = "technical_support"
    result = evaluate(payload)
    assert result.decision.value == "ask"
    assert "PROPOSED_ROUTE_CONFLICTS_WITH_TICKET_EVIDENCE" in result.reason_codes


def test_missing_required_evidence_asks_for_exact_claims():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    payload.context.evidence = []
    result = evaluate(payload)
    assert result.decision.value == "ask"
    assert "evidence:order_exists" in result.missing_information
    assert "evidence:payment_settled" in result.missing_information


def test_unregistered_source_is_rejected_and_cannot_satisfy_required_evidence():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    ledgers = [e for e in payload.context.evidence if e.kind == "payment_ledger"]
    for ledger in ledgers:
        ledger.source = "agent_claimed_ledger"
    result = evaluate(payload)
    assert all(ledger.id in result.evidence_rejected for ledger in ledgers)
    assert "evidence:payment_settled" in result.missing_information
    assert result.decision.value == "ask"


def test_source_cannot_masquerade_as_another_evidence_kind():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    ledgers = [e for e in payload.context.evidence if e.kind == "payment_ledger"]
    for ledger in ledgers:
        ledger.source = "support_platform"
    result = evaluate(payload)
    assert all(ledger.id in result.evidence_rejected for ledger in ledgers)
    assert "evidence:payment_settled" in result.missing_information


def test_stale_ci_evidence_is_rejected():
    payload = scenario_by_id("deploy-tests-running").request.model_copy(deep=True)
    ci = next(e for e in payload.context.evidence if e.kind == "ci_results")
    ci.observed_at = datetime.now(timezone.utc) - timedelta(days=8)
    result = evaluate(payload)
    assert ci.id in result.evidence_rejected
    assert "evidence:ci_status" in result.missing_information
    assert result.decision.value == "ask"


def test_audit_chain_contains_full_decision_path():
    result = evaluate(scenario_by_id("ticket-clear-route").request)
    trail = get_audit(result.decision_id)
    assert trail is not None
    assert trail["chain_valid"] is True
    assert [event["stage"] for event in trail["events"]] == [
        "input_received",
        "evidence_analyzed",
        "domain_assessed",
        "signals_computed",
        "decision_emitted",
    ]
    assert trail["events"][-1]["payload"]["decision"] == "execute"


def test_repeated_input_preserves_decision_semantics():
    request = scenario_by_id("refund-high-value").request
    first = evaluate(request)
    second = evaluate(request)
    assert first.decision == second.decision
    assert first.reason_codes == second.reason_codes
    assert first.policy_version == second.policy_version
    assert first.decision_id != second.decision_id


def test_registered_source_cannot_assert_unapproved_claim():
    payload = scenario_by_id("deploy-tests-running").request.model_copy(deep=True)
    ci = next(e for e in payload.context.evidence if e.claim == "ci_status")
    ci.claim = "tests_green"
    ci.value = True
    result = evaluate(payload)
    assert ci.id in result.evidence_rejected
    assert "evidence:ci_status" in result.missing_information
    assert result.decision.value == "ask"


def test_duplicate_refund_requires_duplicate_charge_evidence():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    payload.context.evidence = [e for e in payload.context.evidence if e.claim != "duplicate_charge"]
    result = evaluate(payload)
    assert result.decision.value == "ask"
    assert "evidence:duplicate_charge" in result.missing_information


def test_authoritative_legal_hold_cannot_be_overridden_by_context():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    payload.context.attributes["legal_hold"] = False
    legal_hold = next(e for e in payload.context.evidence if e.claim == "legal_hold")
    legal_hold.value = True
    result = evaluate(payload)
    assert result.decision.value == "refuse"
    assert "LEGAL_HOLD_BLOCKS_REFUND" in result.reason_codes


def test_defer_does_not_hide_unrelated_missing_information():
    payload = scenario_by_id("deploy-tests-running").request.model_copy(deep=True)
    payload.context.evidence = [
        e for e in payload.context.evidence if e.claim != "target_environment"
    ]
    result = evaluate(payload)
    assert result.decision.value == "ask"
    assert "evidence:target_environment" in result.missing_information


def test_refund_requires_negative_blocker_and_risk_checks_before_execute():
    payload = scenario_by_id("refund-high-value").request.model_copy(deep=True)
    payload.action.parameters["amount"] = 120
    payload.context.evidence = [
        e for e in payload.context.evidence if e.claim not in {"legal_hold", "chargeback_open", "customer_risk"}
    ]
    result = evaluate(payload)
    assert result.decision.value == "ask"
    assert "evidence:legal_hold" in result.missing_information
    assert "evidence:chargeback_open" in result.missing_information
    assert "evidence:customer_risk" in result.missing_information


def test_close_ticket_requires_safety_and_vip_facts():
    payload = scenario_by_id("ticket-clear-route").request.model_copy(deep=True)
    payload.action.type = "close_ticket"
    payload.action.parameters = {}
    result = evaluate(payload)
    assert result.decision.value == "ask"
    assert "evidence:safety_related" in result.missing_information
    assert "evidence:vip_customer" in result.missing_information
