# 90-second walkthrough

**0–12 seconds**  
“Agents are already good at calling tools. The harder problem is deciding whether a consequential action should happen at all. ActionGate sits between an agent proposal and the system it wants to change.”

**12–28 seconds**  
Open **Clear billing ticket** and run it.  
“This action is low risk, highly reversible, and supported by a registered source. The result is `execute`. The response exposes confidence, risk, evidence, missing information, reversibility, cost of error, reason codes, and the exact policy version.”

**28–43 seconds**  
Open **Refund missing a reason**.  
“This is `ask`: the required reason can be supplied now. If the missing truth does not exist yet, that is different.”

**43–55 seconds**  
Open **Production deploy while CI is running**.  
“CI is still running, so the correct control action is `defer` and re-evaluate when CI finishes.”

**55–67 seconds**  
Open **Deploy with failed tests**.  
“Failed CI is a hard policy boundary, so the engine `refuse`s the deploy. Confidence cannot override it.”

**67–90 seconds**  
Open **Failure test: conflicting refund evidence**.  
“The agent is confident, but a CRM note and the payment ledger disagree. Source trust comes from the server, not the agent. Because the conflict touches an authoritative ledger, ActionGate escalates. The full input, evidence resolution, signals, policy reasoning, and outcome are preserved in the verified hash-chained audit trail.”
