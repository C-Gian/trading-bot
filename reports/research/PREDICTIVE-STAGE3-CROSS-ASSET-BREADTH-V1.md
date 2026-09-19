# Predictive Stage 3 — cross-asset breadth V1

`PREDICTIVE_STAGE3_CROSS_ASSET_BREADTH_FAMILY_V1`, the first Stage-3 information family of `PREDICTIVE_RESEARCH_GENERATION_V1` and the first orthogonal, non-BTC channel this generation has tested: whether contemporaneous crypto-market breadth carries 24h directional information about BTCUSDT.

Family disposition: **REJECTED_DEVELOPMENT_NO_SEALED**. Configurations executed: 2 of 2; 0 remaining.

## Source, universe and point-in-time semantics

`BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1`: 17925 official monthly objects from `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/data/spot/monthly/klines`, spot `1h`, credential-free, consolidated into 12886210 hourly rows over 486 symbols. The universe is derived from `HISTORICAL_ARCHIVE_EVIDENCE_NOT_CURRENT_EXCHANGE_INFO`, 52 leveraged tokens are excluded by the frozen symbol rule, and **BTCUSDT is removed from the cross-section entirely** — it is the prediction target, never a context feature.

At each decision instant `T` an asset participates only when it carries all 4 required endpoint bars (`T`, `T-1h`, `T-24h`, `T-168h`), and the instant is usable only when at least 30 such assets exist. Membership is recomputed at every instant and may grow or shrink causally. There is no future-survival filter, no whole-sample participation threshold, no revival of the retired 504-row rule, no interpolation, no forward fill and no nearest-bar substitution. Cross-sectional statistics are `EQUAL_WEIGHTED`.

Point-in-time universe over the included evaluation timestamps: minimum 0, median 322, maximum 387 of 485 admitted symbols. Universe size is source accounting and never a model feature.

Source audit `SOURCE_GATES_PASSED`. Included folds 2020, 2021, 2022, 2023, 2024; excluded candidate folds 2019. The fold set is the deterministic output of the pre-result source audit (`PRE_RESULT_SOURCE_AUDIT_DETERMINISTIC`), and no return value entered that choice (`fold_selection_used_return_values: false`).

`PREDICTIVE_CROSS_ASSET_BREADTH_FEATURES_V1`, 8 features: `BREADTH_UP_SHARE_1H`, `BREADTH_UP_SHARE_24H`, `BREADTH_UP_SHARE_168H`, `CROSS_MEDIAN_RETURN_1H`, `CROSS_MEDIAN_RETURN_24H`, `CROSS_MEDIAN_RETURN_168H`, `CROSS_MAD_RETURN_24H`, `CROSS_MAD_RETURN_168H`. 50731 available vectors, 13592 unavailable and typed: `DECISION_INSTANT_OUTSIDE_SOURCE_SPAN` 12061, `INSUFFICIENT_POINT_IN_TIME_UNIVERSE` 1531, `NON_FINITE_CROSS_ASSET_FEATURE` 0. Direction and calibrated probability only; no magnitude is declared.

## CROSS_ASSET_BREADTH_LINEAR_V1

`EXP-PRED-007-CROSS-ASSET-BREADTH-LINEAR` — `H-PRED-XB-001`. Terminal classification: **NO_ADVANCE_CROSS_ASSET_BREADTH_LINEAR_V1**.

Pooled win rate **0.4930** on 43572 actionable predictions at coverage 0.99840 over 43642 eligible decision timestamps, with 69 counted abstentions and 1 declared sides on NEUTRAL truth.

Matched `TRAINING_UP_BASE_RATE` on the identical timestamps **0.5268**; primary delta **-0.0338** against a minimum important effect of +0.015, paired 97.5% interval [-0.0597, -0.0071] at alpha 0.025, seed 20260919.

Matched `ALWAYS_UP` win rate 0.5268 (-0.0338 against the candidate). Candidate Brier 0.2561 against the control's 0.2500. Matched `PREVIOUS_24H_SIGN_PERSISTENCE` 0.4680 at coverage 0.99966 (descriptive only, never inverted).

| fold | eligible | actionable | abstentions | coverage | candidate | TRAINING_UP_BASE_RATE | delta | ALWAYS_UP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 8713 | 8676 | 37 | 0.99575 | 0.4195 | 0.5807 | -0.1611 | 0.5807 |
| 2021 | 8699 | 8670 | 29 | 0.99667 | 0.5261 | 0.5210 | +0.0051 | 0.5210 |
| 2022 | 8737 | 8737 | 0 | 1.00000 | 0.5060 | 0.4692 | +0.0369 | 0.4692 |
| 2023 | 8733 | 8730 | 3 | 0.99966 | 0.4914 | 0.5263 | -0.0349 | 0.5263 |
| 2024 | 8760 | 8759 | 0 | 0.99989 | 0.5219 | 0.5372 | -0.0153 | 0.5372 |

| bin | count | mean predicted | empirical correct |
| --- | --- | --- | --- |
| [0.0,0.1) | 0 | n/a | n/a |
| [0.1,0.2) | 0 | n/a | n/a |
| [0.2,0.3) | 0 | n/a | n/a |
| [0.3,0.4) | 0 | n/a | n/a |
| [0.4,0.5) | 0 | n/a | n/a |
| [0.5,0.6) | 34681 | 0.5499 | 0.4800 |
| [0.6,0.7) | 8693 | 0.6358 | 0.5420 |
| [0.7,0.8) | 198 | 0.7103 | 0.6313 |
| [0.8,0.9) | 0 | n/a | n/a |
| [0.9,1.0] | 0 | n/a | n/a |

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| `POOLED_COVERAGE_AT_LEAST_0_95` | 0.95000 | 0.99840 | yes |
| `EVERY_INCLUDED_FOLD_COVERAGE_AT_LEAST_0_90` | 0.90000 | 0.99575 | yes |
| `POOLED_DELTA_VERSUS_MATCHED_TRAINING_BASE_RATE_AT_LEAST_MESI` | 0.01500 | -0.03376 | no |
| `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO` | 0.00000 | -0.05968 | no |
| `WIN_RATE_AT_LEAST_MATCHED_ALWAYS_UP` | 0.52681 | 0.49305 | no |
| `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER` | 0.24999 | 0.25615 | no |
| `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE` | 4.00000 | 2.00000 | no |

Failed conditions: `POOLED_DELTA_VERSUS_MATCHED_TRAINING_BASE_RATE_AT_LEAST_MESI`, `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO`, `WIN_RATE_AT_LEAST_MATCHED_ALWAYS_UP`, `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER`, `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE`. No secondary metric rescues a failed directional gate.

Model fits 10: 5 direction base and 5 training-only Platt calibration.

## CROSS_ASSET_BREADTH_HGBR_V1

`EXP-PRED-008-CROSS-ASSET-BREADTH-HGBR` — `H-PRED-XB-002`. Terminal classification: **NO_ADVANCE_CROSS_ASSET_BREADTH_HGBR_V1**.

Pooled win rate **0.4882** on 43572 actionable predictions at coverage 0.99840 over 43642 eligible decision timestamps, with 69 counted abstentions and 1 declared sides on NEUTRAL truth.

Matched `TRAINING_UP_BASE_RATE` on the identical timestamps **0.5268**; primary delta **-0.0386** against a minimum important effect of +0.015, paired 97.5% interval [-0.0616, -0.0148] at alpha 0.025, seed 20260919.

Matched `ALWAYS_UP` win rate 0.5268 (-0.0386 against the candidate). Candidate Brier 0.2563 against the control's 0.2500. Matched `PREVIOUS_24H_SIGN_PERSISTENCE` 0.4680 at coverage 0.99966 (descriptive only, never inverted).

| fold | eligible | actionable | abstentions | coverage | candidate | TRAINING_UP_BASE_RATE | delta | ALWAYS_UP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 8713 | 8676 | 37 | 0.99575 | 0.4255 | 0.5807 | -0.1551 | 0.5807 |
| 2021 | 8699 | 8670 | 29 | 0.99667 | 0.5180 | 0.5210 | -0.0030 | 0.5210 |
| 2022 | 8737 | 8737 | 0 | 1.00000 | 0.4949 | 0.4692 | +0.0258 | 0.4692 |
| 2023 | 8733 | 8730 | 3 | 0.99966 | 0.4740 | 0.5263 | -0.0523 | 0.5263 |
| 2024 | 8760 | 8759 | 0 | 0.99989 | 0.5280 | 0.5372 | -0.0091 | 0.5372 |

| bin | count | mean predicted | empirical correct |
| --- | --- | --- | --- |
| [0.0,0.1) | 0 | n/a | n/a |
| [0.1,0.2) | 0 | n/a | n/a |
| [0.2,0.3) | 0 | n/a | n/a |
| [0.3,0.4) | 0 | n/a | n/a |
| [0.4,0.5) | 0 | n/a | n/a |
| [0.5,0.6) | 34236 | 0.5421 | 0.4788 |
| [0.6,0.7) | 9082 | 0.6302 | 0.5175 |
| [0.7,0.8) | 254 | 0.7238 | 0.7008 |
| [0.8,0.9) | 0 | n/a | n/a |
| [0.9,1.0] | 0 | n/a | n/a |

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| `POOLED_COVERAGE_AT_LEAST_0_95` | 0.95000 | 0.99840 | yes |
| `EVERY_INCLUDED_FOLD_COVERAGE_AT_LEAST_0_90` | 0.90000 | 0.99575 | yes |
| `POOLED_DELTA_VERSUS_MATCHED_TRAINING_BASE_RATE_AT_LEAST_MESI` | 0.01500 | -0.03865 | no |
| `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO` | 0.00000 | -0.06163 | no |
| `WIN_RATE_AT_LEAST_MATCHED_ALWAYS_UP` | 0.52681 | 0.48816 | no |
| `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER` | 0.24999 | 0.25634 | no |
| `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE` | 4.00000 | 1.00000 | no |

Failed conditions: `POOLED_DELTA_VERSUS_MATCHED_TRAINING_BASE_RATE_AT_LEAST_MESI`, `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO`, `WIN_RATE_AT_LEAST_MATCHED_ALWAYS_UP`, `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER`, `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE`. No secondary metric rescues a failed directional gate.

Model fits 10: 5 direction base and 5 training-only Platt calibration.

## Family disposition

Both configurations were executed as preregistered and neither was chosen post hoc (`post_hoc_winner_selected: false`). Family `REJECTED_DEVELOPMENT_NO_SEALED`. Sealed eligibility: `EXP-PRED-007-CROSS-ASSET-BREADTH-LINEAR` NOT_ELIGIBLE_REJECTED_DEVELOPMENT, `EXP-PRED-008-CROSS-ASSET-BREADTH-HGBR` NOT_ELIGIBLE_REJECTED_DEVELOPMENT.

## Accounting

Base-rate controls refit per fold: 5 (`COUNTED_TRAINING_BASE_RATE_NOT_A_MODEL_FIT`). Sealed queries 0. Champion NONE. Real money false. BTCUSDT remains the sole prediction target and no asset was authorized for trading. No combination with the rejected Stage-1, settled-funding or open-interest features, no import of historical cross-section research results, no basis, CFTC, macro, calendar, news, sentiment or on-chain source, no Stage-1 substrate repair, no post-cutoff data. Every prior predictive experiment result is unchanged.
