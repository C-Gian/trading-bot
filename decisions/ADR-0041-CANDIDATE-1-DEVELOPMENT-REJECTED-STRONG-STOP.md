# ADR-0041 — Candidate #1 Development rejected; project enters STRONG_STOP_PENDING_ASTRA

Status: ACCEPTED — Research Director, 2026-09-25

## Basis

The single frozen Candidate #1 Development execution authorized by ADR-0040 produced:

- result: `research/experiments/CANDIDATE-1-DEVELOPMENT-V1/result.json`;
- canonical result sha256: `4a5d6f39d4c41157a12b79b3f38d9122e3ed0f4d99e38bd6cfce4d7d3dc7e866`;
- deterministic replay: PASS;
- protocol identity: PASS;
- implementation identity: PASS;
- admission identity replay: PASS;
- source/execution coverage: 116/116 Candidate trades and 101/101 matched pairs scorable;
- no new market data, no post-cutoff/sealed access, sealed queries 0.

The mechanical disposition is `DEVELOPMENT_REJECTED`.

Primary economic evidence:

- gross Candidate expectancy: approximately -3.03 bp/trade;
- net Candidate expectancy: `ABS_NET_BP = -27.03` bp/trade;
- incremental Candidate-minus-control expectancy:
  `INCREMENTAL_NET_BP = -17.47` bp/matched pair;
- annual absolute means are negative in 2022, 2023 and 2024;
- incremental annual means are negative in 2022 and 2023 and approximately flat in 2024;
- all twelve frozen Development gates fail;
- prospective detectability fails for both claims (required N 461 absolute / 1751 incremental
  versus 35 conservative annual Candidate arrivals).

Robustness does not rescue the result:

- cost-stress absolute net expectancy remains negative;
- delay-stress absolute and incremental expectancy remain negative;
- top-three-winner removal leaves absolute and incremental expectancy more negative;
- Candidate ES10 is worse than matched control;
- maximum cumulative fixed-notional drawdown exceeds the frozen risk limit.

## Research Director adjudication

Accept `DEVELOPMENT_REJECTED` as the valid terminal Candidate #1 Development disposition.

This is not a borderline or underpowered positive result. The frozen Candidate #1 formulation fails
both absolute and incremental economic questions, and its gross expectancy is already slightly
negative before the frozen transaction-cost convention.

No implementation or source defect has been identified that invalidates the scientific execution.
The post-run schema/tooling fixes described by the executor concern governance compatibility and
legacy-format recognition; they do not alter the frozen population, matching, execution prices,
payoff calculation or result.

Candidate #1 is therefore **closed under the current allocation**.

## Interpretation boundary

This decision establishes only that the frozen Candidate #1 proposition did not earn further budget:

> Within the admitted 2022-2024 sharp-sell-off population, the frozen conjunction of OI quantity
> contraction and traded perpetual-relative weakness did not identify a materially better ~4h BTC
> spot LONG payoff than the matched price-only comparison under the frozen execution semantics.

It does **not** prove that all deleveraging, positioning, mean-reversion or temporary-pressure
mechanisms are impossible.

It does forbid ordinary rescue of this Candidate through:

- another holding horizon;
- a different sell-off threshold;
- a stronger/weaker OI threshold;
- a different relative-price threshold;
- stop/target optimization;
- funding/flow/volume/news/technical filters;
- cheaper historical costs;
- favorable subperiod/subgroup selection;
- a new learner/model on the same proposition.

Any reopening requires Astra under the V2 strategic policy.

## Project-level consequence

Per Astra Directive V2 and `RESEARCH_STAGE_POLICY_V1`, exhaustion of the current one-card allocation
without promotion moves the project to:

`STRONG_STOP_PENDING_ASTRA`

Candidate Card #2 remains unallocated.

No new alpha-development experiment, source acquisition, R&D branch, prospective confirmation or
replacement candidate is authorized.

The next action is strategic review by Astra: decide whether to park active alpha research under the
current BTC spot LONG/NO_TRADE/public-data envelope or authorize one specifically justified remaining
allocation. The default presumption is parking unless a genuinely distinct, feasible case has
superior expected information value.

Champion remains NONE. Sealed queries remain 0. Real money remains false.
