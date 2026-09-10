# Architecture snapshot

ActionGate sits between an AI agent and any consequential tool. The agent proposes an action; ActionGate turns the proposal into a deterministic decision using domain policy and observable signals. It does not let an LLM own the final execution boundary.

```text
Agent / caller
    |
    v
Proposed action + context
    |
    v
Policy contract -------- policy version + required claims
    |
    v
Evidence analyzer
    |
    +--> source trust / typed claim values / freshness / conflicts
    |
    v
Actor authorization + domain assessment
    |
    +--> capability boundary / hard rules / reversibility / cost of error
    |
    v
Signal engine
    |
    +--> confidence
    +--> risk
    +--> evidence strength
    +--> reversibility
    +--> cost of error
    +--> missing information
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
Hash-chained audit trail
```

## Decision precedence

1. **refuse** — a hard policy boundary is violated.
2. **escalate** — authoritative evidence conflicts on a consequential action.
3. **ask** — a required fact is missing and can be supplied now.
4. **defer** — the needed fact does not exist yet but is expected to arrive.
5. **escalate** — the action may be legitimate but exceeds autonomous authority/risk limits.
6. **execute** — required evidence exists, no hard boundary is triggered, and residual risk is acceptable.

## Why this split exists

The five outcomes are not labels over one confidence threshold. They encode different operational responses. Missing information is not the same as pending information; a high-impact action is not the same as a prohibited action. The engine keeps those distinctions explicit so downstream systems know what to do next.

## Audit model

Each decision writes five append-only events:

1. `input_received`
2. `evidence_analyzed`
3. `domain_assessed`
4. `signals_computed`
5. `decision_emitted`

Every event contains the previous event hash and its own SHA-256 hash. The demo verifies the chain when the audit trail is loaded.

### Audit integrity boundary

The local SHA-256 chain detects mutation when stored hashes are not recomputed. It is not a cryptographic transparency log against an attacker who fully controls the database and can rewrite the entire chain. A production design would anchor hashes outside the writable audit store or sign checkpoints with an external key.
