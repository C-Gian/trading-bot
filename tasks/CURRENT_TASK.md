# CURRENT TASK — PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1

Status: ACTIVE_PREDICTIVE_MODELLING_RESEARCH_DIRECTOR_FROZEN

Starting HEAD: `d39672baa6f89338fa695275ea73a32546008ecd` on `main`.

Predecessor: `PREDICTIVE-STAGE3-MACRO-VINTAGE-V1` — Research Director review:
**ACCEPTED AS SOURCE-BLOCKED, NOT A MARKET RESULT**.

The predecessor remains immutable with disposition `BLOCKED_MACRO_SOURCE_COVERAGE_V1`.
It executed 0 model fits, observed 0 outer predictions, consumed 0 predictive configurations
and made 0 sealed queries. Its 10.72%–13.73% fold coverage came almost entirely from the
frozen rule that judged the *observation date* of the latest CPI release stale after 45 days;
the source audit counted 55,342
`CPIAUCSL_CURRENT_ANCHOR_UNAVAILABLE_OR_STALE` failures. No BTC return or prediction was
used to discover that source-design defect.

This checkpoint authorizes exactly **one** prospective source-semantics remediation for the
same ALFRED information family. It is not a retrospective weakening of the predecessor gate.
If this remediation still cannot pass its source gate, park the macro family and do not create
another source redesign in `PREDICTIVE_RESEARCH_GENERATION_V1`.

Governing documents:

- `governance/SCIENTIFIC_CONSTITUTION.md` Version 2.0;
- `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md`, Amendment A1;
- `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`, Stage 3;
- `docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md`;
- `data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json`;
- `research/exogenous/ALFRED_SERIES_CATALOG_V1.json`;
- the complete immutable records of `PREDICTIVE-STAGE3-MACRO-VINTAGE-V1`.

Champion remains `NONE`; real money remains `false`; sealed queries remain 0.

## 1. Research Director decisions frozen before execution

Record all of the following before any target-bearing fit or outer prediction:

1. `PREDICTIVE_RESEARCH_GENERATION_V1` continues.
2. The BTCUSDT 24h terminal direction target, labels, folds, scorer, MESI and advancement
   semantics remain unchanged.
3. Magnitude remains deferred until a family earns directional admission.
4. Basis remains deferred.
5. Stage-1 substrate debt remains `DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH`.
6. All eight executed predictive configurations remain unchanged and rejected.
7. `PREDICTIVE-STAGE3-MACRO-VINTAGE-V1` remains source-blocked and is never reclassified as
   negative market evidence.
8. This checkpoint is the one and only source-semantics remediation authorized for this
   ALFRED macro family inside Generation V1.
9. No current-revised FRED substitution, interpolation, future vintage, feature search,
   threshold search or sealed BTC access is authorized.

## 2. Why the source semantics are being recut

The predecessor correctly enforced point-in-time availability but used one inappropriate
freshness concept for low-frequency releases: it compared the current CPI observation period
date with the BTC decision date. CPI is published after the reference month, so a legitimate
latest-known release became mechanically "stale" for most of every month even though no newer
release yet existed.

The new contract must distinguish:

- **state persistence**: the last value actually published and available at T remains the
  market's current known macro state until superseded by a later available release;
- **interpolation/backfill**: inventing or importing a value that was not available at T,
  which remains forbidden.

This distinction is frozen from source-only audit evidence before any macro predictive result.

## 3. Source identity and release-state contract

Use exactly the existing ALFRED substrate:

- manifest `data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json`;
- canonical parquet `data/derived/ALFRED-macro-context-v1.parquet`;
- catalog `research/exogenous/ALFRED_SERIES_CATALOG_V1.json`;
- exact series `DFF, DGS10, T10Y2Y, VIXCLS, NFCI, WALCL, CPIAUCSL, UNRATE`;
- availability rule `NEXT_CALENDAR_DAY_00_00_UTC_AFTER_VINTAGE_START`;
- current-revised substitution false;
- post-2024 vintages 0.

Create a new predictive contract:

`docs/contracts/PREDICTIVE_MACRO_RELEASE_STATE_V1.md`

Do not modify `POINT_IN_TIME_EXOGENOUS_DATA_V1.md` or the predecessor predictive contract.

At decision time T:

- reconstruct each series strictly from records with `availability_time <= T`;
- for each observation date, use only its latest vintage state available by T;
- define the **current known level** as the value belonging to the greatest observation date
  present in that as-of-T snapshot;
- that current level persists causally until a newer observation becomes available;
- do not reject a current level merely because its observation period date is older than a
  fixed number of days relative to T;
- do not interpolate, nearest-future substitute, or use a later revision.

### Source-cadence integrity audit

Before BTC outcomes are read, prove the admitted source itself is not silently frozen or
missing long stretches. On the sequence of observation dates represented in the point-in-time
substrate, require no gap larger than:

- 10 calendar days for daily/business-daily series;
- 21 calendar days for weekly series;
- 70 calendar days for monthly series.

A violation blocks before prediction with
`BLOCKED_MACRO_RELEASE_STATE_SOURCE_INTEGRITY_V1`.

These are source-integrity limits only. They are not per-decision "current value" expiry rules.

## 4. Frozen feature set V2

Create `PREDICTIVE_MACRO_VINTAGE_FEATURES_V2`, exactly the same 13 economic quantities and
order as V1, but with the corrected current-state semantics above:

1. `DFF_LEVEL`
2. `DFF_DELTA_30D`
3. `DGS10_LEVEL`
4. `DGS10_DELTA_30D`
5. `T10Y2Y_LEVEL`
6. `T10Y2Y_DELTA_30D`
7. `LOG_VIX_LEVEL`
8. `VIX_LOG_CHANGE_5D`
9. `NFCI_LEVEL`
10. `NFCI_DELTA_28D`
11. `WALCL_LOG_CHANGE_28D`
12. `CPI_YOY_LOG_CHANGE`
13. `UNRATE_DELTA_3M`

Historical-anchor rules:

- DFF/DGS10/T10Y2Y 30d anchors: latest observation on/before `T_date - 30d`, at most 7
  calendar days earlier than that anchor;
- VIX 5d anchor: latest observation on/before `T_date - 5d`, at most 7 days earlier;
- NFCI/WALCL 28d anchors: latest observation on/before `T_date - 28d`, at most 14 days
  earlier;
- CPI YoY: take the current-known CPI observation date and require the observation exactly
  12 calendar months earlier to exist in the same as-of-T snapshot;
- UNRATE 3m: take the current-known unemployment observation date and require the observation
  exactly 3 calendar months earlier to exist in the same as-of-T snapshot.

The historical anchor tolerance is measured against the intended historical anchor, never
against current decision time. Later revisions are visible only if their availability time is
<= T.

If a required anchor is absent/non-finite or a log input is non-positive, abstain and record a
typed source-feature reason.

No BTC price/volume, breadth, funding, open interest, basis, CFTC, calendar, news, sentiment
or on-chain feature may enter.

## 5. Pre-result source coverage gate

The source audit may read only canonical BTC timestamps/completeness needed to define the
frozen eligible grid. It may not load BTC closes, returns, direction labels, model scores or
predictions.

For each calendar fold 2019–2024, compute feature validity under V2.

A fold is source-admissible iff:

- source-feature coverage >= 0.90; and
- at least 365 calendar days of feature-valid history exist before the fold start.

Execution is authorized only if:

- at least 5 folds are source-admissible; and
- pooled source-feature coverage over included folds >= 0.95.

If this gate fails, stop before model fitting and classify
`BLOCKED_MACRO_RELEASE_STATE_SOURCE_COVERAGE_V1`. Record the macro family as
`PARKED_SOURCE_DESIGN_EXHAUSTED_NO_MARKET_RESULT`. Do not create a third source semantics
version in Generation V1.

## 6. Frozen model family if and only if the source gate passes

Create and freeze:

`research/protocols/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-SEARCH-PLAN-V1.json`

Family:

`PREDICTIVE_STAGE3_MACRO_RELEASE_STATE_FAMILY_V1`

Exactly two configurations:

### A. `MACRO_RELEASE_STATE_LINEAR_V1`
Experiment: `EXP-PRED-009-MACRO-RELEASE-STATE-LINEAR`
Hypothesis: `H-PRED-MACRO-003`

- StandardScaler + LogisticRegression;
- l2, C=1.0, class_weight null, fit_intercept true, solver lbfgs, max_iter 2000, tol 1e-8;
- training-only Platt calibration using unpenalized LogisticRegression on raw decision score;
- chronological 80% base-fit / 20% calibration split with the frozen 48h calibration embargo;
- UP iff calibrated p_up >= 0.5, ties UP;
- no threshold/hyperparameter search.

### B. `MACRO_RELEASE_STATE_HGBR_V1`
Experiment: `EXP-PRED-010-MACRO-RELEASE-STATE-HGBR`
Hypothesis: `H-PRED-MACRO-004`

- HistGradientBoostingClassifier;
- learning_rate 0.05;
- max_iter 200;
- max_leaf_nodes 15;
- min_samples_leaf 50;
- l2_regularization 1.0;
- max_bins 255;
- early_stopping false;
- random_state 20260921;
- same training-only Platt calibration and action rule;
- no threshold/hyperparameter search.

Execute both regardless of the first result. No magnitude estimator.

Multiplicity:

- family size 2;
- familywise alpha 0.05;
- Bonferroni alpha 0.025 each;
- central paired interval mass 0.975.

If the source gate passes, both configurations are consumed and this family closes.

## 7. Evaluation, controls and advancement

Use the frozen canonical BTCUSDT 24h labels/folds and source-admissible fold subset selected
before outcomes.

For each included fold:

- expanding chronological training;
- frozen 24h purge/embargo;
- feature-valid training rows only;
- 80/20 chronological fit/calibration split;
- 48h calibration embargo;
- Platt map fit only on training/calibration data;
- outer rows unseen until design/admission identities are frozen.

Primary control: `TRAINING_UP_BASE_RATE` fitted on the same fold training portion and scored
on exact candidate-actionable timestamps.

Absolute floor: matched `ALWAYS_UP`.

Descriptive only: `PREVIOUS_24H_SIGN_PERSISTENCE`, never inverted.

Primary effect:
`candidate win rate - matched TRAINING_UP_BASE_RATE win rate`.

MESI: +0.015 absolute win-rate points.

Inference:

- fold-stratified 48h moving-block bootstrap;
- 10,000 replicates;
- seed 20260921;
- paired candidate/control records;
- 97.5% interval.

All seven gates must hold independently for each configuration:

1. pooled coverage >= 0.95;
2. every included fold coverage >= 0.90;
3. pooled primary delta >= +0.015;
4. paired interval lower bound > 0;
5. candidate win rate >= matched ALWAYS_UP;
6. candidate Brier <= matched TRAINING_UP_BASE_RATE Brier;
7. at least `ceil(2*N_folds/3)` folds have non-negative candidate-minus-control delta.

Pass:
`ADVANCE_MACRO_RELEASE_STATE_LINEAR_V1` /
`ADVANCE_MACRO_RELEASE_STATE_HGBR_V1`.

Fail:
`NO_ADVANCE_MACRO_RELEASE_STATE_LINEAR_V1` /
`NO_ADVANCE_MACRO_RELEASE_STATE_HGBR_V1`.

If neither advances:
`REJECTED_DEVELOPMENT_NO_SEALED`.

No sealed query is authorized here even if one passes; passing means only
`ELIGIBLE_FOR_RESEARCH_DIRECTOR_SEALED_REVIEW`.

## 8. Required artifacts and guards

Produce:

- new release-state contract;
- deterministic source-integrity/source-coverage audit;
- search plan;
- two preregistrations;
- pre-execution admission artifact hashing source, V2 semantics, preregistrations and
  implementation;
- implementation and synthetic PIT tests;
- if source gate passes: two result/trial records and research report;
- if blocked: explicit source-block report with 0 fits/0 predictions;
- state update;
- archived task and next Research-Director-review task.

Tests must prove:

- later vintages cannot alter an earlier feature vector;
- a latest-known monthly release remains available between releases;
- a future monthly release is invisible before availability;
- CPI/UNRATE historical anchors are taken from the same as-of-T snapshot;
- source coverage computation is outcome-blind;
- predecessor V1 records remain byte-identical;
- all eight prior executed predictive results remain byte-identical.

## 9. Permanent boundaries

Forbidden:

- editing or reclassifying the predecessor source block;
- lowering the completed or new coverage gates after seeing them;
- a third macro source redesign in Generation V1;
- feature pruning/search after source or market result;
- mixing rejected feature families;
- breadth inversion/negation/threshold rescue;
- changing 24h target/horizon;
- magnitude head;
- basis;
- Stage-1 gap repair;
- current-revised macro data;
- interpolation/future vintage;
- sealed/post-cutoff BTC access;
- real money.

## 10. Validation

Require backend tests, frontend validation if touched, ruff, format, mypy,
`scripts/check.py --no-data`, full installed-development-data validation, deterministic
source audit/result replay, exact search-budget/source-redesign accounting, clean tree,
commit+push to main and exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE STAGE3 MACRO RELEASE STATE V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, predecessor disposition, Research Director
decisions, corrected source semantics, source integrity gate, source coverage gate, included
folds, search-plan/admission hashes, Experiment IDs, feature set, model/calibration procedure,
model fits, candidate win rates+coverage if executed, matched controls, primary deltas+97.5%
intervals, calibration, per-fold results, advancement gates, classifications, family
disposition/search budget, source-redesign budget, sealed eligibility, prior-result integrity,
sealed queries, Champion, real money, validation, exact-head CI, next action.
