# Predictive V2 deterministic calendar V1

Family disposition: **REJECTED_DEVELOPMENT_NO_SEALED**.

The frozen seven-feature vector is a pure function of the aware UTC decision timestamp. Causality proofs pass; feature validity is 1.0 on all six annual development folds. Magnitude is deferred, sealed queries are 0, Champion is `NONE`, and real money is false.

## Configuration results

| configuration | actionable N | coverage | selective win rate | full-fold UP rate | enrichment | 97.5% interval | classification |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `V2_CALENDAR_LINEAR_V1` | 3567 | 0.068183 | 0.526773 | 0.526179 | 0.000594 | [-0.059920, 0.063978] | `NO_ADVANCE_V2_CALENDAR_LINEAR_V1` |
| `V2_CALENDAR_HGBR_V1` | 2847 | 0.054420 | 0.529680 | 0.526179 | 0.003501 | [-0.062663, 0.071984] | `NO_ADVANCE_V2_CALENDAR_HGBR_V1` |

## V2_CALENDAR_LINEAR_V1

Full-probability Brier `0.253060611`; matched training-base-rate Brier `0.249722045`. Action mean p_up `0.614925114`; empirical LONG win rate `0.526773199`; calibration gap `0.088151915`.

Bootstrap retained `10000` and discarded `0` (`0.000000`); support `STABLE`.

| fold | LONG N | coverage | win rate | full-fold UP | enrichment |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2019 | 0 | 0.000000 | n/a | 0.521910 | n/a |
| 2020 | 37 | 0.004247 | 0.486486 | 0.580741 | -0.094255 |
| 2021 | 3530 | 0.405794 | 0.527195 | 0.521784 | 0.005411 |
| 2022 | 0 | 0.000000 | n/a | 0.469154 | n/a |
| 2023 | 0 | 0.000000 | n/a | 0.526394 | n/a |
| 2024 | 0 | 0.000000 | n/a | 0.537162 | n/a |

Advancement gates:

- `POOLED_ACTION_COVERAGE_AT_LEAST_0_02`: PASS (observed `0.06818312147567619`, threshold `0.02`).
- `EVERY_FOLD_ACTION_COVERAGE_AT_LEAST_0_005`: FAIL (observed `0.0`, threshold `0.005`).
- `POOLED_ACTIONABLE_LONGS_AT_LEAST_500`: PASS (observed `3567`, threshold `500`).
- `EVERY_FOLD_ACTIONABLE_LONGS_AT_LEAST_30`: FAIL (observed `0`, threshold `30`).
- `POOLED_SELECTIVE_LONG_WIN_RATE_AT_LEAST_0_60`: FAIL (observed `0.5267731987664704`, threshold `0.6`).
- `POOLED_ENRICHMENT_OVER_FULL_FOLD_UP_RATE_AT_LEAST_0_05`: FAIL (observed `0.0005942375140093326`, threshold `0.05`).
- `ENRICHMENT_INTERVAL_LOWER_BOUND_ABOVE_ZERO`: FAIL (observed `-0.059919720095041255`, threshold `0.0`).
- `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE_ENRICHMENT`: FAIL (observed `1`, threshold `4`).
- `FULL_PROBABILITY_BRIER_AT_MOST_MATCHED_TRAINING_UP_BASE_RATE_BRIER`: FAIL (observed `0.25306061097699667`, threshold `0.2497220450654606`).
- `ACTION_CALIBRATION_GAP_AT_MOST_0_05`: FAIL (observed `0.08815191546869094`, threshold `0.05`).

Actionable reliability bins:

- `[0.0,0.1)`: n=0, mean_p=None, empirical=None.
- `[0.1,0.2)`: n=0, mean_p=None, empirical=None.
- `[0.2,0.3)`: n=0, mean_p=None, empirical=None.
- `[0.3,0.4)`: n=0, mean_p=None, empirical=None.
- `[0.4,0.5)`: n=0, mean_p=None, empirical=None.
- `[0.5,0.6)`: n=0, mean_p=None, empirical=None.
- `[0.6,0.7)`: n=3567, mean_p=0.6149251142351614, empirical=0.5267731987664704.
- `[0.7,0.8)`: n=0, mean_p=None, empirical=None.
- `[0.8,0.9)`: n=0, mean_p=None, empirical=None.
- `[0.9,1.0]`: n=0, mean_p=None, empirical=None.

## V2_CALENDAR_HGBR_V1

Full-probability Brier `0.253733529`; matched training-base-rate Brier `0.249722045`. Action mean p_up `0.606307090`; empirical LONG win rate `0.529680365`; calibration gap `0.076626724`.

Bootstrap retained `10000` and discarded `0` (`0.000000`); support `STABLE`.

| fold | LONG N | coverage | win rate | full-fold UP | enrichment |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2019 | 0 | 0.000000 | n/a | 0.521910 | n/a |
| 2020 | 0 | 0.000000 | n/a | 0.580741 | n/a |
| 2021 | 2847 | 0.327279 | 0.529680 | 0.521784 | 0.007896 |
| 2022 | 0 | 0.000000 | n/a | 0.469154 | n/a |
| 2023 | 0 | 0.000000 | n/a | 0.526394 | n/a |
| 2024 | 0 | 0.000000 | n/a | 0.537162 | n/a |

Advancement gates:

- `POOLED_ACTION_COVERAGE_AT_LEAST_0_02`: PASS (observed `0.05442033833508554`, threshold `0.02`).
- `EVERY_FOLD_ACTION_COVERAGE_AT_LEAST_0_005`: FAIL (observed `0.0`, threshold `0.005`).
- `POOLED_ACTIONABLE_LONGS_AT_LEAST_500`: PASS (observed `2847`, threshold `500`).
- `EVERY_FOLD_ACTIONABLE_LONGS_AT_LEAST_30`: FAIL (observed `0`, threshold `30`).
- `POOLED_SELECTIVE_LONG_WIN_RATE_AT_LEAST_0_60`: FAIL (observed `0.5296803652968036`, threshold `0.6`).
- `POOLED_ENRICHMENT_OVER_FULL_FOLD_UP_RATE_AT_LEAST_0_05`: FAIL (observed `0.0035014040443425154`, threshold `0.05`).
- `ENRICHMENT_INTERVAL_LOWER_BOUND_ABOVE_ZERO`: FAIL (observed `-0.06266302397996246`, threshold `0.0`).
- `AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE_ENRICHMENT`: FAIL (observed `1`, threshold `4`).
- `FULL_PROBABILITY_BRIER_AT_MOST_MATCHED_TRAINING_UP_BASE_RATE_BRIER`: FAIL (observed `0.25373352905257046`, threshold `0.2497220450654606`).
- `ACTION_CALIBRATION_GAP_AT_MOST_0_05`: FAIL (observed `0.0766267243298`, threshold `0.05`).

Actionable reliability bins:

- `[0.0,0.1)`: n=0, mean_p=None, empirical=None.
- `[0.1,0.2)`: n=0, mean_p=None, empirical=None.
- `[0.2,0.3)`: n=0, mean_p=None, empirical=None.
- `[0.3,0.4)`: n=0, mean_p=None, empirical=None.
- `[0.4,0.5)`: n=0, mean_p=None, empirical=None.
- `[0.5,0.6)`: n=0, mean_p=None, empirical=None.
- `[0.6,0.7)`: n=2847, mean_p=0.6063070896266036, empirical=0.5296803652968036.
- `[0.7,0.8)`: n=0, mean_p=None, empirical=None.
- `[0.8,0.9)`: n=0, mean_p=None, empirical=None.
- `[0.9,1.0]`: n=0, mean_p=None, empirical=None.

## Integrity and boundaries

Admission identity: `91f47e036408b19c3023c508f61530bdcfba53525955566a16c2334b2bf97bcf`. Both planned configurations were consumed; none remains. All ten V1 result files, the macro source block and the residual source finding replay byte-identically. No V1 score or tail was used. This is a reconstructed deterministic calendar representation, not a claim about Ciclica Evoluta or Analisi Evoluta.
