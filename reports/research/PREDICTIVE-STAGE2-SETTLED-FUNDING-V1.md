# Predictive Stage 2 — settled funding structure V1

`PREDICTIVE_STAGE2_SETTLED_FUNDING_FAMILY_V1` — `H-PRED-FUND-001` / `CAUSAL_SETTLED_FUNDING_STRUCTURE_ADDS_24H_DIRECTIONAL_INFORMATION`, the first Stage-2 information family of `PREDICTIVE_RESEARCH_GENERATION_V1`.

Family disposition: **REJECTED_DEVELOPMENT_NO_SEALED**. Configurations executed: 2 of 2; 0 remaining.

## Stage-1 closure, recorded with this checkpoint

`PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1` is **REJECTED_DEVELOPMENT_NO_SEALED**. Linear sealed eligibility `NOT_ELIGIBLE_REJECTED_DEVELOPMENT`; HGBR sealed eligibility `NOT_ELIGIBLE_REJECTED_DEVELOPMENT`. The canonical hourly gaps were not repaired and the 169-bar contiguity rule was not relaxed: the substrate issue is recorded as `DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH`. This rejects the defined two-configuration Stage-1 family, not the proposition that all internal BTCUSDT information is useless.

## Source and availability

`BTCUSDT-USDM-FUNDING-DEV-v1`, 5819 settled records from 2019-09-10T08:00:00Z to 2024-12-31T16:00:00Z, `BINANCE_USDM_FUTURES_PUBLIC_MARKET_DATA`, credential-free. Fields read: `funding_time`, `funding_rate`. Availability rule `FUNDING_TIME_STRICTLY_BEFORE_DECISION_INSTANT` — a settlement stamped exactly at the decision instant is unavailable. No interpolation, no forward fill.

`PREDICTIVE_SETTLED_FUNDING_FEATURES_V1`, 5 features: `LATEST_SETTLED_RATE`, `MEAN_LAST_3_SETTLEMENTS`, `MEAN_LAST_9_SETTLEMENTS`, `DELTA_LATEST_PREVIOUS`, `STD_LAST_9_SETTLEMENTS`. 46361 available vectors, 17962 unavailable and typed: `INSUFFICIENT_PRIOR_SETTLEMENTS` 17962, `NON_FINITE_FUNDING_FEATURE` 0, `SETTLEMENT_GAP_TOO_LARGE` 0.

Evaluation folds 2020, 2021, 2022, 2023, 2024 over 43642 eligible decision timestamps. 2019 is training/warmup only because the source begins in September 2019, so its 8673 canonical eligible labels are excluded from scoring and counted here.

## FUNDING_LINEAR_DUAL_HEAD_V1

`EXP-PRED-003-FUNDING-LINEAR-DUAL-HEAD`. Terminal classification: **NO_ADVANCE_FUNDING_LINEAR_V1**.

Pooled win rate **0.4855** on 43641 actionable predictions at coverage 0.99998 over 43642 eligible decision timestamps, with 0 counted abstentions and 1 declared sides on NEUTRAL truth.

Matched `MATCHED_TRAINING_UP_BASE_RATE` on the identical timestamps **0.4948**; primary delta **-0.0093** against a minimum important effect of +0.015, paired 97.5% interval [-0.0296, +0.0126] at alpha 0.025.

Matched `ALWAYS_UP` **0.5270**; secondary delta -0.0415 (absolute reference, no interval claimed). Matched `PREVIOUS_24H_SIGN_PERSISTENCE` 0.4681 at coverage 0.99895.

| fold | eligible | actionable | abstentions | coverage | candidate | MATCHED_TRAINING_UP_BASE_RATE | primary delta | ALWAYS_UP delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 8713 | 8713 | 0 | 1.00000 | 0.4291 | 0.4193 | +0.0099 | -0.1516 |
| 2021 | 8699 | 8699 | 0 | 1.00000 | 0.5216 | 0.5218 | -0.0002 | -0.0002 |
| 2022 | 8737 | 8737 | 0 | 1.00000 | 0.4721 | 0.4692 | +0.0030 | +0.0030 |
| 2023 | 8733 | 8733 | 0 | 1.00000 | 0.4736 | 0.5264 | -0.0528 | -0.0528 |
| 2024 | 8760 | 8759 | 0 | 0.99989 | 0.5310 | 0.5372 | -0.0062 | -0.0062 |

Brier **0.2584** against the matched control's 0.2546 — worse than the control.

| bin | count | mean predicted | empirical correct |
| --- | --- | --- | --- |
| [0.0,0.1) | 0 | n/a | n/a |
| [0.1,0.2) | 0 | n/a | n/a |
| [0.2,0.3) | 0 | n/a | n/a |
| [0.3,0.4) | 0 | n/a | n/a |
| [0.4,0.5) | 0 | n/a | n/a |
| [0.5,0.6) | 31730 | 0.5368 | 0.4806 |
| [0.6,0.7) | 11245 | 0.6399 | 0.4951 |
| [0.7,0.8) | 538 | 0.7265 | 0.5967 |
| [0.8,0.9) | 96 | 0.8522 | 0.4583 |
| [0.9,1.0] | 32 | 0.9334 | 0.2500 |

Magnitude MAE **2.2938 pp** (229.38 bps), median absolute error 1.5124 pp over 43642 source-eligible rows; 0 abstained rows declare no magnitude and are excluded and counted. Matched `ZERO_RETURN_MAGNITUDE` 2.2530 pp. Signed magnitude-match mean -0.54 over 42257 included records; exclusions `ABSTAINED_MAGNITUDE` 1372, `NEAR_ZERO_BOTH` 12, `NEUTRAL_REALIZED` 1.

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| `POOLED_SOURCE_COVERAGE_AT_LEAST_0_95` | 0.95000 | 0.99998 | yes |
| `EVERY_FOLD_COVERAGE_AT_LEAST_0_90` | 0.90000 | 0.99989 | yes |
| `POOLED_PRIMARY_DELTA_AT_LEAST_MESI` | 0.01500 | -0.00928 | no |
| `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO` | 0.00000 | -0.02963 | no |
| `POOLED_DELTA_VERSUS_MATCHED_ALWAYS_UP_ABOVE_ZERO` | 0.00000 | -0.04152 | no |
| `AT_LEAST_4_OF_5_FOLD_PRIMARY_DELTAS_NON_NEGATIVE` | 4.00000 | 2.00000 | no |
| `POOLED_BRIER_AT_MOST_MATCHED_CONTROL_BRIER` | 0.25458 | 0.25844 | no |

Failed conditions: `POOLED_PRIMARY_DELTA_AT_LEAST_MESI`, `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO`, `POOLED_DELTA_VERSUS_MATCHED_ALWAYS_UP_ABOVE_ZERO`, `AT_LEAST_4_OF_5_FOLD_PRIMARY_DELTAS_NON_NEGATIVE`, `POOLED_BRIER_AT_MOST_MATCHED_CONTROL_BRIER`. The magnitude head is reported but never rescues a failed directional gate.

Model fits 15: 5 direction base, 5 training-only Platt calibration, 5 magnitude.

## FUNDING_HGBR_DUAL_HEAD_V1

`EXP-PRED-004-FUNDING-HGBR-DUAL-HEAD`. Terminal classification: **NO_ADVANCE_FUNDING_HGBR_V1**.

Pooled win rate **0.4941** on 43641 actionable predictions at coverage 0.99998 over 43642 eligible decision timestamps, with 0 counted abstentions and 1 declared sides on NEUTRAL truth.

Matched `MATCHED_TRAINING_UP_BASE_RATE` on the identical timestamps **0.4948**; primary delta **-0.0006** against a minimum important effect of +0.015, paired 97.5% interval [-0.0177, +0.0174] at alpha 0.025.

Matched `ALWAYS_UP` **0.5270**; secondary delta -0.0329 (absolute reference, no interval claimed). Matched `PREVIOUS_24H_SIGN_PERSISTENCE` 0.4681 at coverage 0.99895.

| fold | eligible | actionable | abstentions | coverage | candidate | MATCHED_TRAINING_UP_BASE_RATE | primary delta | ALWAYS_UP delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 8713 | 8713 | 0 | 1.00000 | 0.4327 | 0.4193 | +0.0134 | -0.1481 |
| 2021 | 8699 | 8699 | 0 | 1.00000 | 0.5218 | 0.5218 | +0.0000 | +0.0000 |
| 2022 | 8737 | 8737 | 0 | 1.00000 | 0.4724 | 0.4692 | +0.0032 | +0.0032 |
| 2023 | 8733 | 8733 | 0 | 1.00000 | 0.5109 | 0.5264 | -0.0155 | -0.0155 |
| 2024 | 8760 | 8759 | 0 | 0.99989 | 0.5328 | 0.5372 | -0.0043 | -0.0043 |

Brier **0.2618** against the matched control's 0.2546 — worse than the control.

| bin | count | mean predicted | empirical correct |
| --- | --- | --- | --- |
| [0.0,0.1) | 0 | n/a | n/a |
| [0.1,0.2) | 0 | n/a | n/a |
| [0.2,0.3) | 0 | n/a | n/a |
| [0.3,0.4) | 0 | n/a | n/a |
| [0.4,0.5) | 0 | n/a | n/a |
| [0.5,0.6) | 26895 | 0.5269 | 0.4994 |
| [0.6,0.7) | 16043 | 0.6398 | 0.4886 |
| [0.7,0.8) | 703 | 0.7208 | 0.4211 |
| [0.8,0.9) | 0 | n/a | n/a |
| [0.9,1.0] | 0 | n/a | n/a |

Magnitude MAE **2.4702 pp** (247.02 bps), median absolute error 1.7150 pp over 43642 source-eligible rows; 0 abstained rows declare no magnitude and are excluded and counted. Matched `ZERO_RETURN_MAGNITUDE` 2.2530 pp. Signed magnitude-match mean -0.01 over 43283 included records; exclusions `ABSTAINED_MAGNITUDE` 357, `NEAR_ZERO_BOTH` 1, `NEUTRAL_REALIZED` 1.

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| `POOLED_SOURCE_COVERAGE_AT_LEAST_0_95` | 0.95000 | 0.99998 | yes |
| `EVERY_FOLD_COVERAGE_AT_LEAST_0_90` | 0.90000 | 0.99989 | yes |
| `POOLED_PRIMARY_DELTA_AT_LEAST_MESI` | 0.01500 | -0.00064 | no |
| `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO` | 0.00000 | -0.01767 | no |
| `POOLED_DELTA_VERSUS_MATCHED_ALWAYS_UP_ABOVE_ZERO` | 0.00000 | -0.03288 | no |
| `AT_LEAST_4_OF_5_FOLD_PRIMARY_DELTAS_NON_NEGATIVE` | 4.00000 | 3.00000 | no |
| `POOLED_BRIER_AT_MOST_MATCHED_CONTROL_BRIER` | 0.25458 | 0.26185 | no |

Failed conditions: `POOLED_PRIMARY_DELTA_AT_LEAST_MESI`, `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO`, `POOLED_DELTA_VERSUS_MATCHED_ALWAYS_UP_ABOVE_ZERO`, `AT_LEAST_4_OF_5_FOLD_PRIMARY_DELTAS_NON_NEGATIVE`, `POOLED_BRIER_AT_MOST_MATCHED_CONTROL_BRIER`. The magnitude head is reported but never rescues a failed directional gate.

Model fits 15: 5 direction base, 5 training-only Platt calibration, 5 magnitude.

## Family disposition

Both configurations were executed as preregistered and neither was chosen post hoc (`post_hoc_winner_selected: false`). Family `REJECTED_DEVELOPMENT_NO_SEALED`. Sealed eligibility: `EXP-PRED-003-FUNDING-LINEAR-DUAL-HEAD` NOT_ELIGIBLE_REJECTED_DEVELOPMENT, `EXP-PRED-004-FUNDING-HGBR-DUAL-HEAD` NOT_ELIGIBLE_REJECTED_DEVELOPMENT.

## Accounting

Matched-control base rates refit per fold: 5 (`COUNTED_TRAINING_BASE_RATE_NOT_A_MODEL_FIT`). Sealed queries 0. Champion NONE. Real money false. No additional information family, no post-cutoff data, no Stage-1 rescue, no canonical hourly gap repair. PREDICTIVE-BASELINES-V1, PREDICTIVE-INTERNAL-STRUCTURE-V1 and PREDICTIVE-INTERNAL-NONLINEAR-V1 results unchanged.
