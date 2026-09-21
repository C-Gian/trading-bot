# CURRENT TASK — PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1

Status: ACTIVE_PREDICTIVE_RESEARCH_DIRECTOR_FROZEN

Starting HEAD: `7bba31220f746c92b2eab0302ccc7fb35604584f` on `main`.

Predecessor: `PREDICTIVE-GENERATION-V2-SELECTIVE-LONG-REBASELINE-V1` — Research Director review:
**ACCEPTED**. The Generation V2 scorer and all frozen thresholds remain unchanged.

This is the first market-model family of `PREDICTIVE_RESEARCH_GENERATION_V2`.

No Generation V1 result is re-scored, reinterpreted or rescued. The first V2 family is chosen
without consulting any V1 model-score tail: deterministic UTC calendar context is a new,
source-free, fully causal information family with essentially zero point-in-time provenance
risk and direct relevance to recurring market/session phenomena.

Magnitude remains deferred. No SHORT, leverage, sealed/post-cutoff BTC access, Champion,
prospective observer or real money is authorized.

Governing documents:

- `governance/SCIENTIFIC_CONSTITUTION.md`;
- `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V2.md` Amendment B1;
- `decisions/ADR-0028-GENERATION-V2-SELECTIVE-LONG-REBASELINE.md`;
- `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`;
- V1 search-memory and family dispositions in `state/current_state.json`.

## 1. Research Director verdict before execution

Record an immutable review/admission decision before any fit or outer prediction:

1. confirm V2 action threshold `p_up >= 0.60` unchanged;
2. confirm all ten V2 advancement conditions unchanged;
3. confirm `FULL_FOLD_UP_RATE` remains the primary enrichment control;
4. confirm magnitude status `DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`;
5. confirm Generation V1 remains closed and byte-identical;
6. open exactly one new V2 family:
   `PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FAMILY_V1`;
7. rationale: deterministic calendar state is new information not tested as a V1 predictive
   family, requires no external acquisition or as-of reconstruction, and can test whether
   recurring temporal regimes contain selective LONG opportunities;
8. no old cycle/cross-section result is imported as evidence;
9. this is a project-reconstructed calendar representation, not an implementation or claim
   about Ciclica Evoluta / Analisi Evoluta.

## 2. Frozen information boundary and feature set

Create `PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FEATURES_V1`.

Features are derived **only** from the UTC decision timestamp T. They must not read BTC price,
volume, returns, labels, funding, open interest, cross-asset data, macro data, news, sentiment,
on-chain data or any future timestamp.

Exactly seven features, in this order:

1. `UTC_HOUR_SIN = sin(2*pi*hour/24)`
2. `UTC_HOUR_COS = cos(2*pi*hour/24)`
3. `UTC_WEEKDAY_SIN = sin(2*pi*weekday/7)`, Monday = 0
4. `UTC_WEEKDAY_COS = cos(2*pi*weekday/7)`
5. `UTC_YEAR_PHASE_SIN = sin(2*pi*(day_of_year-1)/days_in_UTC_year)`
6. `UTC_YEAR_PHASE_COS = cos(2*pi*(day_of_year-1)/days_in_UTC_year)`
7. `UTC_WEEKEND = 1 if weekday in {5,6}, else 0`

Leap years use 366 in the denominator, other years 365. All calculations use timezone-aware UTC
only. DST and local time never participate.

The feature vector must be available at every canonical eligible timestamp. Any feature-invalid
row is an implementation defect and fails closed before model execution.

Do not add month dummies, day-of-month, quarter-end, halving, holiday, session labels or any
other calendar feature in this family.

## 3. Causality and deterministic proofs before market result

Before any model fit, tests must prove:

- feature output depends only on T;
- changing any BTC market value while holding T fixed cannot change the feature vector;
- moving T by exactly one hour changes only the deterministic calendar representation implied
  by the new timestamp;
- UTC weekday/hour boundary behaviour is correct;
- Dec 31 -> Jan 1 wrap is deterministic;
- Feb 28/29 leap-year behaviour is correct;
- no local timezone/DST dependency exists;
- feature validity is 1.0 on all eligible development timestamps.

The feature implementation and all preregistration/admission artifacts must be committed in a
**pre-result commit** before any outer-evaluation number is produced.

## 4. Frozen search family

Create:

`research/protocols/PREDICTIVE-V2-DETERMINISTIC-CALENDAR-SEARCH-PLAN-V1.json`

Family size: exactly 2 configurations. Both are executed regardless of the first result unless
an integrity/software defect blocks the family.

Familywise alpha: 0.05.
Bonferroni per-configuration alpha: 0.025.
Primary interval mass: 0.975.
Inference seed: **20260921**.

### A. `V2_CALENDAR_LINEAR_V1`

Experiment ID:
`EXP-PRED-V2-001-CALENDAR-LINEAR`

Hypothesis:
`H-PRED-V2-CALENDAR-001`

Model:

- `StandardScaler + LogisticRegression`;
- penalty l2;
- C = 1.0;
- class_weight = null;
- fit_intercept = true;
- solver = lbfgs;
- max_iter = 2000;
- tol = 1e-8;
- training-only Platt calibration on raw decision score using unpenalized LogisticRegression;
- no hyperparameter search;
- no threshold search.

### B. `V2_CALENDAR_HGBR_V1`

Experiment ID:
`EXP-PRED-V2-002-CALENDAR-HGBR`

Hypothesis:
`H-PRED-V2-CALENDAR-002`

Model:

- `HistGradientBoostingClassifier`;
- learning_rate = 0.05;
- max_iter = 200;
- max_leaf_nodes = 15;
- min_samples_leaf = 50;
- l2_regularization = 1.0;
- max_bins = 255;
- early_stopping = false;
- random_state = 20260921;
- same training-only Platt calibration and action rule;
- no hyperparameter search;
- no threshold search.

No magnitude estimator in either configuration.

## 5. Folds, fitting and calibration

Use all six frozen annual development folds 2019–2024. No source-admission fold exclusion is
permitted because the calendar vector is deterministic and universal.

Use:

- frozen V2/V1 24h label eligibility;
- expanding chronological training;
- frozen 24h purge/embargo semantics;
- chronological 80% base-fit / 20% calibration split;
- 48h embargo between base-fit and calibration portions;
- fit and calibration only on prior rows;
- outer evaluation unseen until the complete family design/admission is frozen;
- fail closed if either fitting side lacks both directional classes.

Every feature-valid outer row must receive calibrated `p_up = P(r_24h > 0)`.

Action:

- `LONG` iff `p_up >= 0.60`;
- otherwise `NO_TRADE`.

Exactly 0.60 acts LONG. Never tune, sweep or vary this threshold.

## 6. Controls and primary effect

Primary evaluation control:
`FULL_FOLD_UP_RATE`, exactly as frozen in Contract V2.

Primary effect:
`SELECTIVE_LONG_WIN_RATE - FULL_FOLD_UP_RATE`.

Secondary controls/references:

- `FEATURE_VALID_FOLD_UP_RATE`;
- `TRAINING_UP_BASE_RATE` for full-probability Brier;
- `ALWAYS_UP`;
- `PREVIOUS_24H_SIGN_PERSISTENCE`, descriptive only and never inverted.

The full-fold control may enter scoring only. It may not influence fitting, calibration,
thresholding, feature construction, fold selection or family design.

## 7. Advancement gate — inherited unchanged from V2

For each configuration independently, all ten conditions must hold:

1. pooled LONG action coverage >= 0.02;
2. every fold LONG action coverage >= 0.005;
3. pooled actionable LONG N >= 500;
4. every fold actionable LONG N >= 30;
5. pooled selective LONG win rate >= 0.60;
6. pooled enrichment over `FULL_FOLD_UP_RATE` >= +0.05;
7. lower bound of paired dependence-aware enrichment interval > 0;
8. at least 4 of 6 folds have non-negative enrichment;
9. full-probability Brier over all feature-valid outer rows <= matched
   `TRAINING_UP_BASE_RATE` Brier;
10. actionable-LONG calibration gap
    `abs(mean p_up - empirical LONG win rate) <= 0.05`.

Inference:

- fold-stratified moving-block bootstrap;
- 48h blocks;
- 10,000 replicates;
- seed 20260921;
- blocks never cross fold boundaries;
- recompute selected LONG win rate and same-fold full-universe UP rate in every replicate;
- empty-LONG replicates discarded and counted;
- >1% discarded => `UNSTABLE_RESAMPLE_SUPPORT` and gate 7 fails closed.

No secondary metric may rescue a failed gate.

Pass classifications:

- `ADVANCE_V2_CALENDAR_LINEAR_V1`
- `ADVANCE_V2_CALENDAR_HGBR_V1`

Fail classifications:

- `NO_ADVANCE_V2_CALENDAR_LINEAR_V1`
- `NO_ADVANCE_V2_CALENDAR_HGBR_V1`

If neither passes:
`REJECTED_DEVELOPMENT_NO_SEALED`.

A passing configuration becomes only
`ELIGIBLE_FOR_RESEARCH_DIRECTOR_SEALED_REVIEW`; this task does not query sealed data.

## 8. Search-memory and integrity requirements

Record before execution:

- Generation V1 remains `CLOSED_NO_DIRECTIONAL_ADMISSION_NO_SEALED`;
- all ten V1 result artifacts remain byte-identical;
- the macro source-block and residual source finding remain byte-identical;
- no V1 probability score, tail, reliability-bin result or action reconstruction is used in
  V2 family selection or fitting;
- cross-asset inversion remains forbidden;
- Stage-1 substrate debt remains deferred;
- basis remains deferred;
- macro source redesign budget remains exhausted;
- V2 calendar family search budget = 2, consumed exactly by the two declared configurations;
- sealed queries = 0.

## 9. Mandatory report

For each configuration report:

- actionable LONG N;
- LONG action coverage pooled and by fold;
- selective LONG win rate pooled and by fold;
- `FULL_FOLD_UP_RATE` pooled under count-weighted scoring and by fold;
- enrichment pooled and by fold;
- 97.5% paired moving-block interval;
- discarded bootstrap replicate count/share;
- full-probability Brier and matched training-base-rate Brier;
- actionable mean p_up, empirical LONG win rate and calibration gap;
- V1 fixed reliability bins for actionable LONGs;
- all ten advancement gates;
- model-fit accounting.

Also report:

- exact feature set and causality proof status;
- preregistration/search-plan/admission hashes;
- family search-budget closure;
- V1/V2 state integrity;
- magnitude deferred;
- sealed queries 0;
- Champion NONE;
- real money false.

## 10. Artifacts and validation

Produce:

- immutable Research Director V2-first-family decision record;
- deterministic calendar feature contract;
- feature implementation under `backend/app/predictive/`;
- synthetic/causality tests;
- search plan;
- two preregistrations;
- pre-result admission artifact hashing design + implementation;
- **pre-result commit**;
- two executed result/trial artifacts;
- research/checkpoint reports;
- state update;
- archive this task;
- next task = Research Director review; no automatic second V2 family.

Validation requires:

- backend tests PASS;
- frontend lint/typecheck/tests/build if touched;
- ruff check/format PASS;
- mypy PASS;
- `scripts/check.py --no-data` PASS;
- full installed-development-data replay PASS;
- deterministic result replay;
- prior V1 artifacts byte-identical;
- clean tree;
- commit and push main;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE V2 DETERMINISTIC CALENDAR V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, Research Director decision, experiment IDs,
feature set, causality proofs, fold set, model/calibration procedures, pre-result commit/hash
identities, model fits, actionable LONG N/coverage, selective win rates, matched full-fold UP
rates, enrichment + 97.5% intervals, bootstrap discard support, Brier/calibration, per-fold
results, advancement gates, classifications, family disposition/search budget, sealed
eligibility, V1 integrity, magnitude, sealed queries, Champion, real money, validation,
exact-head CI, next action.
