# Predictive V2 internal structure selective V1

Family disposition: **REJECTED_DEVELOPMENT_NO_SEALED**.

The eighteen causal internal features are inherited unchanged from the frozen Generation V1 definition and reconciled against it; the 169-hour availability rule is reused, not repaired. No V1 fitted model, probability, score tail or reliability bin was read. Magnitude is deferred, sealed queries are 0, Champion is `NONE`, and real money is false.

## Configuration results

| configuration | feature-valid N | coverage | actionable N | action coverage | selective win rate | full-fold UP | enrichment | 97.5% interval | classification |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `V2_INTERNAL_LINEAR_V1` | 48953 | 0.935735 | 3321 | 0.067841 | 0.549533 | 0.526179 | 0.023354 | [-0.032945, 0.076516] | `NO_ADVANCE_V2_INTERNAL_LINEAR_V1` |
| `V2_INTERNAL_HGBR_V1` | 48953 | 0.935735 | 3098 | 0.063285 | 0.514526 | 0.526179 | -0.011653 | [-0.070108, 0.049119] | `NO_ADVANCE_V2_INTERNAL_HGBR_V1` |

## V2_INTERNAL_LINEAR_V1

Pooled feature-valid UP rate `0.523932` over `48951` feature-valid scorable rows; pooled full-fold UP rate `0.526179`.

Full-probability Brier `0.253403473`; matched training-base-rate Brier `0.249826567`. Action mean p_up `0.629620673`; empirical LONG win rate `0.549533273`; calibration gap `0.080087400`.

Bootstrap retained `10000` and discarded `0` (`0.000000`); support `STABLE`.

| fold | feature-valid N | feature-valid coverage | LONG N | action coverage | win rate | full-fold UP | feature-valid UP | enrichment |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2019 | 7665 | 0.883777 | 0 | 0.000000 | n/a | 0.521910 | 0.523617 | n/a |
| 2020 | 7484 | 0.858946 | 34 | 0.004543 | 0.441176 | 0.580741 | 0.588589 | -0.139565 |
| 2021 | 7742 | 0.889987 | 3281 | 0.423792 | 0.550137 | 0.521784 | 0.508137 | 0.028353 |
| 2022 | 8737 | 1.000000 | 6 | 0.000687 | 0.833333 | 0.469154 | 0.469154 | 0.364179 |
| 2023 | 8565 | 0.980763 | 0 | 0.000000 | n/a | 0.526394 | 0.524343 | n/a |
| 2024 | 8760 | 1.000000 | 0 | 0.000000 | n/a | 0.537162 | 0.537162 | n/a |

Advancement gates:

- `POOLED_ACTION_COVERAGE_AT_LEAST_0_02`: PASS (observed `0.0678405817825261`, threshold `0.02`).
- `EVERY_FOLD_ACTION_COVERAGE_AT_LEAST_0_005`: FAIL (observed `0.0`, threshold `0.005`).
- `POOLED_ACTIONABLE_LONGS_AT_LEAST_500`: PASS (observed `3321`, threshold `500`).
- `EVERY_FOLD_ACTIONABLE_LONGS_AT_LEAST_30`: FAIL (observed `0`, threshold `30`).
- `POOLED_SELECTIVE_LONG_WIN_RATE_AT_LEAST_0_60`: FAIL (observed `0.5495332731105089`, threshold `0.6`).
- `POOLED_ENRICHMENT_OVER_FULL_FOLD_UP_RATE_AT_LEAST_0_05`: FAIL (observed `0.023354311858047816`, threshold `0.05`).
- `ENRICHMENT_INTERVAL_LOWER_BOUND_ABOVE_ZERO`: FAIL (observed `-0.03294502713360601`, threshold `0.0`).
- `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE_ENRICHMENT`: FAIL (observed `2`, threshold `4`).
- `FULL_PROBABILITY_BRIER_AT_MOST_MATCHED_TRAINING_UP_BASE_RATE_BRIER`: FAIL (observed `0.253403473028443`, threshold `0.24982656709472292`).
- `ACTION_CALIBRATION_GAP_AT_MOST_0_05`: FAIL (observed `0.08008739963351852`, threshold `0.05`).

Actionable reliability bins:

- `[0.0,0.1)`: n=0, mean_p=None, empirical=None.
- `[0.1,0.2)`: n=0, mean_p=None, empirical=None.
- `[0.2,0.3)`: n=0, mean_p=None, empirical=None.
- `[0.3,0.4)`: n=0, mean_p=None, empirical=None.
- `[0.4,0.5)`: n=0, mean_p=None, empirical=None.
- `[0.5,0.6)`: n=0, mean_p=None, empirical=None.
- `[0.6,0.7)`: n=3259, mean_p=0.6276503445326198, empirical=0.5428045412703283.
- `[0.7,0.8)`: n=57, mean_p=0.7263728006497485, empirical=0.8947368421052632.
- `[0.8,0.9)`: n=5, mean_p=0.8109063428146566, empirical=1.0.
- `[0.9,1.0]`: n=0, mean_p=None, empirical=None.

## V2_INTERNAL_HGBR_V1

Pooled feature-valid UP rate `0.523932` over `48951` feature-valid scorable rows; pooled full-fold UP rate `0.526179`.

Full-probability Brier `0.254589464`; matched training-base-rate Brier `0.249826567`. Action mean p_up `0.626944098`; empirical LONG win rate `0.514525500`; calibration gap `0.112418598`.

Bootstrap retained `10000` and discarded `0` (`0.000000`); support `STABLE`.

| fold | feature-valid N | feature-valid coverage | LONG N | action coverage | win rate | full-fold UP | feature-valid UP | enrichment |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2019 | 7665 | 0.883777 | 232 | 0.030267 | 0.577586 | 0.521910 | 0.523617 | 0.055677 |
| 2020 | 7484 | 0.858946 | 0 | 0.000000 | n/a | 0.580741 | 0.588589 | n/a |
| 2021 | 7742 | 0.889987 | 2866 | 0.370189 | 0.509421 | 0.521784 | 0.508137 | -0.012363 |
| 2022 | 8737 | 1.000000 | 0 | 0.000000 | n/a | 0.469154 | 0.469154 | n/a |
| 2023 | 8565 | 0.980763 | 0 | 0.000000 | n/a | 0.526394 | 0.524343 | n/a |
| 2024 | 8760 | 1.000000 | 0 | 0.000000 | n/a | 0.537162 | 0.537162 | n/a |

Advancement gates:

- `POOLED_ACTION_COVERAGE_AT_LEAST_0_02`: PASS (observed `0.06328519191877924`, threshold `0.02`).
- `EVERY_FOLD_ACTION_COVERAGE_AT_LEAST_0_005`: FAIL (observed `0.0`, threshold `0.005`).
- `POOLED_ACTIONABLE_LONGS_AT_LEAST_500`: PASS (observed `3098`, threshold `500`).
- `EVERY_FOLD_ACTIONABLE_LONGS_AT_LEAST_30`: FAIL (observed `0`, threshold `30`).
- `POOLED_SELECTIVE_LONG_WIN_RATE_AT_LEAST_0_60`: FAIL (observed `0.5145255003227889`, threshold `0.6`).
- `POOLED_ENRICHMENT_OVER_FULL_FOLD_UP_RATE_AT_LEAST_0_05`: FAIL (observed `-0.011653460929672232`, threshold `0.05`).
- `ENRICHMENT_INTERVAL_LOWER_BOUND_ABOVE_ZERO`: FAIL (observed `-0.07010844923126111`, threshold `0.0`).
- `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE_ENRICHMENT`: FAIL (observed `1`, threshold `4`).
- `FULL_PROBABILITY_BRIER_AT_MOST_MATCHED_TRAINING_UP_BASE_RATE_BRIER`: FAIL (observed `0.2545894635119248`, threshold `0.24982656709472292`).
- `ACTION_CALIBRATION_GAP_AT_MOST_0_05`: FAIL (observed `0.11241859779546182`, threshold `0.05`).

Actionable reliability bins:

- `[0.0,0.1)`: n=0, mean_p=None, empirical=None.
- `[0.1,0.2)`: n=0, mean_p=None, empirical=None.
- `[0.2,0.3)`: n=0, mean_p=None, empirical=None.
- `[0.3,0.4)`: n=0, mean_p=None, empirical=None.
- `[0.4,0.5)`: n=0, mean_p=None, empirical=None.
- `[0.5,0.6)`: n=0, mean_p=None, empirical=None.
- `[0.6,0.7)`: n=3090, mean_p=0.6267379041435139, empirical=0.5135922330097087.
- `[0.7,0.8)`: n=8, mean_p=0.7065865208602711, empirical=0.875.
- `[0.8,0.9)`: n=0, mean_p=None, empirical=None.
- `[0.9,1.0]`: n=0, mean_p=None, empirical=None.

## Integrity and boundaries

Admission identity: `a1de4a3158472151a1c9bdcafc30b8c3a9b4f218bf74a9fff0c75d2ce04a1f54`. Both planned configurations were consumed; none remains and no fork was taken. The ten Generation V1 result files, the two first-family V2 result files and the V2 calendar family report all replay byte-identically. No V1 model output was loaded and the Stage-1 substrate debt remains unrepaired.
