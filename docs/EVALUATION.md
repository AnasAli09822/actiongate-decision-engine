# Evaluation

`python scripts/evaluate.py` runs a fixed synthetic decision suite across the three domains and all five outcomes.

Current suite: 14 cases.

```text
exact decision accuracy: 14/14 (100.0%)
unsafe execute rate:     0/11 (0.0%)
unnecessary block rate:  0/3  (0.0%)
```

Outcome distribution:

```text
execute   3
ask       3
defer     2
escalate  3
refuse    3
```

The suite includes clear low-risk actions, missing facts, pending payment and CI state, high-value financial actions, unsupported evidence, failed CI, target mismatch, nonexistent orders, and the deliberate authoritative-evidence conflict.

These numbers describe only this repository's defined synthetic suite. They are not a production accuracy claim and the confidence score is not statistically calibrated.

The safety-oriented metric is **unsafe execute rate**: among cases whose expected outcome is not `execute`, how often did the engine execute anyway? The separate **unnecessary block rate** prevents a system from appearing safe simply by refusing everything.
