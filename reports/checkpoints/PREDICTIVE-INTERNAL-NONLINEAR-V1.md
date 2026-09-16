# Predictive internal nonlinear V1

The reserved second configuration of `PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1`.
`EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD` tested `H-PRED-INT-002` —
`INTERNAL_HGBR_DUAL_HEAD_V1` — against the matched `ALWAYS_UP` control on the frozen
2019–2024 outer folds.

Terminal classification: **`NO_ADVANCE_INTERNAL_HGBR_V1`**. All five predeclared gates
failed. Stage-1 is now **closed**: 2 of 2 configurations executed, 0 reserved. Full numbers:
`reports/research/PREDICTIVE-INTERNAL-NONLINEAR-V1.md` and its JSON; the immutable record is
`research/experiments/EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD/`.

## The coverage ruling came before the result

The Research Director took **option 1 — execute unchanged**, and the ruling is recorded in
the preregistration, the admission artifact and the result, all committed in `5b24c02`,
before any HGBR outer-evaluation number existed.

What the ruling says, and what it deliberately does not: the reserved configuration is
executed exactly as frozen; the feature set, the feature-validity rules and the coverage
thresholds are unchanged; the two coverage gates are known in advance to be structurally
unpassable on this substrate, because the candidate abstains on exactly the timestamps the
linear configuration abstained on. It waives nothing, reinterprets nothing and removes
nothing. All five conditions remain all-must-hold, so no directional result could have
produced formal advancement while coverage fails. The directional delta, the calibration and
the magnitude error stay scientifically informative on the feature-available subset, and no
window-rule, gap-policy, threshold, feature or parameter rescue is authorized.

A dedicated test asserts the gate still binds: a synthetic case with coverage 0.80 and a
delta of +0.25 inside a strictly positive interval still classifies `NO_ADVANCE`.

## What was run

The configuration frozen in `54dc831`, unchanged: `HistGradientBoostingClassifier` and
`HistGradientBoostingRegressor` with learning_rate 0.05, max_iter 200, max_leaf_nodes 15,
min_samples_leaf 50, l2_regularization 1.0, max_bins 255, early_stopping False,
random_state 20260916, squared-error loss on the magnitude head.

Everything else is inherited from the linear configuration rather than rebuilt: the same 18
causal features, the same validity rules, the same folds, the same 80% split with a 48h
embargo, the same training-only Platt map from the base model's raw `decision_function`
score, the same action rule and the same scoring semantics. The nonlinear checkpoint imports
those steps from the linear module rather than copying them, and its admission artifact
hashes the linear implementation files too — so if any of them had changed, the run would
have failed closed instead of quietly comparing two different procedures.

18 model fits: six direction base, six Platt calibration, six magnitude.

## The result

Pooled over 52,315 eligible timestamps: candidate win rate **0.4896** on 48,951 actionable
predictions at coverage **0.9357**, with 3,362 counted abstentions. Matched `ALWAYS_UP` on
the identical timestamps **0.5239**. Primary delta **−0.0343**, paired 97.5% fold-stratified
moving-block interval **[−0.0575, −0.0100]** — entirely below zero.

| condition | threshold | observed | passed |
| --- | --- | --- | --- |
| pooled coverage | ≥ 0.95 | 0.9357 | no |
| every fold coverage | ≥ 0.90 | 0.8589 | no |
| pooled matched delta | ≥ +0.015 | −0.0343 | no |
| paired interval lower bound | > 0 | −0.0575 | no |
| folds with delta ≥ 0 | ≥ 4 of 6 | 1 | no |

Per fold: 2019 −0.030, 2020 −0.177, 2021 −0.002, 2022 +0.020, 2023 −0.020, 2024 −0.013. Only
2022 is positive. As with the linear candidate, the worst fold is 2020, where `ALWAYS_UP`
itself scored 0.589 and the candidate 0.411.

Calibration: Brier 0.2546, with 44,181 of 48,951 predictions in `[0.5,0.6)` at mean predicted
0.535 against 0.489 empirical, and 4,759 in `[0.6,0.7)` at mean 0.630 against **0.497**
empirical. The boosted head is more confident than the linear one and no more right; the
`[0.6,0.7)` bin is essentially a coin flip sold at 63%. The 11 records in `[0.7,0.8)` are too
few to read.

Magnitude: MAE 2.4081 pp (240.81 bps), median absolute error 1.6135 pp over the 48,953
feature-available rows. `ZERO_RETURN_MAGNITUDE` scored 2.2635 pp on the full universe and the
linear ridge 2.3042 pp, so the boosted magnitude head is the worst of the three. Signed
magnitude-match mean −0.22 over 48,070 included records (`ABSTAINED_MAGNITUDE` 880,
`NEAR_ZERO_BOTH` 1, `NEUTRAL_REALIZED` 2).

## Nonlinearity bought nothing

The comparison against the linear configuration is descriptive and was preregistered as
descriptive: the family's alpha is allocated to two candidate-versus-baseline tests, and a
candidate-versus-candidate interval would consume multiplicity the family does not have.

To make the comparison trustworthy the linear configuration was **replayed inside this run**
on the same feature cache, with 18 replayed fits that consume no Stage-1 budget, and it
reproduced its committed win rate, coverage and Brier score exactly —
`independent_reconciliation: PASS`.

| quantity | linear | nonlinear |
| --- | --- | --- |
| pooled win rate | 0.4888 | 0.4896 |
| pooled coverage | 0.93570 | 0.93570 |
| matched delta | −0.0351 | −0.0343 |
| Brier score | 0.2534 | 0.2546 |
| magnitude MAE pp | 2.3042 | 2.4081 |

The two configurations declared a side on the identical 48,953 timestamps and agreed on
39,038 of them — an agreement rate of 0.7975. So the boosted head disagrees with the linear
head one time in five, and those disagreements bought +0.0008 of win rate while costing
calibration and magnitude accuracy. Both remain far below the matched control. The honest
reading is that the added capacity fitted noise: on the same 18 causal internal features,
over the same folds, nonlinearity did not recover directional information the linear
configuration missed.

## Coverage failed for the same substrate reason, and only that reason

5,106 of 64,323 admissible labels have no feature vector: `LOOKBACK_BAR_MISSING` 3,147 and
`LOOKBACK_BAR_INCOMPLETE` 1,959 — identical to the linear checkpoint, because the validity
rules are identical. Coverage by fold is 0.884, 0.859, 0.890, 1.000, 0.981, 1.000; the
canonical substrate is materially gappier before 2022. The abstention sets of the two
configurations are provably identical, which is exactly what the pre-execution ruling
predicted.

## Validation and accounting

Backend tests, `check.py --no-data`, ruff, format, mypy and frontend validation all pass. The
committed result replays byte-identically against the installed market data.

Stage-1 budget: 2 of 2 consumed, 0 remaining, family
`CLOSED_BOTH_PREDECLARED_CONFIGURATIONS_EXECUTED`. Model fits 18, plus 18 replay fits that
consume no budget. Sealed queries 0. No external information family. No post-cutoff data.
`PREDICTIVE-BASELINES-V1` and `PREDICTIVE-INTERNAL-STRUCTURE-V1` results unchanged;
historical terminal classifications unchanged; `PREVIOUS_24H_SIGN_PERSISTENCE` was not
inverted or negated; no tuned descendant of either configuration exists. Champion `NONE`,
real money `false`.

## Next

Stage 1 is answered and closed. Two predeclared configurations, one linear and one nonlinear,
on 18 causal internal price/volume/volatility features, both scored below the matched
`ALWAYS_UP` control with multiplicity-adjusted intervals entirely below zero. Nothing in this
family advances, and no descendant of it is authorized.

The open items are for the Research Director, not the executor:

1. whether the canonical hourly substrate's gap structure should be repaired or the feature
   window relaxed — a substrate decision, preregistered separately, never a rescue of these
   two results;
2. whether Stage 2 of `PREDICTIVE_SOURCE_ROADMAP_V1` should open a new information family
   now that internal structure alone has been tested and rejected.

`state/current_state.json` records the next checkpoint as
`RESEARCH_DIRECTOR_REVIEW_STAGE_1_CLOSURE`.
