# Predictive internal structure V1

The first result-bearing experiment of `PREDICTIVE_RESEARCH_GENERATION_V1`.
`EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD` tested `H-PRED-INT-001` —
`INTERNAL_LINEAR_DUAL_HEAD_V1` — against the matched `ALWAYS_UP` control on the frozen
2019–2024 outer folds.

Terminal classification: **`NO_ADVANCE_INTERNAL_LINEAR_V1`**. All five predeclared gates
failed. Full numbers: `reports/research/PREDICTIVE-INTERNAL-STRUCTURE-V1.md` and its JSON;
the immutable record is `research/experiments/EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD/`.

## The design was frozen before the first candidate number existed

The Stage-1 family, the preregistration and the implementation were committed in
`54dc831` — one commit before any outer-evaluation number was computed. The admission
artifact `reports/validation/PREDICTIVE-INTERNAL-STRUCTURE-V1-ADMISSION.json` hashes the
search plan, the preregistration and the nine implementation files, and repository
validation recomputes those hashes on every run, so the design cannot be edited to fit the
result without the check failing. Admission identity
`092e6761e0cdc31a6d489ff8af4ef08906398834bfad885ca3ef572c8f6ff18f`.

The reserved `INTERNAL_HGBR_DUAL_HEAD_V1` configuration was frozen in the same commit, in
full, so the linear result could not shape it. It was not executed.

## What was run

Eighteen causal features on completed canonical 1h OHLCV bars — signed returns at 1/6/24/72/168h,
realized volatility at 6/24/72/168h, signed efficiency at 24/72/168h, up fraction at 24/168h,
close position in the 24/168h range, and two volume features. The maximum lookback requires
169 contiguous complete bars, `T-168h` through `T`.

Direction head: `StandardScaler` plus `LogisticRegression(l2, C=1.0)` on the first 80% of
each fold's feature-valid training rows, with a 48h embargo, then a training-only Platt map
fitted on the remaining calibration rows. Magnitude head: `StandardScaler` plus
`Ridge(alpha=1.0)` on every feature-valid training row. 18 model fits in total — six of
each — no hyperparameter search, no threshold search, no feature search.

## The result

Pooled over 52,315 eligible timestamps: candidate win rate **0.4888** on 48,951 actionable
predictions at coverage **0.9357**, with 3,362 counted abstentions. Matched `ALWAYS_UP` on
the identical timestamps **0.5239**. Primary delta **−0.0351**, paired 97.5% fold-stratified
moving-block interval **[−0.0608, −0.0080]**.

The interval lies entirely below zero. This is not "no evidence of skill"; it is evidence
that this candidate is worse than always predicting UP, at a multiplicity-adjusted level.

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| pooled coverage | ≥ 0.95 | 0.9357 | no |
| every fold coverage | ≥ 0.90 | 0.8589 | no |
| pooled matched delta | ≥ +0.015 | −0.0351 | no |
| paired interval lower bound | > 0 | −0.0608 | no |
| folds with delta ≥ 0 | ≥ 4 of 6 | 2 | no |

Per fold, the deltas are 2019 −0.047, 2020 −0.156, 2021 +0.001, 2022 +0.042, 2023 −0.049,
2024 −0.017. The single worst fold is 2020, where `ALWAYS_UP` itself scored 0.589 and the
candidate 0.433 — the candidate was most wrong exactly where the unconditional drift was
strongest.

Calibration is honest but almost flat: Brier 0.2534, with 45,399 of 48,951 predictions in
the `[0.5,0.6)` bin at mean predicted 0.536 against 0.485 empirical. The model is
systematically over-confident in a direction it does not have. The few high-probability
bins are too small to interpret: 89 records in `[0.7,0.8)`, 5 in `[0.8,0.9)`.

Magnitude: MAE 2.3042 pp (230.42 bps), median absolute error 1.5308 pp, over the 48,953
feature-available rows; the 3,362 abstained rows declare no magnitude and are excluded and
counted. `ZERO_RETURN_MAGNITUDE` scored 2.2635 pp on the full universe, so the ridge head is
**worse than predicting zero**. The signed magnitude-match mean is −1.12 over 48,004 included
records, with `ABSTAINED_MAGNITUDE` 940, `NEAR_ZERO_BOTH` 7, `NEUTRAL_REALIZED` 2.

None of this rescues anything, and none of it was allowed to. The gate is directional and
primary; calibration and magnitude are companions.

## Coverage failed for a data reason, not a model reason

The candidate abstains only when the frozen 169-bar causal window cannot be constructed.
5,106 of 64,323 admissible labels have no feature vector: `LOOKBACK_BAR_MISSING` 3,147 and
`LOOKBACK_BAR_INCOMPLETE` 1,959. A single missing or incomplete canonical hourly bar
invalidates the next 169 decision instants, so the 329 inadmissible labels reported by
`PREDICTIVE-BASELINES-V1` become two orders of magnitude more unavailable feature vectors.

The damage is concentrated early: 2019 coverage 0.884, 2020 0.859, 2021 0.890, then 2022
1.000, 2023 0.981, 2024 1.000. The canonical substrate is materially gappier before 2022.

This is a real and useful finding, and it was not anticipated when the 0.95/0.90 coverage
gates were frozen. It is recorded, not repaired: changing the window rule, the gap policy or
the coverage gate after seeing this result would be exactly the post-result adaptation the
protocol forbids. The Research Director may decide whether any Stage-1 successor needs a
different treatment of canonical gaps, as a preregistered decision.

## What was proven rather than asserted

Causality is proven on synthetic bars: the causal surface is exactly the 169 bars up to `T`;
mutating every bar after `T` cannot move a value; a bar before the maximum lookback cannot
move anything; each signed lookback reads exactly its own origin close and each rolling
window spans exactly the hours it claims; the look-ahead guard fires on the real code path.
Every edge rule is exercised — a missing or incomplete bar, a non-positive close, a negative
volume, a zero mean volume, a zero decision volume, the zero-efficiency-denominator value
0.0 and the zero-range close-position value 0.5.

Fitting separation is proven, not described: perturbing rows on the calibration side leaves
the base coefficients bit-identical while the Platt map moves, and perturbing rows inside the
48h embargo moves neither.

The paired bootstrap is proven on fixtures whose answers are degenerate by construction: a
fold whose timeline is exactly one block long has one legal start, so every replicate
reproduces that fold exactly. Two such folds side by side reproduce the pooled delta with a
zero-width interval, which would be impossible if a block could straddle the fold boundary.
A fold with records at hours 0 and 10 keeps an 11-hour timeline, which would be impossible if
abstentions were compressed into adjacency.

A tamper test confirms the validator rejects a result whose gate verdict was edited after the
fact: the gate is recomputed from the reported numbers, never read from the classification
string beside them.

## Validation and accounting

Backend tests, `check.py --no-data`, ruff, format, mypy and frontend validation all pass. The
committed result replays byte-identically against the installed market data.

Stage-1 budget: 1 of 2 configurations consumed, 1 reserved. Model fits 18. Sealed queries 0.
No external information family. No post-cutoff data. `PREDICTIVE-BASELINES-V1` results
unchanged; historical terminal classifications unchanged; `PREVIOUS_24H_SIGN_PERSISTENCE` was
not inverted or negated. Champion `NONE`, real money `false`.

## Next

`PREDICTIVE-INTERNAL-NONLINEAR-V1`: execute the reserved `INTERNAL_HGBR_DUAL_HEAD_V1`
configuration, unchanged, on the identical features, folds, calibration split, action rule
and scoring semantics. It is scheduled regardless of this result and consumes the second and
last Stage-1 configuration. No tuned descendant of the linear candidate is authorized.
