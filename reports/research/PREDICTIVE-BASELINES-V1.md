# Predictive baselines V1 — reference report

Classification: **baseline reference report, not an experiment result.** No hypothesis was
tested, no model was fitted, no candidate was created, and no Champion exists. The machine
readable record is `reports/research/PREDICTIVE-BASELINES-V1.json`; the protocol frozen
before any number below was computed is `research/protocols/PREDICTIVE-BASELINES-V1.json`.

Scoring follows `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md` as amended by
Amendment A1 ([ADR-0027](../../decisions/ADR-0027-BASELINE-PROBABILITY-SEMANTICS-AND-METRIC-APPLICABILITY.md)),
which was recorded before these baselines touched market data.

## Label accounting

Target `r_24h = log(close[T + 24h] / close[T])` on the canonical hourly decision grid.

| Quantity | Count |
| --- | ---: |
| Grid decision instants | 64,652 |
| Admissible labels | 64,323 |
| Excluded, typed | 329 |
| `DECISION_BAR_MISSING` | 127 |
| `DECISION_BAR_INCOMPLETE` | 31 |
| `HORIZON_BAR_BEYOND_COVERAGE` | 24 |
| `HORIZON_BAR_MISSING` | 118 |
| `HORIZON_BAR_INCOMPLETE` | 29 |
| `NON_POSITIVE_PRICE` | 0 |

The accounting closes exactly: 64,323 + 329 = 64,652. Canonical gaps produce inadmissible
labels; nothing is interpolated and no nearest-bar substitution exists.

Direction truth over admissible labels: **UP 33,637**, **DOWN 30,681**, **NEUTRAL 5**. The
five exactly-flat 24h windows are counted here, excluded from directional scoring, and never
counted as wins.

## Fold design

Expanding chronological walk-forward over calendar years, purge and embargo 24h — one full
label horizon — on both sides of every boundary. Random K-fold is not implemented.

| Fold | Training labels | Eligible decision timestamps |
| --- | ---: | ---: |
| 2019 | 11,846 | 8,673 |
| 2020 | 20,542 | 8,713 |
| 2021 | 29,278 | 8,699 |
| 2022 | 38,000 | 8,737 |
| 2023 | 46,760 | 8,733 |
| 2024 | 55,516 | 8,760 |

Eligible total **52,315**. The remaining admissible labels are 11,893 in the pre-2019 warmup
training block and 115 removed by the fold-boundary embargo. 52,315 + 11,893 + 115 = 64,323.

Every baseline is scored on this identical eligible universe; they differ only in how often
they abstain.

## Pooled baseline results

| Baseline | Declares | Win rate | Coverage | Actionable | Moving-block 95% | Naive Wilson 95% (optimistic) |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `TRAINING_UP_BASE_RATE` | direction + probability | 0.5262 | 0.99996 | 52,313 | [0.5109, 0.5412] | [0.5219, 0.5305] |
| `ALWAYS_UP` | direction | 0.5262 | 0.99996 | 52,313 | [0.5109, 0.5412] | [0.5219, 0.5305] |
| `PREVIOUS_24H_SIGN_PERSISTENCE` | direction | 0.4667 | 0.99845 | 52,234 | [0.4547, 0.4792] | [0.4624, 0.4709] |
| `ZERO_RETURN_MAGNITUDE` | magnitude | — | — | — | — | — |

`TRAINING_UP_BASE_RATE` calibration: Brier **0.24972**. Its reliability table populates a
single bin, `[0.5,0.6)`, with 52,313 records, mean predicted probability 0.5215 against an
empirical frequency correct of 0.5262. A constant predictor has nothing to calibrate across;
this is a reference point for a real probabilistic model, not evidence of calibration
quality.

`ALWAYS_UP` and `PREVIOUS_24H_SIGN_PERSISTENCE` declare `probability: null`
(`PROBABILITY_NOT_DECLARED`) and receive no Brier score and no reliability table, per
Amendment A1 §5.2.

`ZERO_RETURN_MAGNITUDE` declares no direction (`DIRECTION_NOT_DECLARED`) and so has no win
rate and no coverage. MAE **2.2635 percentage points** (226.35 bps), median absolute error
1.4599 percentage points. Its signed magnitude-match aggregate is undefined by construction:
all 52,315 records are excluded, 52,056 as `ABSTAINED_MAGNITUDE` and 259 as
`NEAR_ZERO_BOTH`, and the counts are reported rather than suppressed.

## By fold

| Fold | `TRAINING_UP_BASE_RATE` p_up / win / Brier | `ALWAYS_UP` win | `PREV_24H_SIGN` win / coverage | `ZERO_RETURN` MAE pp |
| --- | --- | ---: | --- | ---: |
| 2019 | 0.5095 / 0.5219 / 0.2497 | 0.5219 | 0.4593 / 0.9961 | 2.3168 |
| 2020 | 0.5148 / 0.5807 / 0.2478 | 0.5807 | 0.4746 / 0.9972 | 2.2925 |
| 2021 | 0.5335 / 0.5218 / 0.2497 | 0.5218 | 0.4676 / 0.9978 | 3.1985 |
| 2022 | 0.5313 / 0.4692 / 0.2529 | 0.4692 | 0.4687 / 1.0000 | 2.3059 |
| 2023 | 0.5196 / 0.5264 / 0.2493 | 0.5264 | 0.4585 / 0.9998 | 1.5204 |
| 2024 | 0.5204 / 0.5372 / 0.2489 | 0.5372 | 0.4711 / 0.9998 | 1.9519 |

2022 is reported exactly like every other fold: `ALWAYS_UP` loses there, 0.4692.

## What these numbers mean, and what they do not

**The reference bar for direction is ~0.526, not 0.500.** Over 2019–2024 the 24h UP rate on
this grid is 52.6%, so a predictor that reaches 53% has demonstrated nothing. The relevant
comparison is against `ALWAYS_UP`, not against a coin.

**`TRAINING_UP_BASE_RATE` and `ALWAYS_UP` are numerically identical here.** The training
majority was UP in all six folds (p_up 0.5095–0.5335), so the fitted baseline declared UP
every time. They differ only in that one declares a probability and is therefore calibrated.
The Amendment A1 tie rule was never exercised, and the `DOWN`-majority branch — the case the
amendment exists to get right — was never reached on this data. It remains proven by test,
not by this run.

**Persistence is below 50% in every single fold**, pooled 0.4667 with a moving-block interval
of [0.4547, 0.4792] that excludes 0.5 comfortably. At a 24h horizon on hourly decisions, the
trailing 24h sign is a consistently *anti*-predictive signal over this period. Its inverse
would score ~0.533 — and inverting it now would be exactly the result-driven adaptation this
protocol forbids. It is recorded as an observation and nothing is built on it.

**The dependence correction is not cosmetic.** On the pooled series the moving-block interval
is roughly 3.5× wider than the naive Wilson interval (0.0304 versus 0.0086 for `ALWAYS_UP`).
Treating 52,315 overlapping 24h labels as independent would have understated uncertainty by
that factor, and would have made a ~1pp edge look decisive.

**Magnitude is the harder problem.** Predicting zero gives an MAE of 2.26 percentage points
with a median of 1.46, and the fold spread is wide — 1.52 in 2023 against 3.20 in 2021. Any
magnitude model must beat this while being scored on the same universe.

## Boundaries

Model fits 0. Optimizer or parameter search: none. External data: none. Sealed queries 0.
Post-cutoff market data: none. Champion `NONE`. Real money `false`. No baseline was promoted
to a candidate. Thresholds, folds, bins, block length and seed were frozen before any number
here existed and were not revised afterwards.
