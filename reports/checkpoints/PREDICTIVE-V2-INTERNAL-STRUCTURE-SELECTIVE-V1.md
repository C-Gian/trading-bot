# Checkpoint — PREDICTIVE-V2-INTERNAL-STRUCTURE-SELECTIVE-V1

Status: **COMPLETE — REJECTED_DEVELOPMENT_NO_SEALED**.

Starting HEAD `ea92e9b652b8296964b713ff0ae6b3e62209426a`. The second Generation V2
market-model family executed exactly the two preregistered configurations on all six frozen
annual development folds 2019–2024. Neither advanced. No sealed or post-cutoff data was
accessed; sealed queries remain 0, Champion remains `NONE`, real money remains `false`, and
magnitude remains `DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`.

## Pre-result freeze and feature reconciliation

Research Director decision: [ADR-0030](../../decisions/ADR-0030-PREDICTIVE-V2-INTERNAL-STRUCTURE-SELECTIVE.md),
which accepts the first V2 family as a negative result and opens exactly one new family.
Pre-result commit: `8d6de7e0ee8cd10e315b667ee82c1ece5ef2a03a`. It contains the immutable
decision, feature contract, implementation, proof tests, search plan, both preregistrations
and the admission; it contains 0 fits and 0 outer predictions.

Admission identity: `a1de4a3158472151a1c9bdcafc30b8c3a9b4f218bf74a9fff0c75d2ce04a1f54`.
Search plan SHA-256 `b3b111aee89dc1174ca310edd5fb4c625b3eec3e808700b77f33e483e82fe9fd`;
linear preregistration `5a672853d4f5c8f0858ecd69cf6cc6f6780421e72f4b0df56e896e2202b47913`;
HGBR preregistration `83b974f23b4a139db4f5c6b192eae17f3eb159eb3b47708d41ba8c0d6894feed`;
feature contract `bd43e903b29c6ec024a6c3248e3fa5e64b132ee37a805df46115546c96efbb87`;
ADR `1dcaeff7ed9984e85e0102a39f3f7da4567dc9477be80a825f84b4c5828387a3`.

The eighteen causal quantities are **inherited**, not transcribed:
`PREDICTIVE_V2_INTERNAL_CAUSAL_FEATURES_V1` names
`PREDICTIVE_INTERNAL_CAUSAL_FEATURES_V1` and calls its builder. Reconciliation on fixed
fixtures is identical. Causality proofs pass: future-bar mutation cannot move the vector at
`T`, a guarded bar index rejects any post-`T` read, the causal surface is exactly the 169
bars `T-168h .. T`, the 1h/6h/24h/72h/168h endpoints are exact, and the missing/incomplete
bar, non-positive close, negative volume and the two named degenerate denominators all match
the frozen V1 rule.

The Stage-1 substrate debt is **deferred and unrepaired**. Feature validity is 0.920619 over
64,323 admissible development labels and 0.935735 over 52,315 outer-fold timestamps;
5,106 development rows are unavailable (3,147 `LOOKBACK_BAR_MISSING`, 1,959
`LOOKBACK_BAR_INCOMPLETE`). Every unavailable row is counted and excluded from every rate,
never imputed, and no fold was removed for low availability.

## Frozen procedures

`V2_INTERNAL_LINEAR_V1` used `StandardScaler + LogisticRegression` with the frozen L2
parameters. `V2_INTERNAL_HGBR_V1` used the frozen `HistGradientBoostingClassifier` parameters
and seed 20260922. Each fold used expanding chronological training over feature-valid rows
only, the frozen 24h purge/embargo, a chronological 80% base fit / 20% calibration split, a
48h calibration embargo, and a training-only unpenalized logistic Platt map on the raw
decision score. Each configuration consumed 12 fits (6 base classifiers and 6 calibrators);
family total 24. No hyperparameter, feature or threshold search occurred. Exactly
`p_up >= 0.60` acted `LONG`.

## Pooled results

| configuration | feature-valid N | coverage | LONG N | action coverage | LONG win rate | full-fold UP | feature-valid UP | enrichment | 97.5% paired interval | Brier / control | mean p / gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Linear | 48,953 | 0.935735 | 3,321 | 0.067841 | 0.549533 | 0.526179 | 0.523932 | +0.023354 | [-0.032945, 0.076516] | 0.253403 / 0.249827 | 0.629621 / 0.080087 |
| HGBR | 48,953 | 0.935735 | 3,098 | 0.063285 | 0.514526 | 0.526179 | 0.523932 | -0.011653 | [-0.070108, 0.049119] | 0.254589 / 0.249827 | 0.626944 / 0.112419 |

Both 10,000-replicate, 48h fold-stratified paired bootstraps retained all replicates: 0
discarded, share 0.0, support `STABLE`.

## Per-fold results

| configuration | fold | feature-valid N | feature-valid coverage | LONG N | action coverage | win rate | full-fold UP | feature-valid UP | enrichment |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Linear | 2019 | 7,665 | 0.883777 | 0 | 0.000000 | n/a | 0.521910 | 0.523617 | n/a |
| Linear | 2020 | 7,484 | 0.858946 | 34 | 0.004543 | 0.441176 | 0.580741 | 0.588589 | -0.139565 |
| Linear | 2021 | 7,742 | 0.889987 | 3,281 | 0.423792 | 0.550137 | 0.521784 | 0.508137 | +0.028353 |
| Linear | 2022 | 8,737 | 1.000000 | 6 | 0.000687 | 0.833333 | 0.469154 | 0.469154 | +0.364179 |
| Linear | 2023 | 8,565 | 0.980763 | 0 | 0.000000 | n/a | 0.526394 | 0.524343 | n/a |
| Linear | 2024 | 8,760 | 1.000000 | 0 | 0.000000 | n/a | 0.537162 | 0.537162 | n/a |
| HGBR | 2019 | 7,665 | 0.883777 | 232 | 0.030267 | 0.577586 | 0.521910 | 0.523617 | +0.055677 |
| HGBR | 2020 | 7,484 | 0.858946 | 0 | 0.000000 | n/a | 0.580741 | 0.588589 | n/a |
| HGBR | 2021 | 7,742 | 0.889987 | 2,866 | 0.370189 | 0.509421 | 0.521784 | 0.508137 | -0.012363 |
| HGBR | 2022 | 8,737 | 1.000000 | 0 | 0.000000 | n/a | 0.469154 | 0.469154 | n/a |
| HGBR | 2023 | 8,565 | 0.980763 | 0 | 0.000000 | n/a | 0.526394 | 0.524343 | n/a |
| HGBR | 2024 | 8,760 | 1.000000 | 0 | 0.000000 | n/a | 0.537162 | 0.537162 | n/a |

Action concentrates in a single fold for both configurations — 2021 for Linear, 2021 with a
small 2019 block for HGBR — and four to five folds abstain completely. The Linear 2022 fold
shows the failure mode the count floors exist to catch: a 0.833333 win rate over six
actionable hours, which gate 4 refuses before its win rate is ever weighed.

The full report preserves the fixed V1 actionable-LONG reliability bins. For both
configurations gates 1 (pooled coverage) and 3 (pooled N) passed; gates 2 and 4–10 failed:
per-fold coverage, per-fold N, pooled 0.60 win rate, +0.05 enrichment, positive interval
lower bound, four non-negative folds, Brier no worse than the training base rate, and action
calibration gap <= 0.05. Classifications are `NO_ADVANCE_V2_INTERNAL_LINEAR_V1` and
`NO_ADVANCE_V2_INTERNAL_HGBR_V1`; both are `NOT_ELIGIBLE_REJECTED_DEVELOPMENT`.

Neither configuration was rescued by a secondary metric. The Linear pooled enrichment of
+0.023354 is the family's strongest directional signal and it is less than half the
predeclared +0.05, with an interval that comfortably contains zero.

## Closure and integrity

The two-configuration search budget is fully consumed with 0 remaining and 0 result-dependent
forks. Family disposition is `REJECTED_DEVELOPMENT_NO_SEALED`. All ten Generation V1 result
artifacts, both first-family V2 result artifacts and the V2 calendar family report remain
byte-identical. No V1 probability score, tail, reliability bin or action reconstruction was
used: the V2 modules import no Generation V1 fitting or prediction module, and no function on
the execution path opens a result artifact at all. The complete family and trial artifacts
replay byte-identically from installed development data.

Next: `RESEARCH_DIRECTOR_REVIEW_PREDICTIVE_V2_INTERNAL_STRUCTURE_SELECTIVE_V1`; no third V2
family is authorized automatically.
