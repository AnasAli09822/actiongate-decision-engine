# Threat model

The proposing agent may be wrong, overconfident, incomplete, or compromised. The decision boundary therefore treats the agent proposal as a request, not as authorization.

| Failure or abuse case | Control |
|---|---|
| Agent reports high confidence despite contradictory records | Agent-reported confidence is not an authority signal; evidence conflicts are evaluated independently. |
| Agent assigns itself a trusted source score | Request schema does not accept reliability, authority, or freshness scores. Source trust is server-controlled. |
| Agent uses an unknown source name | Unknown sources are rejected. |
| Agent labels a support record as payment-ledger evidence | Source-kind allowlists reject the mismatch. |
| Evidence is stale | Freshness is computed from `observed_at`; evidence beyond the source's maximum age is rejected. |
| Agent omits required evidence | Missing evidence kinds are surfaced explicitly and autonomous execution is blocked. |
| Context says CI passed while CI evidence says failed | The registered CI source resolves the fact; failed CI triggers a hard refusal. |
| Numerical scores drift high | Hard rules run before score-based safety nets. |
| Decision record is edited through the application database path | SQLite triggers reject updates and deletes. |
| Audit storage is modified after those guards are bypassed | SHA-256 chain verification detects the modified event. |

## Trust boundary

The challenge service stops at the decision result. It does not call Stripe, GitHub deployment APIs, or a support platform. In a production executor, the downstream tool gateway should accept only the exact action and parameters authorized by the decision layer, with a short-lived execution permit to prevent time-of-check/time-of-use drift.

## Known boundary

The public demo accepts structured evidence to make the core mechanic inspectable. It models evidence after an authenticated source adapter has produced it. Cryptographic connector authentication, organization authorization, and signed execution permits are intentionally outside this repository.
