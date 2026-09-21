# Predictive Stage 3 — macro release state V1

`PREDICTIVE_STAGE3_MACRO_RELEASE_STATE_FAMILY_V1`, the one authorized prospective source-semantics remediation of the ALFRED macro information family inside `PREDICTIVE_RESEARCH_GENERATION_V1`: whether strict point-in-time U.S. macro and financial-condition release state carries 24h directional information about BTCUSDT.

Family disposition: **REJECTED_DEVELOPMENT_NO_SEALED**. Configurations executed: 2 of 2; 0 remaining. Source-semantics versions consumed: 1 of 1; 0 remaining.

## The predecessor, and what changed

`PREDICTIVE-STAGE3-MACRO-VINTAGE-V1` stays exactly as it was recorded: disposition `BLOCKED_MACRO_SOURCE_COVERAGE_V1`, 0 model fits, 0 outer predictions, 0 configurations consumed. It is not reclassified (`reclassified: false`) and its records are unmodified (`records_modified: false`), which the admission proves by hash.

The predecessor judged a current level stale when its *observation period* date was more than a fixed number of days older than the decision date. A monthly release describes a month that closed before it was published, so that rule discarded the genuinely latest-known CPI for most of every month. This contract keeps strict availability and replaces the per-decision expiry with state persistence: the current known level is the value on the greatest observation date in the as-of-`T` snapshot (`GREATEST_OBSERVATION_DATE_IN_THE_AS_OF_T_SNAPSHOT`), and it persists until a newer observation becomes available. `current_state_expiry_relative_to_decision_time: false`; `interpolation: false`; `nearest_future_substitution: false`; `current_revised_substitution: false`; post-2024 vintages 0.

## Source identity and release-calendar integrity

`ALFRED-MACRO-CONTEXT-DEV-v1`, the same hash-pinned substrate the blocked predecessor used: `data/derived/ALFRED-macro-context-v1.parquet`, 70882 vintage rows over the eight frozen series `DFF`, `DGS10`, `T10Y2Y`, `VIXCLS`, `NFCI`, `WALCL`, `CPIAUCSL`, `UNRATE`, availability rule `NEXT_CALENDAR_DAY_00_00_UTC_AFTER_VINTAGE_START`.

Persistence is only safe if the release calendar itself is not frozen, so the audit walks the observation-date sequence of every series before any outcome is read.

| series | frequency | observation dates | max gap (days) | limit | passed |
| --- | --- | --- | --- | --- | --- |
| `CPIAUCSL` | MONTHLY | 87 | 31 | 70 | yes |
| `DFF` | DAILY | 2693 | 1 | 10 | yes |
| `DGS10` | DAILY | 1842 | 4 | 10 | yes |
| `NFCI` | WEEKLY | 384 | 7 | 21 | yes |
| `T10Y2Y` | DAILY | 1843 | 4 | 10 | yes |
| `UNRATE` | MONTHLY | 87 | 31 | 70 | yes |
| `VIXCLS` | DAILY | 1874 | 4 | 10 | yes |
| `WALCL` | WEEKLY | 384 | 7 | 21 | yes |

Source audit `SOURCE_GATES_PASSED`. Included folds 2020, 2021, 2022, 2023, 2024; excluded candidate folds 2019. The fold set is the deterministic output of the pre-result source audit (`PRE_RESULT_SOURCE_AUDIT_DETERMINISTIC`), and no return value entered that choice (`fold_selection_used_return_values: false`).

`PREDICTIVE_MACRO_VINTAGE_FEATURES_V2` supersedes `PREDICTIVE_MACRO_VINTAGE_FEATURES_V1` and holds the same 13 economic quantities in the same order (`identical_quantities_and_order_to_v1: true`): `DFF_LEVEL`, `DFF_DELTA_30D`, `DGS10_LEVEL`, `DGS10_DELTA_30D`, `T10Y2Y_LEVEL`, `T10Y2Y_DELTA_30D`, `LOG_VIX_LEVEL`, `VIX_LOG_CHANGE_5D`, `NFCI_LEVEL`, `NFCI_DELTA_28D`, `WALCL_LOG_CHANGE_28D`, `CPI_YOY_LOG_CHANGE`, `UNRATE_DELTA_3M`. 54352 available vectors, 9971 unavailable and typed: `CPIAUCSL_12M_EXACT_ANCHOR_UNAVAILABLE` 8597, `CPIAUCSL_CURRENT_RELEASE_STATE_UNAVAILABLE` 1186, `DFF_CURRENT_RELEASE_STATE_UNAVAILABLE` 44, `NFCI_CURRENT_RELEASE_STATE_UNAVAILABLE` 120, `WALCL_CURRENT_RELEASE_STATE_UNAVAILABLE` 24. Direction and calibrated probability only; no magnitude is declared.

How long a current level actually persists over the included folds, as source accounting and never as a feature (`current_release_age_is_a_model_feature: false`):

| series | min age (days) | median | max |
| --- | --- | --- | --- |
| `CPIAUCSL` | 38 | 57 | 75 |
| `DFF` | 2 | 2 | 6 |
| `DGS10` | 2 | 2 | 6 |
| `NFCI` | 6 | 9 | 27 |
| `T10Y2Y` | 1 | 1 | 5 |
| `UNRATE` | 32 | 50 | 70 |
| `VIXCLS` | -2 | 1 | 6 |
| `WALCL` | 2 | 5 | 12 |

## MACRO_RELEASE_STATE_LINEAR_V1

`EXP-PRED-009-MACRO-RELEASE-STATE-LINEAR` — `H-PRED-MACRO-003`. Terminal classification: **NO_ADVANCE_MACRO_RELEASE_STATE_LINEAR_V1**.

Pooled win rate **0.4824** on 43641 actionable predictions at coverage 0.99998 over 43642 eligible decision timestamps, with 0 counted abstentions and 1 declared sides on NEUTRAL truth.

Matched `TRAINING_UP_BASE_RATE` on the identical timestamps **0.5270**; primary delta **-0.0446** against a minimum important effect of +0.015, paired 97.5% interval [-0.0675, -0.0196] at alpha 0.025, seed 20260921.

Matched `ALWAYS_UP` win rate 0.5270 (-0.0446 against the candidate). Candidate Brier 0.2826 against the control's 0.2500. Matched `PREVIOUS_24H_SIGN_PERSISTENCE` 0.4681 at coverage 0.99895 (descriptive only, never inverted).

| fold | eligible | actionable | abstentions | coverage | candidate | TRAINING_UP_BASE_RATE | delta | ALWAYS_UP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 8713 | 8713 | 0 | 1.00000 | 0.4216 | 0.5807 | -0.1592 | 0.5807 |
| 2021 | 8699 | 8699 | 0 | 1.00000 | 0.5110 | 0.5218 | -0.0108 | 0.5218 |
| 2022 | 8737 | 8737 | 0 | 1.00000 | 0.4692 | 0.4692 | +0.0000 | 0.4692 |
| 2023 | 8733 | 8733 | 0 | 1.00000 | 0.4736 | 0.5264 | -0.0528 | 0.5264 |
| 2024 | 8760 | 8759 | 0 | 0.99989 | 0.5367 | 0.5372 | -0.0005 | 0.5372 |

| bin | count | mean predicted | empirical correct |
| --- | --- | --- | --- |
| [0.0,0.1) | 0 | n/a | n/a |
| [0.1,0.2) | 0 | n/a | n/a |
| [0.2,0.3) | 0 | n/a | n/a |
| [0.3,0.4) | 0 | n/a | n/a |
| [0.4,0.5) | 0 | n/a | n/a |
| [0.5,0.6) | 30765 | 0.5283 | 0.4955 |
| [0.6,0.7) | 4551 | 0.6425 | 0.4039 |
| [0.7,0.8) | 3922 | 0.7679 | 0.5309 |
| [0.8,0.9) | 2227 | 0.8475 | 0.4207 |
| [0.9,1.0] | 2176 | 0.9509 | 0.4375 |

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| `POOLED_COVERAGE_AT_LEAST_0_95` | 0.95000 | 0.99998 | yes |
| `EVERY_INCLUDED_FOLD_COVERAGE_AT_LEAST_0_90` | 0.90000 | 0.99989 | yes |
| `POOLED_DELTA_VERSUS_MATCHED_TRAINING_BASE_RATE_AT_LEAST_MESI` | 0.01500 | -0.04459 | no |
| `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO` | 0.00000 | -0.06748 | no |
| `WIN_RATE_AT_LEAST_MATCHED_ALWAYS_UP` | 0.52703 | 0.48244 | no |
| `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER` | 0.25004 | 0.28260 | no |
| `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE` | 4.00000 | 1.00000 | no |

Failed conditions: `POOLED_DELTA_VERSUS_MATCHED_TRAINING_BASE_RATE_AT_LEAST_MESI`, `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO`, `WIN_RATE_AT_LEAST_MATCHED_ALWAYS_UP`, `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER`, `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE`. No secondary metric rescues a failed directional gate.

Model fits 10: 5 direction base and 5 training-only Platt calibration.

## MACRO_RELEASE_STATE_HGBR_V1

`EXP-PRED-010-MACRO-RELEASE-STATE-HGBR` — `H-PRED-MACRO-004`. Terminal classification: **NO_ADVANCE_MACRO_RELEASE_STATE_HGBR_V1**.

Pooled win rate **0.4814** on 43641 actionable predictions at coverage 0.99998 over 43642 eligible decision timestamps, with 0 counted abstentions and 1 declared sides on NEUTRAL truth.

Matched `TRAINING_UP_BASE_RATE` on the identical timestamps **0.5270**; primary delta **-0.0457** against a minimum important effect of +0.015, paired 97.5% interval [-0.0693, -0.0210] at alpha 0.025, seed 20260921.

Matched `ALWAYS_UP` win rate 0.5270 (-0.0457 against the candidate). Candidate Brier 0.2565 against the control's 0.2500. Matched `PREVIOUS_24H_SIGN_PERSISTENCE` 0.4681 at coverage 0.99895 (descriptive only, never inverted).

| fold | eligible | actionable | abstentions | coverage | candidate | TRAINING_UP_BASE_RATE | delta | ALWAYS_UP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 8713 | 8713 | 0 | 1.00000 | 0.4193 | 0.5807 | -0.1615 | 0.5807 |
| 2021 | 8699 | 8699 | 0 | 1.00000 | 0.5218 | 0.5218 | +0.0000 | 0.5218 |
| 2022 | 8737 | 8737 | 0 | 1.00000 | 0.4609 | 0.4692 | -0.0082 | 0.4692 |
| 2023 | 8733 | 8733 | 0 | 1.00000 | 0.4675 | 0.5264 | -0.0589 | 0.5264 |
| 2024 | 8760 | 8759 | 0 | 0.99989 | 0.5372 | 0.5372 | +0.0000 | 0.5372 |

| bin | count | mean predicted | empirical correct |
| --- | --- | --- | --- |
| [0.0,0.1) | 0 | n/a | n/a |
| [0.1,0.2) | 0 | n/a | n/a |
| [0.2,0.3) | 0 | n/a | n/a |
| [0.3,0.4) | 0 | n/a | n/a |
| [0.4,0.5) | 0 | n/a | n/a |
| [0.5,0.6) | 32854 | 0.5363 | 0.4706 |
| [0.6,0.7) | 10787 | 0.6233 | 0.5141 |
| [0.7,0.8) | 0 | n/a | n/a |
| [0.8,0.9) | 0 | n/a | n/a |
| [0.9,1.0] | 0 | n/a | n/a |

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| `POOLED_COVERAGE_AT_LEAST_0_95` | 0.95000 | 0.99998 | yes |
| `EVERY_INCLUDED_FOLD_COVERAGE_AT_LEAST_0_90` | 0.90000 | 0.99989 | yes |
| `POOLED_DELTA_VERSUS_MATCHED_TRAINING_BASE_RATE_AT_LEAST_MESI` | 0.01500 | -0.04567 | no |
| `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO` | 0.00000 | -0.06927 | no |
| `WIN_RATE_AT_LEAST_MATCHED_ALWAYS_UP` | 0.52703 | 0.48136 | no |
| `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER` | 0.25004 | 0.25655 | no |
| `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE` | 4.00000 | 2.00000 | no |

Failed conditions: `POOLED_DELTA_VERSUS_MATCHED_TRAINING_BASE_RATE_AT_LEAST_MESI`, `PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO`, `WIN_RATE_AT_LEAST_MATCHED_ALWAYS_UP`, `BRIER_AT_MOST_MATCHED_TRAINING_BASE_RATE_BRIER`, `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE`. No secondary metric rescues a failed directional gate.

Model fits 10: 5 direction base and 5 training-only Platt calibration.

## Family disposition

Both configurations were executed as preregistered and neither was chosen post hoc (`post_hoc_winner_selected: false`). Family `REJECTED_DEVELOPMENT_NO_SEALED`. Sealed eligibility: `EXP-PRED-009-MACRO-RELEASE-STATE-LINEAR` NOT_ELIGIBLE_REJECTED_DEVELOPMENT, `EXP-PRED-010-MACRO-RELEASE-STATE-HGBR` NOT_ELIGIBLE_REJECTED_DEVELOPMENT. The macro source design is now closed for this generation (`macro_source_design_closed: true`); a third source semantics is forbidden.

## Accounting

Base-rate controls refit per fold: 5 (`COUNTED_TRAINING_BASE_RATE_NOT_A_MODEL_FIT`). Sealed queries 0. Champion NONE. Real money false. No combination with the rejected Stage-1, settled-funding, open-interest or cross-asset breadth features, no basis, CFTC, calendar, news, sentiment or on-chain source, no Stage-1 substrate repair, no current-revised macro data, no interpolation or future vintage, no post-cutoff data. Every prior predictive experiment result and every predecessor record is unchanged.
