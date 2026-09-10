from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from app.engine.claim_contracts import validate_claim_value
from app.engine.source_registry import freshness_score, source_profile
from app.schemas import EvidenceItem


CREDIBLE_WEIGHT = 0.35
AUTHORITATIVE_AUTHORITY = 0.90
AUTHORITATIVE_RELIABILITY = 0.90


@dataclass(frozen=True)
class EvaluatedEvidence:
    id: str
    source: str
    kind: str
    claim: str
    trusted_source: bool
    reliability: float
    authority: float
    freshness: float
    effective_weight: float
    normalized_value: Any = None
    rejection_reason: str | None = None


@dataclass(frozen=True)
class EvidenceAnalysis:
    strength: float
    used_ids: list[str]
    rejected_ids: list[str]
    conflicts: list[str]
    authoritative_conflicts: list[str]
    facts: dict[str, Any]
    fact_sources: dict[str, str]
    missing_required_claims: list[str]
    evaluated: list[EvaluatedEvidence]


def _canonical(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().lower()


def analyze_evidence(items: list[EvidenceItem], required_claims: list[str]) -> EvidenceAnalysis:
    evaluated: list[EvaluatedEvidence] = []
    accepted: list[tuple[EvidenceItem, EvaluatedEvidence, Any]] = []

    for item in items:
        profile = source_profile(item.source, item.kind, item.claim)
        if profile is None:
            entry = EvaluatedEvidence(
                id=item.id,
                source=item.source,
                kind=item.kind,
                claim=item.claim,
                trusted_source=False,
                reliability=0.0,
                authority=0.0,
                freshness=0.0,
                effective_weight=0.0,
                rejection_reason="UNREGISTERED_SOURCE_KIND_OR_CLAIM",
            )
            evaluated.append(entry)
            continue

        claim_value = validate_claim_value(item.claim, item.value)
        freshness = freshness_score(item.observed_at, profile)
        weight = round(profile.reliability * profile.authority * freshness, 4)
        if not claim_value.valid:
            rejection = claim_value.rejection_reason
        elif freshness <= 0:
            rejection = "STALE_EVIDENCE"
        else:
            rejection = None
        entry = EvaluatedEvidence(
            id=item.id,
            source=item.source,
            kind=item.kind,
            claim=item.claim,
            trusted_source=True,
            reliability=profile.reliability,
            authority=profile.authority,
            freshness=freshness,
            effective_weight=weight if rejection is None else 0.0,
            normalized_value=claim_value.value if claim_value.valid else None,
            rejection_reason=rejection,
        )
        evaluated.append(entry)
        if rejection is None:
            accepted.append((item, entry, claim_value.value))

    by_claim: dict[str, list[tuple[EvidenceItem, EvaluatedEvidence, Any]]] = defaultdict(list)
    for item, entry, normalized_value in accepted:
        by_claim[item.claim].append((item, entry, normalized_value))

    conflicts: list[str] = []
    authoritative_conflicts: list[str] = []
    facts: dict[str, Any] = {}
    fact_sources: dict[str, str] = {}
    resolved_weights: list[float] = []

    for claim, pairs in by_claim.items():
        ranked = sorted(pairs, key=lambda pair: pair[1].effective_weight, reverse=True)
        strongest_item, strongest_entry, strongest_value = ranked[0]
        if strongest_entry.effective_weight < CREDIBLE_WEIGHT:
            continue

        facts[claim] = strongest_value
        fact_sources[claim] = strongest_item.id
        resolved_weights.append(strongest_entry.effective_weight)

        credible = [pair for pair in ranked if pair[1].effective_weight >= CREDIBLE_WEIGHT]
        credible_values = {_canonical(pair[2]) for pair in credible}
        if len(credible_values) > 1:
            conflicts.append(claim)
            if any(
                pair[1].authority >= AUTHORITATIVE_AUTHORITY
                and pair[1].reliability >= AUTHORITATIVE_RELIABILITY
                for pair in credible
            ):
                authoritative_conflicts.append(claim)

    credible_claims = {
        item.claim
        for item, entry, _ in accepted
        if entry.effective_weight >= CREDIBLE_WEIGHT
    }
    missing_required = sorted(set(required_claims) - credible_claims)
    coverage = 1.0 if not required_claims else (
        (len(required_claims) - len(missing_required)) / len(required_claims)
    )
    quality = sum(resolved_weights) / len(resolved_weights) if resolved_weights else 0.0
    conflict_penalty = min(0.45, 0.18 * len(conflicts))
    rejection_penalty = min(0.20, 0.05 * sum(1 for entry in evaluated if entry.rejection_reason))
    strength = max(
        0.0,
        min(1.0, (0.60 * quality) + (0.40 * coverage) - conflict_penalty - rejection_penalty),
    )

    used_ids = [
        entry.id
        for entry in evaluated
        if entry.rejection_reason is None and entry.effective_weight >= CREDIBLE_WEIGHT
    ]
    rejected_ids = [
        entry.id
        for entry in evaluated
        if entry.rejection_reason is not None or entry.effective_weight < CREDIBLE_WEIGHT
    ]

    return EvidenceAnalysis(
        strength=round(strength, 3),
        used_ids=used_ids,
        rejected_ids=rejected_ids,
        conflicts=sorted(conflicts),
        authoritative_conflicts=sorted(authoritative_conflicts),
        facts=facts,
        fact_sources=fact_sources,
        missing_required_claims=missing_required,
        evaluated=evaluated,
    )
