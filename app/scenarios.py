from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import Scenario


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _evidence(
    *,
    id: str,
    source: str,
    kind: str,
    claim: str,
    value,
    reference: str | None = None,
) -> dict:
    return {
        "id": id,
        "source": source,
        "kind": kind,
        "claim": claim,
        "value": value,
        "observed_at": _now(),
        "reference": reference,
    }


def build_scenarios() -> list[Scenario]:
    return [
        Scenario.model_validate(
            {
                "id": "ticket-clear-route",
                "title": "Clear billing ticket",
                "description": "A low-risk, reversible routing action is strongly supported by the ticket record.",
                "expected_decision": "execute",
                "request": {
                    "action": {
                        "domain": "ticket_triage",
                        "type": "route_ticket",
                        "target": "ticket_10482",
                        "parameters": {"destination": "billing"},
                    },
                    "context": {
                        "actor": "support-agent-7",
                        "environment": "production",
                        "attributes": {
                            "ticket_text": "I was billed twice for invoice INV-4821. Please fix the duplicate charge.",
                            "vip_customer": False,
                            "safety_related": False,
                        },
                        "evidence": [
                            _evidence(
                                id="ev_ticket_10482",
                                source="support_platform",
                                kind="ticket_content",
                                claim="ticket_topic",
                                value="billing",
                                reference="ticket://10482/message/1",
                            )
                        ],
                    },
                },
            }
        ),
        Scenario.model_validate(
            {
                "id": "refund-missing-reason",
                "title": "Refund missing a reason",
                "description": "The payment and order are known, but a required fact can be supplied immediately.",
                "expected_decision": "ask",
                "request": {
                    "action": {
                        "domain": "refund_approval",
                        "type": "refund",
                        "target": "payment_2201",
                        "parameters": {"amount": 120, "currency": "USD"},
                    },
                    "context": {
                        "actor": "finance-agent-2",
                        "environment": "production",
                        "attributes": {"customer_risk": "low"},
                        "evidence": [
                            _evidence(
                                id="ev_ledger_2201_settled",
                                source="payments_ledger",
                                kind="payment_ledger",
                                claim="payment_settled",
                                value=True,
                                reference="ledger://payments/2201",
                            ),
                            _evidence(
                                id="ev_order_2201",
                                source="orders_service",
                                kind="order_record",
                                claim="order_exists",
                                value=True,
                                reference="orders://2201",
                            ),
                        ],
                    },
                },
            }
        ),
        Scenario.model_validate(
            {
                "id": "deploy-tests-running",
                "title": "Production deploy while CI is running",
                "description": "The missing truth does not exist yet. Waiting for CI to finish should change the decision.",
                "expected_decision": "defer",
                "request": {
                    "action": {
                        "domain": "code_deploy",
                        "type": "deploy",
                        "target": "production/api",
                        "parameters": {"commit": "7e91d3f"},
                    },
                    "context": {
                        "actor": "release-agent-1",
                        "environment": "production",
                        "attributes": {},
                        "evidence": [
                            _evidence(
                                id="ev_ci_7e91",
                                source="ci_pipeline",
                                kind="ci_results",
                                claim="ci_status",
                                value="running",
                                reference="ci://runs/70219",
                            ),
                            _evidence(
                                id="ev_manifest_7e91_target",
                                source="deployment_service",
                                kind="deployment_manifest",
                                claim="target_environment",
                                value="production",
                                reference="deploy://release/7e91d3f",
                            ),
                            _evidence(
                                id="ev_manifest_7e91_rollback",
                                source="deployment_service",
                                kind="deployment_manifest",
                                claim="rollback_available",
                                value=True,
                                reference="deploy://release/7e91d3f",
                            ),
                            _evidence(
                                id="ev_manifest_7e91_risk",
                                source="deployment_service",
                                kind="release_metadata",
                                claim="change_risk",
                                value="medium",
                                reference="deploy://release/7e91d3f",
                            ),
                        ],
                    },
                },
            }
        ),
        Scenario.model_validate(
            {
                "id": "refund-high-value",
                "title": "High-value refund",
                "description": "The claim is well supported, but the financial amount exceeds the autonomous execution limit.",
                "expected_decision": "escalate",
                "request": {
                    "action": {
                        "domain": "refund_approval",
                        "type": "refund",
                        "target": "payment_8832",
                        "parameters": {
                            "amount": 1800,
                            "currency": "USD",
                            "reason": "duplicate_charge",
                        },
                    },
                    "context": {
                        "actor": "finance-agent-2",
                        "environment": "production",
                        "attributes": {"customer_risk": "low"},
                        "evidence": [
                            _evidence(
                                id="ev_ledger_8832_duplicate",
                                source="payments_ledger",
                                kind="payment_ledger",
                                claim="duplicate_charge",
                                value=True,
                                reference="ledger://payments/8832",
                            ),
                            _evidence(
                                id="ev_ledger_8832_settled",
                                source="payments_ledger",
                                kind="payment_ledger",
                                claim="payment_settled",
                                value=True,
                                reference="ledger://payments/8832",
                            ),
                            _evidence(
                                id="ev_order_8832",
                                source="orders_service",
                                kind="order_record",
                                claim="order_exists",
                                value=True,
                                reference="orders://8832",
                            ),
                        ],
                    },
                },
            }
        ),
        Scenario.model_validate(
            {
                "id": "deploy-failed-tests",
                "title": "Deploy with failed tests",
                "description": "Failed CI is a hard boundary. Higher confidence cannot turn this into an executable action.",
                "expected_decision": "refuse",
                "request": {
                    "action": {
                        "domain": "code_deploy",
                        "type": "deploy",
                        "target": "production/web",
                        "parameters": {"commit": "badc0de"},
                    },
                    "context": {
                        "actor": "release-agent-1",
                        "environment": "production",
                        "attributes": {},
                        "evidence": [
                            _evidence(
                                id="ev_ci_badc0de",
                                source="ci_pipeline",
                                kind="ci_results",
                                claim="ci_status",
                                value="failed",
                                reference="ci://runs/70233",
                            ),
                            _evidence(
                                id="ev_manifest_badc0de_target",
                                source="deployment_service",
                                kind="deployment_manifest",
                                claim="target_environment",
                                value="production",
                                reference="deploy://release/badc0de",
                            ),
                            _evidence(
                                id="ev_manifest_badc0de_rollback",
                                source="deployment_service",
                                kind="deployment_manifest",
                                claim="rollback_available",
                                value=True,
                                reference="deploy://release/badc0de",
                            ),
                            _evidence(
                                id="ev_manifest_badc0de_risk",
                                source="deployment_service",
                                kind="release_metadata",
                                claim="change_risk",
                                value="medium",
                                reference="deploy://release/badc0de",
                            ),
                        ],
                    },
                },
            }
        ),
        Scenario.model_validate(
            {
                "id": "failure-conflicting-refund-evidence",
                "title": "Failure test: conflicting refund evidence",
                "description": "A CRM note claims a duplicate charge while the authoritative payment ledger says only one charge succeeded.",
                "expected_decision": "escalate",
                "deliberate_failure": True,
                "request": {
                    "action": {
                        "domain": "refund_approval",
                        "type": "refund",
                        "target": "payment_4410",
                        "parameters": {
                            "amount": 480,
                            "currency": "USD",
                            "reason": "duplicate_charge",
                        },
                    },
                    "context": {
                        "actor": "finance-agent-2",
                        "environment": "production",
                        "attributes": {"agent_reported_confidence": 0.96},
                        "evidence": [
                            _evidence(
                                id="ev_crm_4410",
                                source="crm_note",
                                kind="order_record",
                                claim="duplicate_charge",
                                value=True,
                                reference="crm://customer/771/note/9102",
                            ),
                            _evidence(
                                id="ev_ledger_4410",
                                source="payments_ledger",
                                kind="payment_ledger",
                                claim="duplicate_charge",
                                value=False,
                                reference="ledger://payments/4410",
                            ),
                            _evidence(
                                id="ev_order_4410",
                                source="orders_service",
                                kind="order_record",
                                claim="order_exists",
                                value=True,
                                reference="orders://4410",
                            ),
                            _evidence(
                                id="ev_ledger_4410_settled",
                                source="payments_ledger",
                                kind="payment_ledger",
                                claim="payment_settled",
                                value=True,
                                reference="ledger://payments/4410",
                            ),
                        ],
                    },
                },
            }
        ),
    ]


def get_scenarios() -> list[Scenario]:
    return build_scenarios()


def get_scenario(scenario_id: str) -> Scenario | None:
    return next((scenario for scenario in build_scenarios() if scenario.id == scenario_id), None)
