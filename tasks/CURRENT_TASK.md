# CURRENT TASK — PREDICTIVE-STAGE2-SETTLED-FUNDING-V1

Status: ACTIVE_PREDICTIVE_STAGE2_RESEARCH_DIRECTOR_FROZEN

Starting HEAD: `0b84d690397a451af567450562dc762ac90fbed0` on `main`.

Predecessor: `PREDICTIVE-INTERNAL-NONLINEAR-V1` — Research Director review: **ACCEPTED**.
Exact-head CI `35157729753` is green.

## Research Director Stage-1 closure decisions

These decisions are final for this checkpoint and must be recorded in state/checkpoint artifacts.

1. `PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1` is **REJECTED_DEVELOPMENT**. Both frozen
   configurations were materially worse than their matched `ALWAYS_UP` control and both
   multiplicity-adjusted paired intervals were entirely below zero. Neither configuration is
   eligible for sealed evaluation. Record:
   - family disposition: `REJECTED_DEVELOPMENT_NO_SEALED`;
   - linear sealed eligibility: `NOT_ELIGIBLE_REJECTED_DEVELOPMENT`;
   - HGBR sealed eligibility: `NOT_ELIGIBLE_REJECTED_DEVELOPMENT`.
   This rejects only the defined two-configuration Stage-1 family, not the proposition that
   all possible internal BTC information is useless.
2. Do **not** repair canonical hourly gaps and do **not** relax the frozen 169-bar contiguity
   rule now. The coverage defect is real, but it does not explain the negative directional
   result: both candidates were below the matched baseline with intervals wholly below zero.
   Treat the gap/contiguity issue as deferred substrate debt, not as a rescue path. A future
   independent protocol may revisit it only if scientifically justified on its own terms.
3. Open Stage 2 of `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`. The first Stage-2
   information family is **settled BTCUSDT perpetual funding structure**, using the already
   canonical point-in-time funding dataset. Do not acquire or admit open interest, basis,
   position ratios, CFTC, macro, news, or any other source in this checkpoint.

Champion remains `NONE`. Real money remains `false`.

## 1. Scientific question

Family:

`PREDICTIVE_STAGE2_SETTLED_FUNDING_FAMILY_V1`

Root hypothesis:

`H-PRED-FUND-001 — CAUSAL_SETTLED_FUNDING_STRUCTURE_ADDS_24H_DIRECTIONAL_INFORMATION`

Question: does strictly prior, already-settled BTCUSDT USD-M perpetual funding history contain
credible out-of-sample information about the frozen BTCUSDT spot 24h terminal direction,
relative to an information-free chronological control and the canonical `ALWAYS_UP` baseline?

Historical WP-015 results from the superseded cost-expectancy generation are preserved but
are **not** evidence for this predictive hypothesis and must not be used to choose the design.
Only its source-integrity tooling and canonical funding data may be reused.

## 2. Frozen source and point-in-time semantics

Reuse without rewriting:

- `data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json`;
- canonical artifact `data/derived/BTCUSDT-USDM-settled-funding-v1.parquet`;
- source records: `funding_time`, `funding_rate` only;
- existing credential-free Binance USD-M acquisition provenance.

Create a new predictive contract, e.g.
`docs/contracts/PREDICTIVE_SETTLED_FUNDING_STRUCTURE_V1.md`, without changing the old
`PERPETUAL_FUNDING_CONTEXT_V1` historical contract.

At prediction decision timestamp `T`, a funding record is available only when
`funding_time < T` exactly. A record timestamped exactly `T` is unavailable. Never use
predicted funding, mark price, premium, basis, open interest, position ratios, or any field
not present in the canonical artifact.

No interpolation or forward filling across a funding gap is allowed. For the feature vector
below, the last nine strictly-prior funding settlements must exist and every consecutive gap
inside those nine records must be <= 8 hours + 60 seconds. Otherwise the funding feature
vector is unavailable and the timestamp is an explicit counted abstention.

## 3. Frozen funding feature set

Feature version:

`PREDICTIVE_SETTLED_FUNDING_FEATURES_V1`

Exactly five features, in this order, derived only from the last nine valid strictly-prior
settlements:

1. `LATEST_SETTLED_RATE` — most recent strictly-prior funding rate;
2. `MEAN_LAST_3_SETTLEMENTS` — arithmetic mean of the last 3 rates;
3. `MEAN_LAST_9_SETTLEMENTS` — arithmetic mean of the last 9 rates;
4. `DELTA_LATEST_PREVIOUS` — latest rate minus immediately previous rate;
5. `STD_LAST_9_SETTLEMENTS` — population standard deviation of the last 9 rates.

No other transform, clipping, sign flag, interaction, rolling window, threshold, momentum,
calendar variable, spot-price feature, or Stage-1 internal feature is authorized.

This intentionally avoids the rejected Stage-1 169-bar feature-validity rule. The Stage-1
substrate issue is therefore neither repaired nor inherited.

## 4. Evaluation universe and folds

Frozen target, labels, NEUTRAL handling, scorer, reliability bins, bootstrap seed/block rules
and economic-layer separation remain those of `PREDICTIVE_EVALUATION_CONTRACT_V1` Amendment
A1 and `PREDICTIVE-BASELINES-V1` unless explicitly narrowed below for source availability.

The Stage-2 source begins in September 2019, so 2019 is training/warmup only for this family.
Outer evaluation folds are exactly calendar years **2020, 2021, 2022, 2023, 2024**.

For each fold:

- use expanding chronological training data strictly before the fold;
- retain the canonical 24h label purge/embargo at every boundary;
- require a valid five-feature funding vector;
- score the candidate and all matched controls on identical timestamps;
- every source-unavailable timestamp inside an otherwise admissible evaluation label universe
  is counted explicitly as an abstention/source-availability exclusion;
- do not redefine folds or source eligibility after observing a result.

Standard random K-fold is forbidden.

## 5. Frozen matched controls

The family has no previously admitted predictive feature family. Its matched information-free
control is therefore the canonical training-only base-rate predictor, refit separately inside
each fold on the same source-eligible training universe:

`MATCHED_TRAINING_UP_BASE_RATE`

Semantics are Amendment A1: compute training `p_up`, declare the majority direction, use
`p_up` when UP is declared and `1-p_up` when DOWN is declared, tie `p_up >= 0.5 -> UP`.

Also score `ALWAYS_UP`, `PREVIOUS_24H_SIGN_PERSISTENCE`, and `ZERO_RETURN_MAGNITUDE` on the
identical evaluation timestamps where their declared quantity applies. Never invert the
observed persistence baseline.

Primary effect for each candidate:

`candidate directional win rate - matched MATCHED_TRAINING_UP_BASE_RATE win rate`

Secondary absolute reference:

`candidate directional win rate - matched ALWAYS_UP win rate`

## 6. Search family frozen before any Stage-2 result

Create before execution:

`research/protocols/PREDICTIVE-STAGE2-SETTLED-FUNDING-SEARCH-PLAN-V1.json`

The family contains exactly **two** model configurations. Both are executed in this single
work package regardless of the first result unless an integrity/software defect makes the
second impossible. No result-dependent early stop.

### Configuration A — FUNDING_LINEAR_DUAL_HEAD_V1

Experiment id:

`EXP-PRED-003-FUNDING-LINEAR-DUAL-HEAD`

Direction base head:

- `StandardScaler` fitted on base-fit rows only;
- `LogisticRegression`;
- penalty `l2`, `C=1.0`, `class_weight=None`, `fit_intercept=True`, `solver=lbfgs`,
  `max_iter=2000`, `tol=1e-8`.

Probability calibration:

- chronological 80% base-fit / 20% calibration split inside each training portion;
- 48h embargo before calibration rows;
- training-only Platt calibration using the base model score;
- fail closed if either side lacks both directional classes;
- expose `P(declared direction correct)` only after calibration.

Action rule: declare UP when calibrated `P(UP) >= 0.5`, else DOWN. No threshold search and no
selective abstention beyond unavailable source features or fail-closed training validity.

Magnitude head:

- `StandardScaler` on all feature-valid training rows;
- `Ridge(alpha=1.0, fit_intercept=True)` predicting the frozen signed 24h log return.

Strength: training-only inclusive percentile rank of absolute predicted magnitude, same
semantic definition as the canonical contract.

### Configuration B — FUNDING_HGBR_DUAL_HEAD_V1

Experiment id:

`EXP-PRED-004-FUNDING-HGBR-DUAL-HEAD`

Direction estimator: `HistGradientBoostingClassifier`.
Magnitude estimator: `HistGradientBoostingRegressor(loss="squared_error")`.

Frozen structural parameters for both where applicable:

- `learning_rate=0.05`;
- `max_iter=200`;
- `max_leaf_nodes=15`;
- `min_samples_leaf=50`;
- `l2_regularization=1.0`;
- `max_bins=255`;
- `early_stopping=False`;
- `random_state=20260916`.

Use the identical five funding features, source-validity rules, folds, training/calibration
split, 48h embargo, Platt calibration, action rule, magnitude target and strength rule as
Configuration A. No scaling is required for HGBR.

No hyperparameter search, threshold search, feature search, or third Stage-2 funding model is
authorized.

## 7. Multiplicity, MESI and inference

Family size = 2 configurations.

- familywise alpha = 0.05;
- Bonferroni per configuration alpha = 0.025;
- central paired interval mass = 97.5%;
- paired fold-stratified moving-block bootstrap;
- block length = frozen 48h;
- bootstrap replicates = frozen 10,000;
- bootstrap seed = frozen 20260916.

MESI for the primary effect:

**+0.015 absolute win-rate points** (+1.5 percentage points) versus
`MATCHED_TRAINING_UP_BASE_RATE`.

Do not lower MESI or change alpha after observing results.

## 8. Advancement gate — each configuration

Every condition below is all-must-hold for that configuration to be classified as an
advancing settled-funding predictor:

1. pooled source-universe coverage >= 0.95;
2. every one of the five evaluation folds has coverage >= 0.90;
3. pooled primary delta vs `MATCHED_TRAINING_UP_BASE_RATE` >= +0.015;
4. 97.5% paired interval lower bound for that primary delta > 0;
5. pooled delta vs matched `ALWAYS_UP` > 0;
6. at least 4 of 5 fold primary deltas are non-negative;
7. pooled Brier score is <= the matched training-base-rate control Brier score.

Pass classifications:

- `ADVANCE_FUNDING_LINEAR_V1`;
- `ADVANCE_FUNDING_HGBR_V1`.

Fail classifications:

- `NO_ADVANCE_FUNDING_LINEAR_V1`;
- `NO_ADVANCE_FUNDING_HGBR_V1`.

A magnitude head is reported but does not rescue a failed directional gate. Record its MAE,
median absolute error and magnitude-match diagnostic against `ZERO_RETURN_MAGNITUDE`.

## 9. Family disposition after both configurations

After both results exist:

- if neither configuration passes all seven gates, close
  `PREDICTIVE_STAGE2_SETTLED_FUNDING_FAMILY_V1` as `REJECTED_DEVELOPMENT_NO_SEALED` and make
  neither configuration sealed-eligible;
- if at least one passes all seven gates, classify the family
  `DEVELOPMENT_SIGNAL_REQUIRES_RESEARCH_DIRECTOR_REVIEW` and stop. Do **not** query sealed
  data, promote a Champion, create a prospective observer, or tune a descendant automatically.

Do not choose a winner between A and B post hoc. Report both exactly as preregistered.

## 10. Preregistration and admission order

Before any outer-evaluation number for either configuration is observed:

1. freeze the search-plan JSON;
2. create both experiment preregistrations under `research/experiments/`;
3. implement the shared funding feature builder and both model configurations;
4. prove source point-in-time semantics and feature causality on synthetic fixtures;
5. create a pre-execution admission artifact hashing the search plan, both preregistrations,
   the relevant canonical source manifest/contract identity and the implementation;
6. commit those pre-result artifacts;
7. only then execute Configuration A and Configuration B.

The executor must not alter the frozen design in response to either result.

## 11. Mandatory tests

At minimum prove deterministically:

- a funding record exactly at `T` is unavailable and cannot enter the vector;
- no post-`T` settlement can affect a feature at `T`;
- the five features reproduce hand-computed fixtures;
- fewer than nine prior settlements abstains and is counted;
- any disallowed gap inside the nine-record chain abstains and is counted;
- the feature set contains no Stage-1 internal-price feature;
- fold fitting/calibration never touches the outer evaluation portion;
- fixed-seed HGBR is deterministic;
- all seven advancement gates are recomputed from metrics, not trusted from a classification
  string;
- a high win rate with low coverage cannot advance;
- a candidate that beats the training-base-rate control but does not beat matched `ALWAYS_UP`
  cannot advance;
- a candidate with worse Brier than the matched control cannot advance;
- both configurations execute and consume exactly 2 of 2 family slots.

## 12. Boundaries

- No Stage-1 rescue or redesign.
- No canonical hourly-gap repair in this checkpoint.
- No open-interest/basis/CFTC/macro/news/on-chain acquisition or experiment.
- No post-cutoff BTC market data and no sealed query.
- No change to historical experiment results or terminal classifications.
- No change to the frozen prediction target or horizon.
- No parameter, feature or threshold tuning after results.
- Champion `NONE`.
- Real money `false`.

## 13. Artifacts and state

At minimum:

- predictive funding contract under `docs/contracts/`;
- Stage-2 search plan under `research/protocols/`;
- two experiment preregistrations, admissions, trials/results;
- implementation/tests under `backend/app/predictive/` and `backend/tests/`;
- comparison/report artifacts under `reports/research/`;
- Stage-1 final disposition recorded in `state/current_state.json`;
- Stage-2 current/final search-budget accounting in state;
- concise checkpoint report under `reports/checkpoints/`;
- archive this task at completion;
- next `tasks/CURRENT_TASK.md` must be a Research Director review if either candidate advances,
  otherwise may point to the next roadmap decision with no automatic external-family search.

## 14. Validation

- backend tests PASS;
- frontend validation PASS if touched;
- `scripts/check.py --no-data` PASS;
- full data-mode deterministic replay PASS with local development data;
- ruff / format / mypy PASS;
- exact search-budget accounting;
- sealed queries = 0;
- Champion `NONE`;
- real money `false`;
- clean tree;
- commit and push to `main`;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE STAGE2 SETTLED FUNDING V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, Stage-1 disposition, Substrate decision,
Funding source/admission identity, Search-plan hash, Experiment IDs, Feature set, Fold design,
Model/calibration procedures, Model fits, Source-universe coverage, Candidate win rates,
Matched training-base-rate win rates, Matched ALWAYS_UP win rates, Primary deltas + 97.5%
paired intervals, Calibration, Magnitude error, Per-fold deltas/coverage, Advancement gates,
Configuration classifications, Stage-2 family disposition/search budget, Sealed eligibility,
Sealed queries, Champion, Real money, Validation, Exact-head CI, Next action.
