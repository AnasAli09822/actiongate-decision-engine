# Policy reference

Domain policy is explicit and versioned in code. Scores support decisions but never override hard rules.

## Ticket triage — `ticket-triage-v2.0`

- Supported actions: `route_ticket`, `close_ticket`.
- Registered `ticket_content` evidence is required.
- Routing requires a destination and ticket text.
- A proposed route that disagrees with the strongest ticket-topic evidence returns `ask`.
- Closing a VIP or safety-related ticket escalates.

## Refund approval — `refund-approval-v2.0`

- Supported action: `refund`.
- Registered payment-ledger and order-record evidence are required.
- Amount must be positive and currency and reason must be supplied.
- Legal holds, open chargebacks, and authoritative evidence that the order does not exist are hard refusals.
- Unsettled payment state returns `defer`.
- A duplicate-charge refund contradicted by the resolved ledger fact escalates.
- Refunds above $500 exceed autonomous authority and escalate.
- Refunds above $5,000 additionally require senior finance review.

## Code deploy — `code-deploy-v2.0`

- Supported action: `deploy`.
- Registered CI results and deployment-manifest evidence are required.
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
pending truth → defer
    ↓
missing / unresolved fact → ask
    ↓
authority or impact boundary → escalate
    ↓
residual risk / confidence safety net → escalate
    ↓
execute
```
