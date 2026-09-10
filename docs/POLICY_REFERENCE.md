# Policy reference

Domain policy is explicit and versioned in code. Scores support decisions but never override hard rules.

## Ticket triage — `ticket-triage-v2.1`

- Supported actions: `route_ticket`, `close_ticket`.
- A credible `ticket_topic` claim from a registered support source is required.
- Routing requires a destination and ticket text.
- A proposed route that disagrees with the strongest ticket-topic evidence returns `ask`.
- Closing a VIP or safety-related ticket escalates.

## Refund approval — `refund-approval-v2.2`

- Supported action: `refund`.
- Credible `payment_settled`, `order_exists`, `chargeback_open`, `legal_hold`, and `customer_risk` claims are required; duplicate-charge refunds additionally require a credible `duplicate_charge` claim.
- Amount must be a finite JSON number greater than zero; string/NaN/Infinity values are refused. Currency and reason must be supplied.
- Legal holds, open chargebacks, and authoritative evidence that the order does not exist are hard refusals.
- Unsettled payment state returns `defer`.
- A duplicate-charge refund contradicted by the resolved ledger fact escalates.
- Refunds above $500 exceed autonomous authority and escalate.
- Refunds above $5,000 additionally require senior finance review.

## Code deploy — `code-deploy-v2.1`

- Supported action: `deploy`.
- Credible `ci_status`, `target_environment`, `rollback_available`, `change_risk`, `database_migration`, and `incident_active` claims are required from registered sources.
- Failed CI is a hard refusal.
- A deployment-manifest target mismatch is a hard refusal.
- An irreversible database migration without a backup is a hard refusal.
- Running or pending CI returns `defer`.
- High-risk changes and unapproved deploys during an active incident escalate.

## Cross-domain precedence

```text
hard refusal
    ↓
authoritative evidence conflict → escalate
    ↓
missing / unresolved fact → ask
    ↓
pending truth → defer
    ↓
authority or impact boundary → escalate
    ↓
residual risk / confidence safety net → escalate
    ↓
execute
```

## Cross-domain actor authority

Before a domain result can execute, the server-side actor registry verifies that the proposing agent is registered for the requested domain/action pair and environment. Unknown actors or cross-domain capability violations are hard authorization failures and return `refuse`. Caller-supplied role or confidence fields cannot grant authority.
