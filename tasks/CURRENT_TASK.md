# CURRENT TASK — PREDICTIVE-INTERNAL-STRUCTURE-V1

Status: ACTIVE_PREDICTIVE_MODELLING_RESEARCH_DIRECTOR_FROZEN

Starting HEAD: `e31728210d470c52ab68cfa2a322cf568d0e20e2` on `main`.

Predecessor: `PREDICTIVE-BASELINES-V1` — Research Director review: **ACCEPTED**.
The frozen reference bar is `ALWAYS_UP` at 0.5262 pooled development win rate; 0.5 is not
the relevant bar. `PREVIOUS_24H_SIGN_PERSISTENCE` being sub-50% is an observed baseline
fact and may not be inverted or otherwise exploited in this checkpoint.

Governing documents:

- `governance/SCIENTIFIC_CONSTITUTION.md` Version 2.0;
- `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md`, Amendment A1;
- `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`, Stage 1;
- `research/protocols/PREDICTIVE-BASELINES-V1.json`.

This is the first result-bearing predictive experiment of
`PREDICTIVE_RESEARCH_GENERATION_V1`. ChatGPT/Research Director freezes the scientific
design below before any candidate evaluation-fold prediction is observed. Coding agents
implement and validate it; they do not redesign it after seeing results.

Do not inspect sealed/post-cutoff BTC data. Do not admit an external information family.
Do not change the frozen label, fold, baseline, bin, bootstrap-block, or eligibility
semantics. Champion remains `NONE`; real money remains `false`.

## 1. Hypothesis and candidate

Experiment root hypothesis:

`H-PRED-INT-001 — INTERNAL_LINEAR_DUAL_HEAD_V1`

A fixed, causal, low-complexity predictor using only BTCUSDT's own price, volume and
volatility history contains directional information about the frozen 24h terminal target
beyond the `ALWAYS_UP` baseline.

Primary effect:

`candidate actionable directional win rate - matched ALWAYS_UP win rate`

where the matched baseline is scored on the exact timestamps on which the candidate makes
an actionable directional prediction.

Minimum important effect (MESI): **+0.015 absolute win-rate points** (+1.5 percentage
points) versus matched `ALWAYS_UP`.

No probability threshold is searched. When features are valid the candidate always declares
UP or DOWN. Abstention is permitted only because the frozen causal feature vector cannot be
constructed from valid contiguous history.

## 2. Stage-1 search family frozen before result

Create and freeze, before execution, a machine-readable search-plan record:

`research/protocols/PREDICTIVE-STAGE1-INTERNAL-SEARCH-PLAN-V1.json`

Family:

`PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1`

The family contains exactly **two** predeclared model configurations:

1. `INTERNAL_LINEAR_DUAL_HEAD_V1` — executed in this checkpoint;
2. `INTERNAL_HGBR_DUAL_HEAD_V1` — reserved for the next checkpoint and to be executed
   regardless of the linear result unless an integrity/software defect blocks execution.

No third Stage-1 model family, parameter rescue, threshold rescue or feature redesign is
authorized by this plan.

Familywise alpha = 0.05. Bonferroni allocation = 0.025 to each of the two configurations.
The paired primary-effect interval for this checkpoint therefore uses alpha 0.025
(a central 97.5% moving-block-bootstrap interval).

This checkpoint consumes exactly 1 of 2 planned Stage-1 model configurations.

Freeze the reserved HGBR configuration now so the linear result cannot influence it:

- exact same feature set, feature validity rules, folds, calibration split, action rule and
  scoring semantics as V1;
- direction head: `HistGradientBoostingClassifier`, learning_rate=0.05, max_iter=200,
  max_leaf_nodes=15, min_samples_leaf=50, l2_regularization=1.0, max_bins=255,
  early_stopping=False, fixed deterministic random_state=20260916;
- magnitude head: `HistGradientBoostingRegressor` with the same structural parameters,
  squared-error loss, early_stopping=False, random_state=20260916;
- direction probabilities calibrated by the same training-only Platt procedure defined
  below;
- no hyperparameter search.

Do **not** execute the HGBR candidate in this checkpoint.

## 3. Exact causal feature set

Use completed canonical 1h OHLCV bars derived from the existing canonical 1m development
substrate. At decision bar open-time key `T`, the full bar `[T,T+1h)` is completed and may
be used. No bar whose open time is after `T` may enter a feature.

Let `c_t`, `h_t`, `l_t`, `v_t` be close/high/low/volume of completed hour `t`, and
`x_t = log(c_t / c_{t-1h})`.

Freeze exactly these 18 features, in this order:

1. `logret_1h = x_T`
2. `logret_6h = log(c_T / c_{T-6h})`
3. `logret_24h = log(c_T / c_{T-24h})`
4. `logret_72h = log(c_T / c_{T-72h})`
5. `logret_168h = log(c_T / c_{T-168h})`
6. `rv_6h = sqrt(sum(x^2 over the last 6 hourly returns ending T))`
7. `rv_24h = sqrt(sum(x^2 over the last 24 hourly returns ending T))`
8. `rv_72h = sqrt(sum(x^2 over the last 72 hourly returns ending T))`
9. `rv_168h = sqrt(sum(x^2 over the last 168 hourly returns ending T))`
10. `signed_efficiency_24h = logret_24h / sum(|x| over last 24h)`
11. `signed_efficiency_72h = logret_72h / sum(|x| over last 72h)`
12. `signed_efficiency_168h = logret_168h / sum(|x| over last 168h)`
13. `up_fraction_24h = fraction of the last 24 hourly returns strictly > 0`
14. `up_fraction_168h = fraction of the last 168 hourly returns strictly > 0`
15. `close_position_24h = (c_T - min(low,last24h)) / (max(high,last24h)-min(low,last24h))`
16. `close_position_168h = (c_T - min(low,last168h)) / (max(high,last168h)-min(low,last168h))`
17. `log_volume_relative_24h = log(v_T / mean(volume,last24h))`
18. `log_volume_regime_24_168h = log(mean(volume,last24h) / mean(volume,last168h))`

Deterministic edge rules:

- every required hourly bar in the maximum 168h lookback must exist and be complete;
- all closes used in logs must be strictly positive;
- volumes must be non-negative and every mean volume used as a denominator must be
  strictly positive;
- if an efficiency denominator is exactly zero, its feature value is 0.0;
- if a rolling high-low range is exactly zero, close-position is 0.5;
- otherwise any invalid/non-finite quantity makes the entire feature vector unavailable;
- unavailable evaluation features cause `NEUTRAL_UNCERTAIN` abstention and are counted;
- unavailable training rows are excluded from model fitting and counted;
- no interpolation, forward fill, backward fill, median fill or nearest-bar substitution.

Add deterministic causality tests for every lookback family and explicit leakage tests that
mutating bars after `T` cannot change the feature vector.

## 4. Fixed outer evaluation

Reuse the frozen expanding chronological 2019–2024 outer folds exactly. No re-cutting.
The outer evaluation portion remains unseen until the fold's candidate is completely
frozen and fit.

The canonical eligible-label universe remains unchanged. Candidate feature unavailability
is represented as abstention, not by deleting eligible timestamps from the denominator.

For headline candidate-versus-baseline comparison, score `ALWAYS_UP` on the exact
candidate-actionable, non-NEUTRAL timestamps as a paired control. Also report the canonical
full-universe baseline from PREDICTIVE-BASELINES-V1 unchanged for context.

## 5. Fixed inner fit/calibration procedure

For each outer fold, take only its chronological training portion and feature-valid rows.
No outer-evaluation row may influence fitting, scaling, calibration or strength.

Direction head procedure:

1. Sort outer-training feature-valid labels chronologically.
2. Let the calibration boundary `S` be the timestamp at index `floor(0.80 * N)` of those
   rows (0-based, clamped only to a valid in-range row; if either resulting side is
   scientifically unusable, fail closed — no alternative split).
3. Base-fit rows must satisfy `T + 48h <= S`. This creates the 24h label horizon plus a
   further 24h embargo before calibration begins.
4. Calibration rows satisfy `T >= S` and remain entirely inside outer training.
5. Fit `StandardScaler` on base-fit features only.
6. Fit fixed `LogisticRegression(penalty='l2', C=1.0, solver='lbfgs', fit_intercept=True,
   max_iter=2000, tol=1e-8, class_weight=None)` on scaled base-fit rows.
7. Obtain the base model's one-dimensional raw `decision_function` score on calibration
   rows.
8. Fit a Platt map using `LogisticRegression(penalty=None, solver='lbfgs',
   fit_intercept=True, max_iter=2000, tol=1e-8)` from that raw score to UP/DOWN truth.
9. Both base-fit and calibration subsets must contain both directional classes; otherwise
   fail the fold closed. Do not invent a fallback probability.
10. On outer evaluation, calibrated `p_up` comes only from this frozen pipeline.
11. Declare `UP` when `p_up >= 0.5`, else `DOWN`; ties go UP.
12. Exposed `probability = p_up` for UP and `1-p_up` for DOWN, i.e. always
    P(declared direction correct).

There is no probability-based abstention and no threshold search.

Magnitude head procedure:

- fit a separate `StandardScaler` on **all** feature-valid outer-training rows;
- fit `Ridge(alpha=1.0, fit_intercept=True)` on frozen `r_24h` log-return targets;
- `expected_return` is the signed predicted log return;
- no target clipping, winsorization or tuning.

Strength for an outer prediction is the deterministic empirical percentile rank of
`abs(expected_return)` against the absolute realized `r_24h` values from the full
feature-valid outer-training portion only:

`strength = 100 * count(train_abs_return <= abs(predicted_return)) / N_train`

with inclusive ties. Strength is descriptive and is never used to decide direction,
coverage or success.

## 6. Frozen scoring and primary inference

Mandatory reporting remains the complete Predictive Evaluation Contract:

- directional win rate, sample size, coverage;
- Brier score and fixed-bin reliability table for calibrated probabilities;
- signed-return MAE and median absolute error;
- signed magnitude-match diagnostic and exclusion counts;
- chronological per-fold results;
- baseline comparisons.

Primary comparison uses a **paired, fold-stratified moving-block bootstrap** on the original
hourly evaluation timeline:

- 48h contiguous blocks, matching the frozen dependency block length;
- 10,000 replicates;
- seed 20260916;
- resample blocks independently inside each outer fold, never across fold boundaries;
- preserve original timestamps/gaps rather than compressing abstentions into adjacency;
- within each replicate compute candidate win rate minus matched ALWAYS_UP win rate on
  candidate-actionable, non-NEUTRAL records;
- alpha 0.025 for this candidate's multiplicity allocation;
- report the central 97.5% percentile interval.

Synthetic tests must establish that the paired interval and delta calculation reproduce
hand-computed fixtures and do not cross fold or gap boundaries.

## 7. Predeclared advancement gate

`INTERNAL_LINEAR_DUAL_HEAD_V1` advances only if **all** are true:

1. pooled candidate coverage >= 0.95;
2. every outer fold coverage >= 0.90;
3. pooled matched win-rate delta versus ALWAYS_UP >= +0.015 absolute;
4. the multiplicity-adjusted paired 97.5% moving-block-bootstrap interval for the delta has
   lower bound > 0;
5. at least 4 of 6 outer folds have candidate-minus-matched-ALWAYS_UP win-rate delta >= 0.

If all pass:

`ADVANCE_INTERNAL_LINEAR_V1`

Otherwise:

`NO_ADVANCE_INTERNAL_LINEAR_V1`

with each failed gate reported explicitly. Secondary calibration or magnitude performance
may be scientifically informative but **cannot rescue** a failed primary directional gate.
Do not tune, invert, threshold, remove features or rerun a modified descendant after seeing
the result.

The reserved HGBR candidate remains scheduled regardless of the linear result.

## 8. Preregistration and no-peek sequence

Before producing any outer-evaluation candidate number:

1. create the Stage-1 search-plan record from §2;
2. create `research/experiments/<experiment_id>/preregistration.json` containing this exact
   hypothesis, feature list, model specifications, calibration split, primary effect, MESI,
   multiplicity allocation, coverage policy and advancement gate;
3. implement and pass all synthetic causality/evaluation tests;
4. produce a deterministic pre-execution admission artifact proving the preregistration and
   implementation hashes are frozen;
5. only then run the development-period outer evaluation once.

If implementation must change after a failed synthetic test but before market evaluation,
update the preregistration/hash and rerun the admission gate. Once any outer candidate
result is observed, scientific semantics are frozen and defects must be handled append-only
with Research Director review.

## 9. Boundaries

- Stage 1 internal canonical BTCUSDT data only.
- No post-cutoff or sealed data; sealed queries remain 0.
- No external/news/macro/derivatives/on-chain family.
- No change to PREDICTIVE-BASELINES-V1 results.
- No change to historical experiment terminal classifications.
- No change to ALIGNED semantics or its preserved evidence.
- `PREVIOUS_24H_SIGN_PERSISTENCE` may not be inverted or used to engineer a feature that is
  merely its negation in this checkpoint.
- No model-family or hyperparameter search beyond the two predeclared Stage-1
  configurations.
- Champion stays `NONE` regardless of result.
- Real money stays `false`.

## 10. Required artifacts

At minimum:

- `research/protocols/PREDICTIVE-STAGE1-INTERNAL-SEARCH-PLAN-V1.json`;
- one immutable experiment directory under `research/experiments/`;
- implementation under `backend/app/predictive/`;
- deterministic feature and scoring tests;
- pre-execution admission artifact with hashes;
- comparison report under `reports/research/`;
- one checkpoint report `reports/checkpoints/PREDICTIVE-INTERNAL-STRUCTURE-V1.md`;
- `state/current_state.json` updated once after result;
- `tasks/CURRENT_TASK.md` updated to the reserved HGBR checkpoint regardless of result;
- ADR only if an unexpected material architectural decision is genuinely required.

## 11. Validation

- backend tests PASS;
- frontend validation PASS if touched;
- `check.py --no-data` PASS;
- ruff / format / mypy PASS;
- deterministic result replay PASS when development data are installed;
- exact search-budget accounting;
- sealed queries 0;
- Champion `NONE`;
- real money `false`;
- clean tree;
- commit and push to `main`;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE INTERNAL STRUCTURE V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, Experiment ID, Hypothesis,
Preregistration/admission hash, Feature set, Model/calibration procedure, Model fits,
Candidate win rate + coverage, Matched ALWAYS_UP win rate, Primary delta + 97.5% paired
interval, Calibration, Magnitude error, Per-fold deltas/coverage, Advancement gates,
Terminal classification, Stage-1 search budget, Sealed queries, Champion, Real money,
Validation, Exact-head CI, Next action.
