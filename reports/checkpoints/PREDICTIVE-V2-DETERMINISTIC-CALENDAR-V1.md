# Checkpoint — PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1

Status: **COMPLETE — REJECTED_DEVELOPMENT_NO_SEALED**.

Starting HEAD `7bba31220f746c92b2eab0302ccc7fb35604584f`. The first Generation V2
market-model family executed exactly the two preregistered configurations on all frozen annual
development folds 2019–2024. Neither advanced. No sealed or post-cutoff data was accessed;
sealed queries remain 0, Champion remains `NONE`, real money remains `false`, and magnitude
remains `DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`.

## Pre-result freeze and feature proofs

Research Director decision: [ADR-0029](../../decisions/ADR-0029-PREDICTIVE-V2-DETERMINISTIC-CALENDAR.md).
Pre-result commit: `5cc4f153f37b0b200b46834e0b714498164889fc`. It contains the immutable
decision, feature contract, implementation, proof tests, search plan, both preregistrations and
admission; it contains 0 fits and 0 outer predictions.

Admission identity: `91f47e036408b19c3023c508f61530bdcfba53525955566a16c2334b2bf97bcf`.
Search plan SHA-256 `b99674c11839914a41623ee762476a3655d92383510707166e1058f967d086da`;
linear preregistration `c26ddf0fa234254fe6ad00d547a93d3ade3ff3ef756f16d4e7e54d45944d9336`;
HGBR preregistration `438ec56f81457078c47e2fa835ff3657956d0c9f3838db40c24c81696f57d546`;
feature contract `c0374dad1e8dbf3333c91a1e9b9ac9c41381aad94238caa9d9e4d762d5055337`.

The exact ordered feature set is `UTC_HOUR_SIN`, `UTC_HOUR_COS`, `UTC_WEEKDAY_SIN`,
`UTC_WEEKDAY_COS`, `UTC_YEAR_PHASE_SIN`, `UTC_YEAR_PHASE_COS`, `UTC_WEEKEND`. It is a pure
function of aware UTC `T`; market mutation independence, one-hour movement, hour/weekday
boundaries, Dec 31/Jan 1 wrap, Feb 28/29 leap behaviour, non-UTC rejection and local-time/DST
independence all pass. All 64,323 admissible development labels and all 52,315 outer-fold
timestamps produced valid vectors: feature validity 1.0.

## Frozen procedures

`V2_CALENDAR_LINEAR_V1` used `StandardScaler + LogisticRegression` with the frozen L2
parameters. `V2_CALENDAR_HGBR_V1` used the frozen `HistGradientBoostingClassifier` parameters
and seed 20260921. Each fold used expanding chronological training, the frozen 24h
purge/embargo, chronological 80% base fit / 20% calibration, a 48h calibration embargo, and a
training-only unpenalized logistic Platt map on the raw decision score. Each configuration
consumed 12 fits (6 base classifiers and 6 calibrators); family total 24. No hyperparameter,
feature or threshold search occurred. Exactly `p_up >= 0.60` acted `LONG`.

## Pooled results

| configuration | LONG N | coverage | LONG win rate | full-fold UP rate | enrichment | 97.5% paired interval | Brier / control | mean p / gap |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Linear | 3,567 | 0.068183 | 0.526773 | 0.526179 | +0.000594 | [-0.059920, 0.063978] | 0.253061 / 0.249722 | 0.614925 / 0.088152 |
| HGBR | 2,847 | 0.054420 | 0.529680 | 0.526179 | +0.003501 | [-0.062663, 0.071984] | 0.253734 / 0.249722 | 0.606307 / 0.076627 |

Both 10,000-replicate, 48h fold-stratified paired bootstraps retained all replicates: 0
discarded, share 0.0, support `STABLE`.

## Per-fold results

| configuration | fold | LONG N | coverage | win rate | full-fold UP | enrichment |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Linear | 2019 | 0 | 0.000000 | n/a | 0.521910 | n/a |
| Linear | 2020 | 37 | 0.004247 | 0.486486 | 0.580741 | -0.094255 |
| Linear | 2021 | 3,530 | 0.405794 | 0.527195 | 0.521784 | +0.005411 |
| Linear | 2022 | 0 | 0.000000 | n/a | 0.469154 | n/a |
| Linear | 2023 | 0 | 0.000000 | n/a | 0.526394 | n/a |
| Linear | 2024 | 0 | 0.000000 | n/a | 0.537162 | n/a |
| HGBR | 2019 | 0 | 0.000000 | n/a | 0.521910 | n/a |
| HGBR | 2020 | 0 | 0.000000 | n/a | 0.580741 | n/a |
| HGBR | 2021 | 2,847 | 0.327279 | 0.529680 | 0.521784 | +0.007896 |
| HGBR | 2022 | 0 | 0.000000 | n/a | 0.469154 | n/a |
| HGBR | 2023 | 0 | 0.000000 | n/a | 0.526394 | n/a |
| HGBR | 2024 | 0 | 0.000000 | n/a | 0.537162 | n/a |

The full report preserves the fixed V1 actionable-LONG reliability bins. For both
configurations gates 1 (pooled coverage) and 3 (pooled N) passed; gates 2 and 4–10 failed:
per-fold coverage, per-fold N, pooled 0.60 win rate, +0.05 enrichment, positive interval lower
bound, four non-negative folds, Brier no worse than training base rate, and action calibration
gap <= 0.05. Classifications are `NO_ADVANCE_V2_CALENDAR_LINEAR_V1` and
`NO_ADVANCE_V2_CALENDAR_HGBR_V1`; both are `NOT_ELIGIBLE_REJECTED_DEVELOPMENT`.

## Closure and integrity

The two-configuration search budget is fully consumed with 0 remaining and 0 result-dependent
forks. Family disposition is `REJECTED_DEVELOPMENT_NO_SEALED`. All ten Generation V1 result
artifacts, the macro source block and the residual source finding remain byte-identical; no V1
probability score, tail, reliability bin or action reconstruction was used. The complete family
and trial artifacts replay byte-identically from installed development data.

Next: `RESEARCH_DIRECTOR_REVIEW_PREDICTIVE_V2_DETERMINISTIC_CALENDAR_V1`; no second V2 family
is authorized automatically.
