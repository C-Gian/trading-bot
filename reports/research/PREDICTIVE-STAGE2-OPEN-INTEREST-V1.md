# Predictive Stage 2 — open interest V1

`PREDICTIVE_STAGE2_OPEN_INTEREST_MODEL_FAMILY_V1`, the second Stage-2 information family of `PREDICTIVE_RESEARCH_GENERATION_V1`: whether the **quantity** of leveraged BTCUSDT perpetual positioning carries 24h directional information.

Family disposition: **REJECTED_DEVELOPMENT_NO_SEALED**. Configurations executed: 2 of 2; 0 remaining.

## Source, provenance and point-in-time semantics

`BTCUSDT-USDM-OPEN-INTEREST-DEV-v1`: 455273 records from 2020-09-01T00:00:00Z to 2024-12-31T23:55:00Z, 1583 official daily objects, every one verified against the archive's own checksum (`1583` verified). Source `BINANCE_USDM_FUTURES_OFFICIAL_PUBLIC_DATA_ARCHIVE`, class `OFFICIAL_BINANCE_PUBLIC_DATA_ARCHIVE`, credential-free. No third-party vendor, no REST snapshot history, no reconstruction or backfill.

Fields read: `create_time`, `sum_open_interest`. `sum_open_interest_value` is excluded because notional embeds BTC price, and every long/short, top-trader and taker ratio column is excluded. Availability rule `CREATE_TIME_STRICTLY_BEFORE_DECISION_INSTANT` with a 10-minute staleness bound — a record stamped exactly at the decision instant is unavailable, and there is no interpolation or forward fill.

Source audit `SOURCE_GATES_PASSED`. Included folds 2022, 2023, 2024; excluded candidate folds 2020, 2021. The fold set is the deterministic output of the pre-result source audit (`PRE_RESULT_SOURCE_AUDIT_DETERMINISTIC`), and no return value entered that choice (`fold_selection_used_return_values: false`).

`PREDICTIVE_OPEN_INTEREST_FEATURES_V1`, 6 features: `OI_LOG_CHANGE_1H`, `OI_LOG_CHANGE_4H`, `OI_LOG_CHANGE_24H`, `OI_LOG_LEVEL_Z24`, `OI_LOG_DIFF_VOL24`, `OI_LOG_TREND24`. 37353 available vectors, 26970 unavailable and typed: `NON_FINITE_OPEN_INTEREST_FEATURE` 0, `NON_POSITIVE_OPEN_INTEREST` 249, `NO_PRIOR_OPEN_INTEREST_RECORD` 26434, `OPEN_INTEREST_STATE_TOO_STALE` 287.

## OPEN_INTEREST_LINEAR_DUAL_HEAD_V1

`EXP-PRED-005-OPEN-INTEREST-LINEAR-DUAL-HEAD` — `H-PRED-OI-001`. Terminal classification: **NO_ADVANCE_OPEN_INTEREST_LINEAR_V1**.

Pooled win rate **0.4846** on 25970 actionable predictions at coverage 0.99009 over 26230 eligible decision timestamps, with 259 counted abstentions and 1 declared sides on NEUTRAL truth.

Matched `ALWAYS_UP` on the identical timestamps **0.5087**; primary delta **-0.0241** against a minimum important effect of +0.015, paired 97.5% interval [-0.0523, +0.0079] at alpha 0.025, seed 20260917.

Matched `TRAINING_UP_BASE_RATE` win rate 0.5087 and Brier 0.2514; the candidate's Brier is 0.2519. Matched `PREVIOUS_24H_SIGN_PERSISTENCE` 0.4640 at coverage 0.99988 (descriptive only, never inverted).

| fold | eligible | actionable | abstentions | coverage | candidate | ALWAYS_UP | delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | 8737 | 8703 | 34 | 0.99611 | 0.4727 | 0.4672 | +0.0055 |
| 2023 | 8733 | 8683 | 50 | 0.99427 | 0.4732 | 0.5268 | -0.0536 |
| 2024 | 8760 | 8584 | 175 | 0.97991 | 0.5082 | 0.5325 | -0.0243 |

| bin | count | mean predicted | empirical correct |
| --- | --- | --- | --- |
| [0.0,0.1) | 0 | n/a | n/a |
| [0.1,0.2) | 0 | n/a | n/a |
| [0.2,0.3) | 0 | n/a | n/a |
| [0.3,0.4) | 0 | n/a | n/a |
| [0.4,0.5) | 0 | n/a | n/a |
| [0.5,0.6) | 25948 | 0.5246 | 0.4845 |
| [0.6,0.7) | 22 | 0.6109 | 0.6364 |
| [0.7,0.8) | 0 | n/a | n/a |
| [0.8,0.9) | 0 | n/a | n/a |
| [0.9,1.0] | 0 | n/a | n/a |

Magnitude MAE **1.9358 pp** (193.58 bps), median absolute error 1.2846 pp over 25971 source-eligible rows; 259 abstained rows declare no magnitude and are excluded and counted. Matched `ZERO_RETURN_MAGNITUDE` 1.9222 pp. Signed magnitude-match mean -0.16 over 24987 included records; exclusions `ABSTAINED_MAGNITUDE` 976, `NEAR_ZERO_BOTH` 7, `NEUTRAL_REALIZED` 1.

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| `POOLED_COVERAGE_AT_LEAST_0_95` | 0.95000 | 0.99009 | yes |
| `EVERY_INCLUDED_FOLD_COVERAGE_AT_LEAST_0_90` | 0.90000 | 0.97991 | yes |
| `POOLED_DELTA_VERSUS_MATCHED_ALWAYS_UP_AT_LEAST_MESI` | 0.01500 | -0.02410 | no |
| `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO` | 0.00000 | -0.05234 | no |
| `WIN_RATE_AT_LEAST_MATCHED_TRAINING_BASE_RATE` | 0.50870 | 0.48460 | no |
| `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER` | 0.25139 | 0.25189 | no |
| `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE` | 2.00000 | 1.00000 | no |

Failed conditions: `POOLED_DELTA_VERSUS_MATCHED_ALWAYS_UP_AT_LEAST_MESI`, `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO`, `WIN_RATE_AT_LEAST_MATCHED_TRAINING_BASE_RATE`, `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER`, `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE`. Magnitude MAE and the signed magnitude-match diagnostic are mandatory companions and never rescue a failed directional gate.

Model fits 9: 3 direction base, 3 training-only Platt calibration, 3 magnitude.

## OPEN_INTEREST_HGBR_DUAL_HEAD_V1

`EXP-PRED-006-OPEN-INTEREST-HGBR-DUAL-HEAD` — `H-PRED-OI-002`. Terminal classification: **NO_ADVANCE_OPEN_INTEREST_HGBR_V1**.

Pooled win rate **0.5052** on 25970 actionable predictions at coverage 0.99009 over 26230 eligible decision timestamps, with 259 counted abstentions and 1 declared sides on NEUTRAL truth.

Matched `ALWAYS_UP` on the identical timestamps **0.5087**; primary delta **-0.0035** against a minimum important effect of +0.015, paired 97.5% interval [-0.0326, +0.0298] at alpha 0.025, seed 20260917.

Matched `TRAINING_UP_BASE_RATE` win rate 0.5087 and Brier 0.2514; the candidate's Brier is 0.2514. Matched `PREVIOUS_24H_SIGN_PERSISTENCE` 0.4640 at coverage 0.99988 (descriptive only, never inverted).

| fold | eligible | actionable | abstentions | coverage | candidate | ALWAYS_UP | delta |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | 8737 | 8703 | 34 | 0.99611 | 0.5011 | 0.4672 | +0.0339 |
| 2023 | 8733 | 8683 | 50 | 0.99427 | 0.4732 | 0.5268 | -0.0536 |
| 2024 | 8760 | 8584 | 175 | 0.97991 | 0.5416 | 0.5325 | +0.0091 |

| bin | count | mean predicted | empirical correct |
| --- | --- | --- | --- |
| [0.0,0.1) | 0 | n/a | n/a |
| [0.1,0.2) | 0 | n/a | n/a |
| [0.2,0.3) | 0 | n/a | n/a |
| [0.3,0.4) | 0 | n/a | n/a |
| [0.4,0.5) | 0 | n/a | n/a |
| [0.5,0.6) | 25719 | 0.5300 | 0.5055 |
| [0.6,0.7) | 251 | 0.6224 | 0.4701 |
| [0.7,0.8) | 0 | n/a | n/a |
| [0.8,0.9) | 0 | n/a | n/a |
| [0.9,1.0] | 0 | n/a | n/a |

Magnitude MAE **2.0172 pp** (201.72 bps), median absolute error 1.3791 pp over 25971 source-eligible rows; 259 abstained rows declare no magnitude and are excluded and counted. Matched `ZERO_RETURN_MAGNITUDE` 1.9222 pp. Signed magnitude-match mean -0.53 over 25692 included records; exclusions `ABSTAINED_MAGNITUDE` 278, `NEAR_ZERO_BOTH` 0, `NEUTRAL_REALIZED` 1.

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| `POOLED_COVERAGE_AT_LEAST_0_95` | 0.95000 | 0.99009 | yes |
| `EVERY_INCLUDED_FOLD_COVERAGE_AT_LEAST_0_90` | 0.90000 | 0.97991 | yes |
| `POOLED_DELTA_VERSUS_MATCHED_ALWAYS_UP_AT_LEAST_MESI` | 0.01500 | -0.00354 | no |
| `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO` | 0.00000 | -0.03255 | no |
| `WIN_RATE_AT_LEAST_MATCHED_TRAINING_BASE_RATE` | 0.50870 | 0.50516 | no |
| `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER` | 0.25139 | 0.25141 | no |
| `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE` | 2.00000 | 2.00000 | yes |

Failed conditions: `POOLED_DELTA_VERSUS_MATCHED_ALWAYS_UP_AT_LEAST_MESI`, `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO`, `WIN_RATE_AT_LEAST_MATCHED_TRAINING_BASE_RATE`, `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER`. Magnitude MAE and the signed magnitude-match diagnostic are mandatory companions and never rescue a failed directional gate.

Model fits 9: 3 direction base, 3 training-only Platt calibration, 3 magnitude.

## Family disposition

Both configurations were executed as preregistered and neither was chosen post hoc (`post_hoc_winner_selected: false`). Family `REJECTED_DEVELOPMENT_NO_SEALED`. Sealed eligibility: `EXP-PRED-005-OPEN-INTEREST-LINEAR-DUAL-HEAD` NOT_ELIGIBLE_REJECTED_DEVELOPMENT, `EXP-PRED-006-OPEN-INTEREST-HGBR-DUAL-HEAD` NOT_ELIGIBLE_REJECTED_DEVELOPMENT.

## Accounting

Base-rate controls refit per fold: 3 (`COUNTED_TRAINING_BASE_RATE_NOT_A_MODEL_FIT`). Sealed queries 0. Champion NONE. Real money false. No asset-universe expansion, no additional information family, no combination with the rejected Stage-1 or funding features, no Stage-1 substrate repair, no post-cutoff data. Every prior predictive experiment result is unchanged.
