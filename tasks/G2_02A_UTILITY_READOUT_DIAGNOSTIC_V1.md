# G2-02A Utility Readout Diagnostic V1

Status: **AUTHORIZED DIAGNOSTIC — EXISTING EXPOSED CACHE ONLY — NO NEW ECONOMIC RUN**

## Read first

1. `AGENTS.md`
2. `tasks/CURRENT_TASK.md`
3. `reports/reviews/G2-02-RESEARCH-DIRECTOR-REVIEW-V1.md`
4. `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/RESULTS.json`
5. the minimum cached G2-02 records needed for the diagnostic
6. `research/g2/G2_DEVELOPMENT_PROTOCOL_V1.md` §§11, 16-17, 23

Do not bulk-read historical project material.

## Objective

Determine whether the already-fitted G2 utility heads contain useful **ex-ante ranking information**
about their own matured LONG/SHORT standardized shadow NET_R labels.

This task diagnoses the existing G2-02 evidence. It does not revise the system.

## Hard prohibitions

Do not:
- refit any forecast or utility model;
- alter features, penalties, horizon, stop, costs, residual construction or policy;
- choose/test an action threshold;
- simulate a new trading policy;
- recompute G2-02 economics under a changed rule;
- execute R1/R2/R3/RCYCLE;
- read 2025+ market observations;
- use protected data;
- consume a revision slot.

Use the already-frozen G2-02 run/cache identities only.

## Population

For each of:
- G2-V0;
- ABL-G2-01;
- ABL-G2-02;

and separately for LONG and SHORT:

Use scored 2021-2024 decisions where:
- utility prediction was genuinely issued;
- utility evidence was PREQUENTIAL_READY under the frozen run;
- the corresponding shadow NET_R label matured and is available.

Keep exact decision timestamps and fit identity.

## Fixed diagnostics

### 1. Prediction distribution

Report predicted utility:
- min;
- p01;
- p05;
- p10;
- p25;
- p50;
- p75;
- p90;
- p95;
- p99;
- max.

Also report the contemporaneous prudential-margin components:
- predicted utility;
- residual q10;
- resulting margin.

No threshold is selected from these values.

### 2. Fixed prediction deciles

Rank observations by the already-issued predicted utility and split into ten equal-count deciles
D1..D10.

For each decile report:
- count;
- mean and median realized shadow NET_R;
- fraction NET_R > 0;
- p10/p50/p90 realized NET_R;
- stop vs expiry label-exit composition where available.

Deciles are diagnostic bins, not candidate policy thresholds.

### 3. Top-decile uplift

For each system/side report:

`UPLIFT_D10 = mean_NET_R(D10) - mean_NET_R(all eligible)`.

Use the frozen UTC calendar-week block bootstrap:
- 5,000 replicates;
- seed 2026092702;
- complete UTC weeks;
- report point and p10/p50/p90.

Also report the analogous difference in fraction positive.

### 4. Rank stability

Report:
- pooled Spearman rank correlation between predicted utility and realized NET_R (descriptive);
- per-calendar-year Spearman;
- per-UTC-week Spearman distribution: count, p10/p50/p90 and fraction > 0;
- decile-mean monotonicity as Spearman(decile index, decile mean NET_R).

Do not use IID p-values.

### 5. Residual-tail diagnosis

Explain why the utility residual q10 is near -1R.

Report, separately by side:
- residual q10 distribution over time/fits;
- label exit-kind composition of observations contributing to the lower realized-payoff tail;
- fraction of labels at/near stop-loss outcomes;
- whether the q10 magnitude is primarily a consequence of the frozen stop geometry versus large
  model residual dispersion.

This is diagnosis only.

### 6. Cross-system comparison

Apply the exact same diagnostics to G2-V0, ABL-G2-01 and ABL-G2-02.

Do not call an ablation a winner and do not promote it.

The purpose is to see whether the participation/interaction blocks materially alter utility ranking,
not to run an unbudgeted model tournament.

## Predeclared interpretation classes

Classify each side of each system:

`RANKING_SUPPORT`
only if:
- D10 mean realized NET_R > 0; and
- UPLIFT_D10 point > 0; and
- UPLIFT_D10 weekly-block p10 > 0.

`RANKING_NOT_SUPPORTED`
if D10 mean <= 0 or UPLIFT_D10 point <= 0.

`RANKING_MIXED`
otherwise.

These classes do not authorize a trade threshold.

Overall G2-V0 diagnostic:
- `BILATERAL_RANKING_SUPPORT` if LONG and SHORT are both RANKING_SUPPORT;
- `UNILATERAL_OR_MIXED_RANKING` if exactly one side is RANKING_SUPPORT or either is MIXED;
- `NO_UTILITY_RANKING_SUPPORT` otherwise.

## Outputs

Create:
- `reports/diagnostics/G2-02A-UTILITY-READOUT-DIAGNOSTIC-V1.json`;
- `reports/diagnostics/G2-02A-UTILITY-READOUT-DIAGNOSTIC-V1.md`;
- `reports/checkpoints/G2-02A-UTILITY-READOUT-DIAGNOSTIC-V1.md`.

Append an execution record to `research/g2/G2_RESEARCH_LEDGER_V1.jsonl`.

The report must state:
- existing-cache diagnostic only;
- no refit;
- no new policy simulation;
- no threshold selection;
- no revision slot;
- no protected data.

## Validation

Use focused deterministic tests.

This diagnostic should operate from existing cache/artifacts and should not trigger a new
G2-development simulation.

Run a full repository check only if required by the active checkpoint after implementation and
consistent with the permanent executor policy in `AGENTS.md`.

## Completion

Leave:

`EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_G2_02A_REVIEW`

Do not open R1.
