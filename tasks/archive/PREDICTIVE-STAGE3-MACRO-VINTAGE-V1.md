# CURRENT TASK — PREDICTIVE-STAGE3-MACRO-VINTAGE-V1

Status: ACTIVE_PREDICTIVE_MODELLING_RESEARCH_DIRECTOR_FROZEN

Starting HEAD: `5aac18947966eb68af7fa8b187b17af2719f43c3` on `main`.

Predecessor: `PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1` — Research Director review: **ACCEPTED AS NEGATIVE**.
Family disposition remains `REJECTED_DEVELOPMENT_NO_SEALED`; both configurations remain
`NOT_ELIGIBLE_REJECTED_DEVELOPMENT`. The reliably-wrong breadth result may not be inverted,
negated, thresholded, fold-trimmed or otherwise rescued.

Governing documents:

- `governance/SCIENTIFIC_CONSTITUTION.md` Version 2.0;
- `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md`, Amendment A1;
- `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`, Stage 3;
- `docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md`;
- `data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json`;
- `research/exogenous/ALFRED_SERIES_CATALOG_V1.json`.

This checkpoint asks one new question: does strict point-in-time U.S. macro/financial-condition
information contain 24h BTCUSDT directional information beyond the information-free training
base rate?

The 24h terminal target remains frozen. This checkpoint does **not** reopen the horizon.
Magnitude remains deferred: no magnitude head is authorized until a family earns directional
admission. Basis remains deferred. Stage-1 substrate debt remains
`DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH`. Champion remains `NONE`; real money remains
`false`.

## 1. Research Director disposition before execution

Record these decisions in the preregistration/search plan before any result:

1. `PREDICTIVE_RESEARCH_GENERATION_V1` continues.
2. Eight prior configurations across four families are negative and stay unchanged.
3. The Stage-3 breadth result is evidence against the tested breadth formulations, not
   authorization to invert them.
4. Do not test basis in this checkpoint.
5. Do not repair the Stage-1 gap substrate.
6. Do not change the 24h target/horizon in this generation.
7. Do not declare magnitude in this family.
8. Macro vintage is admitted next because it is information-orthogonal to price structure,
   derivatives carry/positioning and crypto breadth, and an existing ALFRED point-in-time
   foundation is already hash-pinned.

## 2. Source admission — must pass before any predictive result

Source identity:

- manifest: `data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json`;
- canonical parquet: `data/derived/ALFRED-macro-context-v1.parquet`;
- source family: ALFRED;
- exact eight-series catalog:
  `DFF, DGS10, T10Y2Y, VIXCLS, NFCI, WALCL, CPIAUCSL, UNRATE`;
- current-revised substitution forbidden;
- post-2024 vintages forbidden;
- availability rule remains
  `NEXT_CALENDAR_DAY_00_00_UTC_AFTER_VINTAGE_START`;
- a record is usable only when `availability_time <= T`.

Create a new predictive contract
`docs/contracts/PREDICTIVE_MACRO_VINTAGE_CONTEXT_V1.md` that references, but does not alter,
`POINT_IN_TIME_EXOGENOUS_DATA_V1.md`.

Before reading any BTC outcome or producing any outer-fold prediction, create a source audit
that proves:

- manifest/file/catalog identities match the tracked records;
- all eight series are present;
- no future revision can enter an as-of snapshot;
- current-revised FRED values are never substituted;
- no interpolation is used;
- synthetic as-of tests prove that adding a later vintage cannot change a feature vector at
  an earlier decision timestamp;
- the source-feature coverage gate below is computed from timestamps/source validity only,
  with no BTC return values and no model predictions.

For each candidate fold 2019–2024, compute source-feature validity over the frozen canonical
eligible timestamps. A fold is source-admissible iff:

- source-feature coverage >= 0.90; and
- at least 365 calendar days of feature-valid history exist before the fold starts.

The checkpoint may execute only if at least **five** folds are source-admissible and pooled
source-feature coverage across those folds is >= 0.95. If the gate fails, stop before model
fit and classify `BLOCKED_MACRO_SOURCE_COVERAGE_V1`. Do not weaken the gate.

## 3. Frozen macro feature vector

Create `PREDICTIVE_MACRO_VINTAGE_FEATURES_V1`, exactly 13 features.

At each decision timestamp T, first reconstruct the complete ALFRED snapshot **as known at T**:
for every observation date, only a vintage state with `availability_time <= T` may be used.
All derived changes below are computed from that same as-of-T snapshot. Later revisions are
never visible.

Anchor lookup policy:

- daily/business-daily series: latest observation on/before the anchor, maximum age 7 days;
- weekly series: latest observation on/before the anchor, maximum age 14 days;
- monthly series: latest observation on/before the anchor, maximum age 45 days;
- no interpolation and no nearest-future substitution;
- if any required anchor is unavailable/stale/non-finite, the feature vector is unavailable
  and the reason is typed and counted.

Features, in this exact order:

1. `DFF_LEVEL`
2. `DFF_DELTA_30D`
3. `DGS10_LEVEL`
4. `DGS10_DELTA_30D`
5. `T10Y2Y_LEVEL`
6. `T10Y2Y_DELTA_30D`
7. `LOG_VIX_LEVEL` = natural log of positive VIX level
8. `VIX_LOG_CHANGE_5D`
9. `NFCI_LEVEL`
10. `NFCI_DELTA_28D`
11. `WALCL_LOG_CHANGE_28D` on strictly positive levels
12. `CPI_YOY_LOG_CHANGE` using the latest monthly CPI observation and the observation
    exactly 12 calendar months earlier, both reconstructed as known at T
13. `UNRATE_DELTA_3M` using the latest monthly unemployment observation and the observation
    exactly 3 calendar months earlier, both reconstructed as known at T

No BTC price/volume feature, cross-asset feature, funding feature, open-interest feature,
basis, CFTC, calendar/cycle, news, sentiment or on-chain feature may enter.

## 4. Search family frozen before result

Create and freeze:

`research/protocols/PREDICTIVE-STAGE3-MACRO-VINTAGE-SEARCH-PLAN-V1.json`

Family:

`PREDICTIVE_STAGE3_MACRO_VINTAGE_FAMILY_V1`

Exactly two configurations, both executed in this checkpoint regardless of the first result
unless a source/integrity/software defect blocks execution:

### A. `MACRO_VINTAGE_LINEAR_V1`

- direction estimator: `StandardScaler + LogisticRegression`;
- LogisticRegression: penalty l2, C=1.0, class_weight null, fit_intercept true,
  solver lbfgs, max_iter 2000, tol 1e-8;
- probability calibration: training-only Platt map using a second
  `LogisticRegression(penalty=None, fit_intercept=True, solver=lbfgs, max_iter=2000,
  tol=1e-8)` on the base raw decision score;
- declare UP when calibrated p_up >= 0.5, else DOWN; ties UP;
- no threshold search, no hyperparameter search.

### B. `MACRO_VINTAGE_HGBR_V1`

- `HistGradientBoostingClassifier`;
- learning_rate 0.05;
- max_iter 200;
- max_leaf_nodes 15;
- min_samples_leaf 50;
- l2_regularization 1.0;
- max_bins 255;
- early_stopping false;
- random_state 20260919;
- same training-only Platt calibration and action rule as configuration A;
- no threshold search, no hyperparameter search.

No magnitude estimator is fitted in either configuration.

Multiplicity:

- family size 2;
- familywise alpha 0.05;
- Bonferroni alpha 0.025 per configuration;
- primary paired interval mass 0.975.

The checkpoint consumes both configurations and closes this family.

## 5. Folds, training and calibration

Use the frozen canonical BTCUSDT 24h labels and fold boundaries unchanged.

Evaluation folds are the source-admissible subset of calendar folds 2019–2024 determined
solely by the pre-result source audit in §2. No fold may be removed after any prediction
number exists.

For each included fold:

- expanding chronological training only;
- keep the frozen 24h purge/embargo semantics;
- feature-valid training rows only;
- chronological 80% base-fit / 20% calibration split;
- 48h embargo between base-fit and calibration portions;
- Platt calibration is training-only;
- outer evaluation rows are unseen until the complete configuration is frozen;
- fail closed if either fitting side lacks both directional classes.

## 6. Controls and primary hypothesis

Experiment IDs:

- `EXP-PRED-007-MACRO-VINTAGE-LINEAR`
- `EXP-PRED-008-MACRO-VINTAGE-HGBR`

Hypotheses:

- `H-PRED-MACRO-001`
- `H-PRED-MACRO-002`

Primary matched control:

`TRAINING_UP_BASE_RATE`, fitted separately on the same fold training portion and scored on the
exact candidate-actionable timestamps.

Absolute reference:

`ALWAYS_UP`, scored on the exact candidate-actionable timestamps.

Also report `PREVIOUS_24H_SIGN_PERSISTENCE` descriptively and never invert it.

Primary effect:

`candidate actionable directional win rate - matched TRAINING_UP_BASE_RATE win rate`.

MESI: **+0.015 absolute win-rate points**.

No information from any rejected family is part of the control or candidate.

## 7. Advancement gate — all conditions must hold

For each configuration independently:

1. pooled candidate coverage >= 0.95;
2. every included fold candidate coverage >= 0.90;
3. pooled primary delta >= +0.015;
4. lower bound of the paired 97.5% moving-block-bootstrap interval > 0;
5. candidate win rate >= matched `ALWAYS_UP`;
6. candidate Brier <= matched `TRAINING_UP_BASE_RATE` Brier;
7. at least `ceil(2 * N_folds / 3)` included folds have non-negative candidate-minus-base-rate
   delta.

Inference:

- reuse the frozen fold-stratified 48h moving-block bootstrap;
- 10,000 replicates;
- seed 20260919 for this family;
- paired candidate/control records only.

All seven gates are binding. No secondary metric, reliability bin, subgroup, year, sign flip,
threshold or narrative may rescue a failure.

Pass classifications:

- `ADVANCE_MACRO_VINTAGE_LINEAR_V1`
- `ADVANCE_MACRO_VINTAGE_HGBR_V1`

Fail classifications:

- `NO_ADVANCE_MACRO_VINTAGE_LINEAR_V1`
- `NO_ADVANCE_MACRO_VINTAGE_HGBR_V1`

If neither advances, family disposition:
`REJECTED_DEVELOPMENT_NO_SEALED`.

No sealed query is authorized in this checkpoint even if a configuration passes; a passing
configuration becomes **eligible for Research Director sealed-review consideration**, not a
Champion.

## 8. Mandatory reporting

For each configuration report:

- win rate, actionable N and coverage;
- matched training-base-rate win rate and Brier;
- matched ALWAYS_UP win rate;
- PREVIOUS_24H_SIGN_PERSISTENCE descriptive comparison;
- calibrated-probability Brier and fixed reliability bins;
- paired primary delta and 97.5% dependence-aware interval;
- every included fold's delta, coverage, candidate win rate and controls;
- feature-unavailable counts by typed reason;
- model-fit accounting;
- complete advancement-gate table.

Also report:

- source audit and included/excluded fold decision before outcome;
- exact ALFRED manifest/catalog identities;
- both preregistration/admission hashes;
- search-budget closure;
- all eight prior predictive results unchanged;
- Stage-1 substrate debt unchanged;
- basis still deferred;
- target/horizon unchanged;
- magnitude still deferred;
- sealed queries 0;
- Champion NONE;
- real money false.

## 9. Artifacts and boundaries

Artifacts:

- new predictive macro contract;
- source audit;
- search plan;
- two preregistrations under `research/experiments/`;
- pre-execution admission artifact hashing source + preregistrations + implementation;
- implementation under `backend/app/predictive/`;
- deterministic synthetic causality/as-of tests;
- trials/results for both configurations;
- research report;
- checkpoint report;
- one state update at completion;
- archive this task and write the next Research-Director-review task.

Forbidden:

- changing or re-reading the Stage-3 breadth signal as an inverse;
- combining prior rejected feature families;
- changing horizon/target/folds/scorer/MESI/alpha after result;
- acquiring a new source when the admitted ALFRED foundation suffices;
- using current revised macro data;
- feature search or pruning after result;
- sealed/post-cutoff BTC access;
- real-money action.

## 10. Validation

Require:

- backend tests PASS;
- frontend lint/typecheck/tests/build PASS if touched;
- ruff check/format PASS;
- mypy PASS;
- `scripts/check.py --no-data` PASS;
- full installed-development-data validation PASS;
- deterministic result replay byte-identical;
- source audit reproducible from the tracked manifest;
- exact search-budget accounting;
- clean working tree;
- commit and push to `main`;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE STAGE3 MACRO VINTAGE V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, Research Director decisions, Source identity
and point-in-time semantics, Source coverage gate, Included folds, Search-plan/admission hashes,
Experiment IDs, Feature set, Model/calibration procedures, Model fits, Candidate win rates +
coverage, Matched controls, Primary deltas + 97.5% intervals, Calibration, Per-fold results,
Advancement gates, Configuration classifications, Family disposition/search budget, Sealed
eligibility, Prior experiment integrity, Sealed queries, Champion, Real money, Validation,
Exact-head CI, Next action.
