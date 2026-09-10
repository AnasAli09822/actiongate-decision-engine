# Signal model

The scores are decision-support heuristics, not calibrated probabilities. Hard policy rules always take precedence.

## Source trust

Evidence does not carry client-supplied trust scores. A server-side source profile defines:

- reliability;
- authority;
- permitted evidence kinds and claims;
- freshness half-life;
- maximum acceptable age.

Freshness is computed from the evidence timestamp:

```text
freshness = 0.5 ^ (age_seconds / freshness_half_life_seconds)
```

Evidence older than the source profile's maximum age is rejected.

For accepted evidence:

```text
effective_weight = source_reliability × source_authority × freshness
```

## Evidence strength

For each claim, the strongest credible item becomes the resolved fact. Credible disagreements are retained as conflicts instead of being averaged away.

```text
evidence_strength =
    0.60 × resolved_evidence_quality
  + 0.40 × required_claim_coverage
  - conflict_penalty
  - rejected_evidence_penalty
```

A required claim is covered only by a registered source that is permitted to assert that claim and whose effective weight meets the credibility threshold.

## Confidence

```text
confidence =
    0.35
  + 0.65 × evidence_strength
  - missing_information_penalty
  - conflict_penalty
```

This is confidence that the decision inputs are sufficiently complete and coherent. It is not a probability that the downstream action will succeed.

## Risk

Each domain supplies a base risk from the proposed action. The cross-domain engine adds penalties for irreversibility, evidence conflicts, and missing information:

```text
risk =
    domain_base_risk
  + 0.20 × (1 - reversibility)
  + evidence_conflict_penalty
  + missing_information_penalty
```

The response also exposes named `risk_factors` so the numerical score is not opaque.

## Why there is no master score

The five outcomes represent different control actions. A missing refund reason should `ask`; CI still running should `defer`; a legitimate high-value refund should `escalate`; failed CI should `refuse`. Collapsing those states into a single threshold would erase the operational distinction the system is designed to preserve.

## Calibration boundary

The constants are intentionally explicit and testable. They are not claimed to be universal. A production rollout should calibrate them from observed false-allow cost, unnecessary escalation cost, domain incidents, approval outcomes, and operator behavior.
