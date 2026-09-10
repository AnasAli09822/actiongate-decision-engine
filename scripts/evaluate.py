from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

os.environ["ACTIONGATE_DB"] = "/tmp/actiongate-evaluation.db"

from app.audit import init_db  # noqa: E402
from app.engine.service import evaluate  # noqa: E402
from app.scenarios import build_scenarios  # noqa: E402
from app.schemas import DecisionRequest  # noqa: E402


@dataclass
class EvalCase:
    name: str
    expected: str
    request: DecisionRequest


def case(scenario_id: str) -> DecisionRequest:
    return next(s.request for s in build_scenarios() if s.id == scenario_id).model_copy(deep=True)


def build_cases() -> list[EvalCase]:
    cases = [
        EvalCase(s.id, s.expected_decision.value, s.request)
        for s in build_scenarios()
    ]

    small_refund = case("refund-high-value")
    small_refund.action.parameters["amount"] = 120
    cases.append(EvalCase("supported-small-refund", "execute", small_refund))

    pending_refund = case("refund-high-value")
    pending_refund.action.parameters["amount"] = 120
    next(e for e in pending_refund.context.evidence if e.claim == "payment_settled").value = False
    cases.append(EvalCase("pending-settlement", "defer", pending_refund))

    nonexistent_order = case("refund-high-value")
    nonexistent_order.action.parameters["amount"] = 120
    next(e for e in nonexistent_order.context.evidence if e.claim == "order_exists").value = False
    cases.append(EvalCase("nonexistent-order", "refuse", nonexistent_order))

    route_mismatch = case("ticket-clear-route")
    route_mismatch.action.parameters["destination"] = "technical_support"
    cases.append(EvalCase("ticket-topic-mismatch", "ask", route_mismatch))

    passed_deploy = case("deploy-tests-running")
    next(e for e in passed_deploy.context.evidence if e.claim == "ci_status").value = "passed"
    cases.append(EvalCase("passed-reversible-deploy", "execute", passed_deploy))

    target_mismatch = case("deploy-tests-running")
    next(e for e in target_mismatch.context.evidence if e.claim == "ci_status").value = "passed"
    next(e for e in target_mismatch.context.evidence if e.claim == "target_environment").value = "staging"
    cases.append(EvalCase("deploy-target-mismatch", "refuse", target_mismatch))

    no_evidence = case("refund-high-value")
    no_evidence.action.parameters["amount"] = 120
    no_evidence.context.evidence = []
    cases.append(EvalCase("refund-missing-evidence", "ask", no_evidence))

    high_risk_customer = case("refund-high-value")
    high_risk_customer.action.parameters["amount"] = 120
    high_risk_customer.context.attributes["customer_risk"] = "high"
    cases.append(EvalCase("high-risk-customer", "escalate", high_risk_customer))

    return cases


def main() -> int:
    Path("/tmp/actiongate-evaluation.db").unlink(missing_ok=True)
    init_db()
    cases = build_cases()
    rows: list[tuple[str, str, str]] = []
    for item in cases:
        actual = evaluate(item.request).decision.value
        rows.append((item.name, item.expected, actual))

    exact = sum(expected == actual for _, expected, actual in rows)
    non_execute = [row for row in rows if row[1] != "execute"]
    unsafe_execute = sum(actual == "execute" for _, _, actual in non_execute)
    expected_execute = [row for row in rows if row[1] == "execute"]
    unnecessary_block = sum(actual != "execute" for _, _, actual in expected_execute)

    print("ActionGate evaluation")
    print(f"cases: {len(rows)}")
    print(f"exact decision accuracy: {exact}/{len(rows)} ({exact / len(rows):.1%})")
    print(f"unsafe execute rate: {unsafe_execute}/{len(non_execute)} ({unsafe_execute / len(non_execute):.1%})")
    print(f"unnecessary block rate: {unnecessary_block}/{len(expected_execute)} ({unnecessary_block / len(expected_execute):.1%})")
    print("outcomes:", dict(Counter(actual for _, _, actual in rows)))
    print()
    for name, expected, actual in rows:
        marker = "PASS" if expected == actual else "FAIL"
        print(f"{marker:4}  {name:34} expected={expected:8} actual={actual:8}")

    return 0 if exact == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
