# Architecture snapshot

ActionGate is a decision boundary between an AI agent and a consequential tool. It accepts a structured proposed action plus context, resolves evidence against server-controlled trust and claim contracts, applies actor capability and versioned domain policy, computes decision-support signals, and emits one operational outcome: `execute`, `ask`, `defer`, `escalate`, or `refuse`.

```text
AI agent / caller
       |
       v
Proposed action + context
       |
       v
Evidence intake
       |
       +--> source registry (server-controlled trust)
       +--> source-kind-claim allowlist
       +--> typed claim contract + normalization
       +--> freshness calculation from observed_at
       +--> conflict detection + resolved facts
       |
       v
Actor authorization + domain policy (versioned)
       |
       +--> registered domain/action/environment capability
       +--> hard boundaries
       +--> pending states
       +--> missing facts
       +--> authority / impact thresholds
       |
       v
Signal engine
       |
       +--> confidence
       +--> risk score
       +--> evidence strength
       +--> missing information
       +--> reversibility
       +--> cost of error
       |
       v
Decision engine
       |
       +--> execute
       +--> ask
       +--> defer
       +--> escalate
       +--> refuse
       |
       v
Append-only, hash-chained audit trail
```

## Decision precedence

1. `refuse` — a hard domain or actor-authorization boundary is violated.
2. `escalate` — credible evidence conflicts with an authoritative source.
3. `ask` — a fact is missing or unresolved and can be obtained now.
4. `defer` — all required facts are present, but a pending system process is expected to change one of them.
5. `escalate` — the action is plausible but exceeds an autonomous authority or impact limit.
6. `escalate` — residual risk is too high or evidence coherence is too weak.
7. `execute` — evidence is sufficient, actor capability is valid, no hard rule is triggered, and residual risk is within the autonomous execution envelope.

The outcomes are operational states, not score bands. `ask` and `defer` differ by whether the needed truth can be obtained now. `escalate` and `refuse` differ by whether a higher-authority review could legitimately allow the exact proposal.

## Evidence trust boundary

The request cannot assign its own reliability, authority, or freshness score. Those values are owned by `app/engine/source_registry.py`. Claim value semantics are owned by `app/engine/claim_contracts.py`.

For every evidence item the engine:

1. verifies that the source is registered for both the claimed evidence kind and the specific claim;
2. obtains reliability and authority from the server-side registry;
3. validates the claim value against an explicit boolean, enum, or text contract and normalizes accepted values;
4. computes freshness from `observed_at` and the source profile;
5. rejects unknown, mismatched, malformed, or stale evidence;
6. resolves facts from the strongest credible evidence;
7. checks required claim coverage, not just evidence-type presence;
8. retains credible disagreements as explicit conflicts.

The public demo API models evidence that has already passed through authenticated source adapters. Production connectors would cryptographically authenticate source provenance before creating these evidence items.

## Actor authority boundary

`app/engine/actor_registry.py` is server-controlled. The caller may name the proposing actor, but that name does not carry authority by itself. Before execution is possible, the registry checks whether that actor is registered for the requested domain/action pair and environment. Unknown actors and cross-domain capability violations are hard authorization refusals.

The demo intentionally stops short of organization identity and connector authentication. In production, the authenticated principal at the API or gateway would be bound to the actor identity before this registry check.

## Audit model

Every decision writes five ordered events:

1. `input_received`
2. `evidence_analyzed`
3. `domain_assessed`
4. `signals_computed`
5. `decision_emitted`

The `domain_assessed` event includes the actor-authorization result alongside policy facts and hard-boundary reasons. SQLite triggers reject normal `UPDATE` and `DELETE` operations on the audit table. Each event includes the previous event hash and its own SHA-256 hash. The read API recomputes the chain and returns `chain_valid`.

This is tamper-evident inside the application boundary, not an external transparency log. An attacker with full control of both application code and the database file could rebuild the store and recompute hashes. A production deployment should sign or externally anchor periodic checkpoints.
