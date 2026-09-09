# Research map

Generated from SEARCH_LEDGER.jsonl, HYPOTHESIS_FAMILIES.json, SEARCH_BUDGET.json and OUTCOMES.jsonl.
DEVELOPMENT RESEARCH - NOT APPROVED STRATEGY PERFORMANCE. Champion NONE.

Reserved: 9 experiments/configurations; 53 evaluation trials; 3 economic core hypotheses. Completed: 6. Sealed queries: 0.

| Root family | Experiments (parent lineage) | Budget consumed / limit | Status and lesson |
|---|---|---|---|
| FAM-REFERENCE | EXP-BASE-001-BUYHOLD | 1/1 experiments; 1/1 trials | REFERENCE_ONLY |
| FAM-RANDOM | EXP-CTRL-002-RANDOM | 1/1 experiments; 32/32 trials | CONTROL_BEHAVES_AS_EXPECTED |
| FAM-TREND | EXP-BASE-003-TREND; EXP-CTRL-005-TREND-DELAY-1H <- EXP-BASE-003-TREND | 2/2 experiments; 4/4 trials | REJECT_COST_DOMINATED; REJECT |
| FAM-BREAKOUT | EXP-BASE-004-BREAKOUT; EXP-ALG-009-ALIGNED <- EXP-BASE-004-BREAKOUT; EXP-ALG-007-REGIME <- EXP-ALG-009-ALIGNED, EXP-BASE-004-BREAKOUT; EXP-ALG-008-PARTICIPATION <- EXP-ALG-009-ALIGNED, EXP-BASE-004-BREAKOUT | 4/4 experiments; 15/15 trials | REJECT_COST_DOMINATED; PREREGISTERED; PREREGISTERED; PREREGISTERED |
| FAM-NO-TRADE | EXP-CTRL-006-NO-TRADE | 1/1 experiments; 1/1 trials | CONTROL_BEHAVES_AS_EXPECTED |

## Legitimate directions and blocked repeats

- FAM-REFERENCE: Reference recomputation requires a new declared data/execution question; never treat endpoint return as a product strategy.
- FAM-RANDOM: New matched eligibility/control question with fixed declared seeds; extra seeds do not create new economic hypotheses.
- FAM-TREND: Immutable diagnostic evidence and a distinct causal structural response; window or stop drift alone is insufficient.
- FAM-BREAKOUT: A fixed orthogonal regime/participation hypothesis responding to observed gross-positive, net-negative and unstable behavior; no numeric search.
- FAM-NO-TRADE: Control changes only when testing changed eligibility or accounting semantics.

Exact behavior and renamed exact behavior are blocked. Parameter-only changes are near duplicates,
with no WP-004 numeric-search allowance. Cost profiles, folds and random seeds are not new mechanisms.
No automatic promotion follows a positive development outcome. See FAILURE_MEMORY.md for falsified
claims and limitations, and the adaptive decision ledger for result-dependent research forks.
