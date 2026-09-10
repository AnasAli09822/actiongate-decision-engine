# Submission notes

## Live demo

https://actiongate-decision.hatchable.site

## What to inspect

- `app/engine/source_registry.py` — server-controlled evidence trust.
- `app/engine/evidence.py` — freshness, source-kind-claim validation, typed value contracts, fact resolution, and conflict detection.
- `app/engine/claim_contracts.py` — strict boolean/enum/text claim validation and normalization.
- `app/engine/actor_registry.py` — server-side domain/action/environment capability checks.
- `app/domains/` — three versioned domain policies.
- `app/engine/signals.py` — confidence, risk, evidence strength, reversibility, and named risk factors.
- `app/engine/decision.py` — explicit precedence for all five outcomes.
- `app/audit.py` — append-only SQLite controls and SHA-256 event chaining.
- `scripts/evaluate.py` — cross-domain evaluation harness.
- `tests/` — decision semantics, source spoofing, claim spoofing, malformed claim values, actor authorization, stale evidence, API behavior, and audit tampering.

## AI usage

AI assistance was used for design review, implementation drafting, adversarial test generation, and documentation editing. Runtime authority is not delegated to a language model.

## Intentionally out of scope

The repository does not execute real refunds or production deployments. It also omits organization authentication, connector-level cryptographic source authentication, signed execution permits, distributed audit persistence, a policy-authoring UI, and statistically calibrated confidence. Those concerns sit outside the decision mechanic demonstrated here and are called out rather than simulated.
