from __future__ import annotations

from app.engine.evidence import EvidenceAnalysis
from app.engine.types import DomainAssessment
from app.schemas import CostLevel, DecisionRequest

POLICY_VERSION = "code-deploy-v2.0"
REQUIRED_EVIDENCE_KINDS = ["ci_results", "deployment_manifest"]


def required_evidence(_: DecisionRequest) -> list[str]:
    return REQUIRED_EVIDENCE_KINDS.copy()


def assess(request: DecisionRequest, evidence: EvidenceAnalysis) -> DomainAssessment:
    action = request.action
    attrs = request.context.attributes

    if action.type != "deploy":
        return DomainAssessment(
            base_risk=0.98,
            reversibility_score=0.05,
            cost_of_error=CostLevel.CRITICAL,
            refusal_reasons=["UNSUPPORTED_DEPLOY_ACTION"],
            required_evidence_kinds=REQUIRED_EVIDENCE_KINDS,
            risk_factors=["UNSUPPORTED_ACTION"],
        )

    missing: list[str] = []
    risk_factors: list[str] = ["PRODUCTION_CHANGE"]

    tests_status = evidence.facts.get("ci_status", attrs.get("tests_status"))
    rollback_available = evidence.facts.get("rollback_available", attrs.get("rollback_available"))
    change_risk = str(evidence.facts.get("change_risk", attrs.get("change_risk", "unknown"))).lower()
    db_migration = bool(evidence.facts.get("database_migration", attrs.get("database_migration", False)))
    backup_available = evidence.facts.get("backup_available", attrs.get("backup_available"))
    incident_active = bool(evidence.facts.get("incident_active", attrs.get("incident_active", False)))
    approved_hotfix = bool(evidence.facts.get("approved_hotfix", attrs.get("approved_hotfix", False)))

    if tests_status is None:
        missing.append("tests_status")
    if rollback_available is None:
        missing.append("rollback_available")
    if change_risk == "unknown":
        missing.append("change_risk")

    target_environment = str(evidence.facts.get("target_environment", "")).strip().lower()
    requested_environment = str(request.context.environment).strip().lower()
    if target_environment and requested_environment and target_environment != requested_environment:
        return DomainAssessment(
            base_risk=0.98,
            reversibility_score=0.05,
            cost_of_error=CostLevel.CRITICAL,
            required_evidence_kinds=REQUIRED_EVIDENCE_KINDS,
            refusal_reasons=["DEPLOYMENT_MANIFEST_TARGET_MISMATCH"],
            risk_factors=risk_factors + ["TARGET_MISMATCH"],
            facts=evidence.facts,
        )

    if tests_status == "failed":
        return DomainAssessment(
            base_risk=0.98,
            reversibility_score=0.25 if rollback_available else 0.05,
            cost_of_error=CostLevel.CRITICAL,
            required_evidence_kinds=REQUIRED_EVIDENCE_KINDS,
            refusal_reasons=["TESTS_FAILED"],
            risk_factors=risk_factors + ["FAILED_CI"],
            facts=evidence.facts,
        )

    if db_migration and rollback_available is False and backup_available is False:
        return DomainAssessment(
            base_risk=1.0,
            reversibility_score=0.02,
            cost_of_error=CostLevel.CRITICAL,
            required_evidence_kinds=REQUIRED_EVIDENCE_KINDS,
            refusal_reasons=["IRREVERSIBLE_MIGRATION_WITHOUT_BACKUP"],
            risk_factors=risk_factors + ["IRREVERSIBLE_DATABASE_CHANGE", "NO_BACKUP"],
            facts=evidence.facts,
        )

    defer: list[str] = []
    if tests_status in {"running", "pending"}:
        defer.append("CI_RESULTS_PENDING")
        risk_factors.append("PENDING_CI")

    escalation: list[str] = []
    if change_risk in {"high", "critical"}:
        escalation.append("HIGH_RISK_CHANGE_REQUIRES_REVIEW")
        risk_factors.append("HIGH_RISK_CHANGE")
    if incident_active and not approved_hotfix:
        escalation.append("ACTIVE_INCIDENT_REQUIRES_INCIDENT_COMMAND_REVIEW")
        risk_factors.append("ACTIVE_INCIDENT")

    reversibility = 0.82 if rollback_available else 0.25
    if db_migration:
        reversibility -= 0.25
        risk_factors.append("DATABASE_MIGRATION")
    reversibility = max(0.05, reversibility)

    risk_by_change = {
        "low": 0.30,
        "medium": 0.48,
        "high": 0.72,
        "critical": 0.90,
        "unknown": 0.62,
    }
    base_risk = risk_by_change.get(change_risk, 0.62)

    return DomainAssessment(
        base_risk=base_risk,
        reversibility_score=reversibility,
        cost_of_error=CostLevel.CRITICAL,
        required_evidence_kinds=REQUIRED_EVIDENCE_KINDS,
        missing_information=missing,
        defer_reasons=defer,
        escalation_reasons=escalation,
        risk_factors=list(dict.fromkeys(risk_factors)),
        facts=evidence.facts,
    )
