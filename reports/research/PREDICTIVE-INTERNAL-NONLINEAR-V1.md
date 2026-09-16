# Predictive internal nonlinear V1

`EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD` — `H-PRED-INT-002` / `INTERNAL_HGBR_DUAL_HEAD_V1`, the reserved second configuration of `PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1`.

Terminal classification: **NO_ADVANCE_INTERNAL_HGBR_V1**. Stage-1 budget consumed: 2 of 2; family status `CLOSED_BOTH_PREDECLARED_CONFIGURATIONS_EXECUTED`.

## Coverage ruling, recorded before execution

Research Director option taken: **OPTION_1_EXECUTE_UNCHANGED**. The reserved configuration was executed exactly as frozen, with the feature set, the feature-validity rules and the coverage thresholds unchanged. The two coverage conditions were known before execution to be unpassable on this substrate, because the candidate abstains on exactly the timestamps the linear configuration abstained on. The ruling waives nothing: all five conditions remain all-must-hold, so no directional result can produce formal advancement while coverage fails.

## Candidate against the matched control

Pooled candidate win rate **0.4896** on 48951 actionable predictions at coverage 0.93570 over 52315 eligible decision timestamps, with 3362 counted abstentions and 2 declared sides on NEUTRAL truth.

Matched `ALWAYS_UP` on the identical timestamps: **0.5239**. Primary delta **-0.0343** against a minimum important effect of +0.015.

Paired 97.5% paired fold stratified moving block bootstrap interval [-0.0575, -0.0100] from 10000 replicates of 48h blocks at seed 20260916, alpha 0.025.

The canonical full-universe reference bar is 0.5262 (`ALWAYS_UP`, PREDICTIVE-BASELINES-V1, unchanged).

## Per fold

| fold | eligible | actionable | abstentions | coverage | candidate | matched ALWAYS_UP | delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 8673 | 7664 | 1008 | 0.88366 | 0.4933 | 0.5236 | -0.0303 |
| 2020 | 8713 | 7484 | 1229 | 0.85895 | 0.4114 | 0.5886 | -0.1772 |
| 2021 | 8699 | 7742 | 957 | 0.88999 | 0.5061 | 0.5081 | -0.0021 |
| 2022 | 8737 | 8737 | 0 | 1.00000 | 0.4893 | 0.4692 | +0.0201 |
| 2023 | 8733 | 8565 | 168 | 0.98076 | 0.5041 | 0.5243 | -0.0202 |
| 2024 | 8760 | 8759 | 0 | 0.99989 | 0.5246 | 0.5372 | -0.0126 |

## Against the linear configuration

Descriptive only — `DESCRIPTIVE_NOT_A_PREREGISTERED_TEST`. The linear configuration was replayed in this run on the same feature cache with 18 replayed fits that consume no Stage-1 budget, and it reproduced its committed result exactly (`independent_reconciliation: PASS`).

| quantity | linear | nonlinear |
| --- | --- | --- |
| pooled win rate | 0.4888 | 0.4896 |
| pooled coverage | 0.93570 | 0.93570 |
| matched delta | -0.0351 | -0.0343 |
| Brier score | 0.2534 | 0.2546 |
| magnitude MAE pp | 2.3042 | 2.4081 |

The two configurations declared a side on the same 48953 timestamps (identical declared sets: true) and agreed on 39038 of them, an agreement rate of 0.7975.

| fold | linear delta | nonlinear delta | linear coverage | nonlinear coverage |
| --- | --- | --- | --- | --- |
| 2019 | -0.0472 | -0.0303 | 0.88366 | 0.88366 |
| 2020 | -0.1555 | -0.1772 | 0.85895 | 0.85895 |
| 2021 | +0.0009 | -0.0021 | 0.88999 | 0.88999 |
| 2022 | +0.0417 | +0.0201 | 1.00000 | 1.00000 |
| 2023 | -0.0487 | -0.0202 | 0.98076 | 0.98076 |
| 2024 | -0.0169 | -0.0126 | 0.99989 | 0.99989 |

## Calibration

Pooled Brier score **0.2546**.

| bin | count | mean predicted | empirical correct |
| --- | --- | --- | --- |
| [0.0,0.1) | 0 | n/a | n/a |
| [0.1,0.2) | 0 | n/a | n/a |
| [0.2,0.3) | 0 | n/a | n/a |
| [0.3,0.4) | 0 | n/a | n/a |
| [0.4,0.5) | 0 | n/a | n/a |
| [0.5,0.6) | 44181 | 0.5349 | 0.4887 |
| [0.6,0.7) | 4759 | 0.6300 | 0.4974 |
| [0.7,0.8) | 11 | 0.7063 | 0.8182 |
| [0.8,0.9) | 0 | n/a | n/a |
| [0.9,1.0] | 0 | n/a | n/a |

## Magnitude

Signed 24h return MAE **2.4081 pp** (240.81 bps), median absolute error 1.6135 pp, over 48953 feature-available rows; 3362 abstained rows declare no magnitude and are excluded and counted.

Signed magnitude-match mean **-0.22** over 48070 included records; exclusions `ABSTAINED_MAGNITUDE` 880, `NEAR_ZERO_BOTH` 1, `NEUTRAL_REALIZED` 2.

## Advancement gate

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| `POOLED_COVERAGE_AT_LEAST_0_95` | 0.95 | 0.93570 | no |
| `EVERY_FOLD_COVERAGE_AT_LEAST_0_90` | 0.9 | 0.85895 | no |
| `POOLED_MATCHED_DELTA_AT_LEAST_MESI` | 0.015 | -0.03434 | no |
| `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO` | 0.0 | -0.05751 | no |
| `AT_LEAST_4_OF_6_FOLD_DELTAS_NON_NEGATIVE` | 4 | 1.00000 | no |

Failed conditions: `POOLED_COVERAGE_AT_LEAST_0_95`, `EVERY_FOLD_COVERAGE_AT_LEAST_0_90`, `POOLED_MATCHED_DELTA_AT_LEAST_MESI`, `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO`, `AT_LEAST_4_OF_6_FOLD_DELTAS_NON_NEGATIVE`. Secondary calibration or magnitude performance cannot rescue a failed primary directional gate, and no tuned descendant is authorized.

## Features and fits

`PREDICTIVE_INTERNAL_CAUSAL_FEATURES_V1`, 18 causal features, identical to the linear configuration: `logret_1h`, `logret_6h`, `logret_24h`, `logret_72h`, `logret_168h`, `rv_6h`, `rv_24h`, `rv_72h`, `rv_168h`, `signed_efficiency_24h`, `signed_efficiency_72h`, `signed_efficiency_168h`, `up_fraction_24h`, `up_fraction_168h`, `close_position_24h`, `close_position_168h`, `log_volume_relative_24h`, `log_volume_regime_24_168h`.

59217 available vectors, 5106 unavailable and typed: `LOOKBACK_BAR_INCOMPLETE` 1959, `LOOKBACK_BAR_MISSING` 3147, `NEGATIVE_VOLUME` 0, `NON_FINITE_FEATURE` 0, `NON_POSITIVE_CLOSE` 0, `NON_POSITIVE_MEAN_VOLUME` 0.

Model fits 18: 6 direction base, 6 training-only Platt calibration, 6 magnitude. No hyperparameter search, no threshold search, no feature search.

## Accounting

Stage-1 family `CLOSED_BOTH_PREDECLARED_CONFIGURATIONS_EXECUTED`. Sealed queries 0. Champion NONE. Real money false. External information family false. Post-cutoff market data false. PREDICTIVE-BASELINES-V1 and PREDICTIVE-INTERNAL-STRUCTURE-V1 results unchanged.
