# Design decisions

## The language model does not own the final decision

A model can normalize unstructured intent upstream, but the final decision path is explicit, deterministic, versioned, and testable. This keeps authorization-like control outside probabilistic model output.

## Source trust is not request data

Reliability, authority, permitted evidence kinds, and permitted claims are configuration owned by the decision service. Allowing an agent to submit those values would let a compromised caller inflate or repurpose its own evidence.

## The five outcomes are control states

`ask`, `defer`, `escalate`, and `refuse` are not weaker confidence bands. They encode different operational next steps and are tested independently.

## Evidence conflicts are retained

When credible sources disagree, the conflict remains visible. Authoritative disagreement escalates rather than being averaged into a deceptively clean score.

## Hard policy outranks scores

Failed CI, legal hold, and other terminal boundaries are evaluated before any confidence or risk threshold. A favorable heuristic score cannot override them.

## Audit data is append-only in the application boundary

The repository uses SQLite triggers plus a SHA-256 event chain. This is deliberately simpler than an external transparency log while still making ordinary mutation impossible and direct tampering detectable.

## Typed claim contracts

Evidence values are validated per claim before policy evaluation. The engine intentionally rejects malformed booleans and unknown enum values rather than coercing them, because coercion can invert a safety decision.

## Actor capability registry

Agent identity is not treated as descriptive metadata. The decision service owns a capability registry for domain/action/environment authorization. This keeps authorization distinct from confidence and evidence quality.
