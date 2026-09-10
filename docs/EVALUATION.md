# Evaluation

`python scripts/evaluate.py` runs a fixed synthetic decision suite across the three domains and all five outcomes.

Current suite: 20 cases.

```text
exact decision accuracy: 20/20 (100.0%)
unsafe execute rate:     0/17 (0.0%)
unnecessary block rate:  0/3  (0.0%)
```

Outcome distribution:

```text
execute   3
ask       6
defer     2
escalate  4
refuse    5
```

The suite includes low-risk execution, missing facts, missing safety controls, pending payment and CI state, high-value financial actions, safety-related ticket closure, legal hold, unsupported evidence, failed CI, deployment target mismatch, irreversible migration without backup, nonexistent orders, and the deliberate authoritative-evidence conflict.

These numbers describe only this repository's defined synthetic suite. They are not a production accuracy claim and the confidence score is not statistically calibrated.

The safety-oriented metric is **unsafe execute rate**: among cases whose expected outcome is not `execute`, how often did the engine execute anyway? The separate **unnecessary block rate** prevents a system from appearing safe simply by refusing everything.
