# Predictive internal structure V1

`EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD` — `H-PRED-INT-001` / `INTERNAL_LINEAR_DUAL_HEAD_V1`, the first result-bearing experiment of `PREDICTIVE_RESEARCH_GENERATION_V1`.

Terminal classification: **NO_ADVANCE_INTERNAL_LINEAR_V1**. Stage-1 budget consumed: 1 of 2.

## Candidate against the matched control

Pooled candidate win rate **0.4888** on 48951 actionable predictions at coverage 0.93570 over 52315 eligible decision timestamps, with 3362 counted abstentions and 2 declared sides on NEUTRAL truth.

Matched `ALWAYS_UP` on the identical timestamps: **0.5239**. Primary delta **-0.0351** against a minimum important effect of +0.015.

Paired 97.5% paired fold stratified moving block bootstrap interval [-0.0608, -0.0080] from 10000 replicates of 48h blocks at seed 20260916, alpha 0.025.

The canonical full-universe reference bar is 0.5262 (`ALWAYS_UP`, PREDICTIVE-BASELINES-V1, unchanged).

## Per fold

| fold | eligible | actionable | abstentions | coverage | candidate | matched ALWAYS_UP | delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 8673 | 7664 | 1008 | 0.88366 | 0.4764 | 0.5236 | -0.0472 |
| 2020 | 8713 | 7484 | 1229 | 0.85895 | 0.4331 | 0.5886 | -0.1555 |
| 2021 | 8699 | 7742 | 957 | 0.88999 | 0.5090 | 0.5081 | +0.0009 |
| 2022 | 8737 | 8737 | 0 | 1.00000 | 0.5108 | 0.4692 | +0.0417 |
| 2023 | 8733 | 8565 | 168 | 0.98076 | 0.4757 | 0.5243 | -0.0487 |
| 2024 | 8760 | 8759 | 0 | 0.99989 | 0.5203 | 0.5372 | -0.0169 |

## Calibration

Pooled Brier score **0.2534**.

| bin | count | mean predicted | empirical correct |
| --- | --- | --- | --- |
| [0.0,0.1) | 0 | n/a | n/a |
| [0.1,0.2) | 0 | n/a | n/a |
| [0.2,0.3) | 0 | n/a | n/a |
| [0.3,0.4) | 0 | n/a | n/a |
| [0.4,0.5) | 0 | n/a | n/a |
| [0.5,0.6) | 45399 | 0.5359 | 0.4847 |
| [0.6,0.7) | 3458 | 0.6276 | 0.5359 |
| [0.7,0.8) | 89 | 0.7232 | 0.7303 |
| [0.8,0.9) | 5 | 0.8109 | 1.0000 |
| [0.9,1.0] | 0 | n/a | n/a |

## Magnitude

Signed 24h return MAE **2.3042 pp** (230.42 bps), median absolute error 1.5308 pp, over 48953 feature-available rows; 3362 abstained rows declare no magnitude and are excluded and counted.

Signed magnitude-match mean **-1.12** over 48004 included records; exclusions `ABSTAINED_MAGNITUDE` 940, `NEAR_ZERO_BOTH` 7, `NEUTRAL_REALIZED` 2.

## Advancement gate

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| `POOLED_COVERAGE_AT_LEAST_0_95` | 0.95 | 0.93570 | no |
| `EVERY_FOLD_COVERAGE_AT_LEAST_0_90` | 0.9 | 0.85895 | no |
| `POOLED_MATCHED_DELTA_AT_LEAST_MESI` | 0.015 | -0.03514 | no |
| `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO` | 0.0 | -0.06080 | no |
| `AT_LEAST_4_OF_6_FOLD_DELTAS_NON_NEGATIVE` | 4 | 2.00000 | no |

Failed conditions: `POOLED_COVERAGE_AT_LEAST_0_95`, `EVERY_FOLD_COVERAGE_AT_LEAST_0_90`, `POOLED_MATCHED_DELTA_AT_LEAST_MESI`, `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO`, `AT_LEAST_4_OF_6_FOLD_DELTAS_NON_NEGATIVE`. Secondary calibration or magnitude performance cannot rescue a failed primary directional gate, and no tuned descendant is authorized.

## Features and fits

`PREDICTIVE_INTERNAL_CAUSAL_FEATURES_V1`, 18 causal features: `logret_1h`, `logret_6h`, `logret_24h`, `logret_72h`, `logret_168h`, `rv_6h`, `rv_24h`, `rv_72h`, `rv_168h`, `signed_efficiency_24h`, `signed_efficiency_72h`, `signed_efficiency_168h`, `up_fraction_24h`, `up_fraction_168h`, `close_position_24h`, `close_position_168h`, `log_volume_relative_24h`, `log_volume_regime_24_168h`.

59217 available vectors, 5106 unavailable and typed: `LOOKBACK_BAR_INCOMPLETE` 1959, `LOOKBACK_BAR_MISSING` 3147, `NEGATIVE_VOLUME` 0, `NON_FINITE_FEATURE` 0, `NON_POSITIVE_CLOSE` 0, `NON_POSITIVE_MEAN_VOLUME` 0.

Model fits 18: 6 direction base, 6 training-only Platt calibration, 6 magnitude. No hyperparameter search, no threshold search, no feature search.

## Accounting

Sealed queries 0. Champion NONE. Real money false. External information family false. Post-cutoff market data false. PREDICTIVE-BASELINES-V1 results unchanged.
