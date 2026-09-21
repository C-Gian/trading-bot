# CURRENT TASK — PREDICTIVE-V2-INTERNAL-STRUCTURE-SELECTIVE-V1

Status: ACTIVE_PREDICTIVE_RESEARCH_DIRECTOR_FROZEN

Starting HEAD: `ea92e9b652b8296964b713ff0ae6b3e62209426a` on `main`.

Predecessor: `PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1` — Research Director review:
**ACCEPTED AS NEGATIVE**. Family disposition remains
`REJECTED_DEVELOPMENT_NO_SEALED`; both configurations remain
`NOT_ELIGIBLE_REJECTED_DEVELOPMENT`. Nothing from that family may be tuned, thresholded,
reweighted or reused as model evidence.

This checkpoint opens the second Generation V2 family.

Scientific question:
can BTCUSDT's own causal price / volume / volatility structure identify a sufficiently
high-confidence subset of hours for `LONG`, under the already-frozen selective V2 scorer,
even though the corresponding Generation V1 always-declare family failed?

This is a **new preregistered V2 hypothesis**, not a rescue or re-scoring of the V1 family.
Do not read, reconstruct, threshold or analyze any stored Generation V1 model probability
tail. The only reusable components are the causal feature-definition code and deterministic
data-integrity machinery.

Magnitude remains `DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`.
No SHORT, leverage, sealed/post-cutoff data, Champion, prospective observer or real money.

Governing documents:

- `governance/SCIENTIFIC_CONSTITUTION.md`;
- `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V2.md` Amendment B1;
- `decisions/ADR-0028-GENERATION-V2-SELECTIVE-LONG-REBASELINE.md`;
- `decisions/ADR-0029-PREDICTIVE-V2-DETERMINISTIC-CALENDAR.md`;
- immutable Generation V1 internal-structure records;
- `state/current_state.json`.

## 1. Research Director ruling before execution

Create an immutable decision/admission record before any target-bearing fit or outer
prediction, recording:

1. `PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1` is accepted as a negative V2 family result;
2. the V2 action threshold `p_up >= 0.60` is unchanged;
3. all ten V2 advancement conditions are unchanged;
4. `FULL_FOLD_UP_RATE` remains the primary enrichment control;
5. magnitude remains deferred;
6. Generation V1 remains closed and byte-identical;
7. this family re-enters internal BTC market structure only because V2 asks a substantively
   different prospective question — selective high-confidence LONG — and not because any
   V1 score tail appeared promising;
8. no V1 score, reliability-bin tail, fold-specific score distribution or threshold
   reconstruction may inform the V2 design or execution;
9. Stage-1 substrate debt remains deferred; the old 169-hour feature-validity rule is reused
   **unchanged**, not repaired;
10. family search budget = exactly two configurations, both executed regardless of the first
    result unless a genuine integrity/software defect blocks execution.

## 2. Exact causal feature set — reuse definition, not results

Feature version for this family:

`PREDICTIVE_V2_INTERNAL_CAUSAL_FEATURES_V1`

Use the same 18 causal quantities and the same edge/validity rules frozen in the Generation V1
internal family. At decision timestamp T, only completed canonical 1h bars at or before T may
enter.

Ordered features:

1. `logret_1h`
2. `logret_6h`
3. `logret_24h`
4. `logret_72h`
5. `logret_168h`
6. `rv_6h`
7. `rv_24h`
8. `rv_72h`
9. `rv_168h`
10. `signed_efficiency_24h`
11. `signed_efficiency_72h`
12. `signed_efficiency_168h`
13. `up_fraction_24h`
14. `up_fraction_168h`
15. `close_position_24h`
16. `close_position_168h`
17. `log_volume_relative_24h`
18. `log_volume_regime_24_168h`

Definitions must be identical to the frozen V1 implementation:

- `logret_1h = log(c_T/c_{T-1h})`;
- `logret_6h = log(c_T/c_{T-6h})`;
- `logret_24h = log(c_T/c_{T-24h})`;
- `logret_72h = log(c_T/c_{T-72h})`;
- `logret_168h = log(c_T/c_{T-168h})`;
- realized-volatility features are square roots of summed squared hourly log returns over
  their declared windows;
- signed-efficiency = declared-window log return divided by summed absolute hourly returns;
- up-fraction = fraction of strictly positive hourly returns;
- close-position = current close inside rolling high-low range;
- volume-relative features retain the exact V1 formulas.

Validity rules remain unchanged:

- every required hourly bar in the maximum 168h lookback must exist and be complete;
- all closes used in logs strictly positive;
- volume non-negative and denominator means strictly positive;
- zero efficiency denominator => 0.0;
- zero high-low range => 0.5;
- otherwise invalid/non-finite => whole feature vector unavailable;
- no interpolation, fill, nearest-bar substitution or substrate repair.

Feature-unavailable rows are counted and excluded exactly as Contract V2 requires. No fold is
removed because its feature availability is low.

The executor may reuse the established deterministic feature builder only if tests prove byte-
identical feature vectors against the frozen V1 definition on fixed fixtures. It may not reuse
V1 fitted models, predictions, probabilities or result records.

## 3. Causality / integrity proofs before result

Before any V2 market model fit:

- mutating any canonical bar after T cannot change the vector at T;
- exact lookback endpoints are tested for 1h/6h/24h/72h/168h windows;
- missing/incomplete-bar behavior matches the frozen V1 rule;
- denominator edge rules match V1;
- fixed-fixture feature vectors reconcile with the frozen V1 feature builder exactly;
- no stored V1 model probability/prediction artifact is loaded by the V2 runner;
- all prior V1 and V2 result artifacts are hash-pinned and unchanged.

Commit the complete scientific design, feature identity, implementation, tests,
preregistrations and admission artifact in a **pre-result commit** before producing any outer
evaluation number.

## 4. Frozen search family

Create:

`research/protocols/PREDICTIVE-V2-INTERNAL-STRUCTURE-SELECTIVE-SEARCH-PLAN-V1.json`

Family:

`PREDICTIVE_V2_INTERNAL_STRUCTURE_SELECTIVE_FAMILY_V1`

Family size: 2.
Familywise alpha: 0.05.
Bonferroni per-configuration alpha: 0.025.
Primary interval mass: 0.975.
Inference seed: **20260922**.

Execute both configurations regardless of the first result.

### A. `V2_INTERNAL_LINEAR_V1`

Experiment ID:
`EXP-PRED-V2-003-INTERNAL-LINEAR`

Hypothesis:
`H-PRED-V2-INTERNAL-001`

Direction/probability model:

- `StandardScaler + LogisticRegression`;
- penalty = l2;
- C = 1.0;
- class_weight = null;
- fit_intercept = true;
- solver = lbfgs;
- max_iter = 2000;
- tol = 1e-8;
- training-only Platt calibration on raw decision score using
  `LogisticRegression(penalty=None, fit_intercept=True, solver=lbfgs, max_iter=2000,
  tol=1e-8)`;
- no hyperparameter search;
- no threshold search.

### B. `V2_INTERNAL_HGBR_V1`

Experiment ID:
`EXP-PRED-V2-004-INTERNAL-HGBR`

Hypothesis:
`H-PRED-V2-INTERNAL-002`

Direction/probability model:

- `HistGradientBoostingClassifier`;
- learning_rate = 0.05;
- max_iter = 200;
- max_leaf_nodes = 15;
- min_samples_leaf = 50;
- l2_regularization = 1.0;
- max_bins = 255;
- early_stopping = false;
- random_state = 20260922;
- same training-only Platt calibration;
- no hyperparameter search;
- no threshold search.

No magnitude model is fitted.

## 5. Folds, fitting and calibration

Use all six frozen annual outer folds 2019–2024. No fold may be removed after any source,
feature, fit or prediction result.

For each fold:

- frozen 24h target and eligible-timestamp semantics;
- expanding chronological training;
- frozen 24h purge/embargo;
- training uses only feature-valid rows;
- chronological 80% base-fit / 20% calibration split on feature-valid training rows;
- 48h embargo between base-fit and calibration portions;
- scaler, classifier and Platt map use training/calibration data only;
- both fit sides must contain both directional classes or fail closed;
- every feature-valid outer row receives calibrated
  `p_up = P(r_24h > 0)`;
- outer rows remain unseen until the family design/admission is frozen.

Action policy inherited unchanged:

- `LONG` iff calibrated `p_up >= 0.60`;
- otherwise `NO_TRADE`;
- exactly 0.60 acts LONG.

Never tune, sweep or vary the threshold.

## 6. Primary control and scoring

Primary control:
`FULL_FOLD_UP_RATE`, exactly as frozen in Contract V2.

Primary effect:
`SELECTIVE_LONG_WIN_RATE - FULL_FOLD_UP_RATE`.

Mandatory secondary transparency:

- `FEATURE_VALID_FOLD_UP_RATE` pooled/by fold;
- pooled/by-fold feature-valid coverage;
- `TRAINING_UP_BASE_RATE` and matched Brier;
- `ALWAYS_UP`;
- `PREVIOUS_24H_SIGN_PERSISTENCE`, descriptive only and never inverted.

Feature availability may not be used to redefine the primary control or remove a fold.

## 7. Advancement gate — unchanged V2 ten-condition gate

For each configuration independently all ten must hold:

1. pooled LONG action coverage >= 0.02;
2. every included fold LONG action coverage >= 0.005;
3. pooled actionable LONG count >= 500;
4. every included fold actionable LONG count >= 30;
5. pooled selective LONG win rate >= 0.60;
6. pooled enrichment over `FULL_FOLD_UP_RATE` >= +0.05;
7. lower bound of paired dependence-aware enrichment interval > 0;
8. at least 4 of 6 folds have non-negative enrichment;
9. full-probability Brier over all feature-valid outer rows <= matched
   `TRAINING_UP_BASE_RATE` Brier;
10. actionable-LONG calibration gap
    `abs(mean p_up - empirical LONG win rate) <= 0.05`.

Inference:

- fold-stratified 48h moving-block bootstrap;
- 10,000 replicates;
- seed 20260922;
- blocks never cross fold boundaries;
- candidate selective win rate and same-fold full-universe UP rate recomputed in each
  replicate;
- empty-action replicates discarded and counted;
- discard share > 1% => `UNSTABLE_RESAMPLE_SUPPORT` and gate 7 fails closed.

No secondary metric rescues any failed gate.

Pass classifications:

- `ADVANCE_V2_INTERNAL_LINEAR_V1`
- `ADVANCE_V2_INTERNAL_HGBR_V1`

Fail classifications:

- `NO_ADVANCE_V2_INTERNAL_LINEAR_V1`
- `NO_ADVANCE_V2_INTERNAL_HGBR_V1`

If neither passes:
`REJECTED_DEVELOPMENT_NO_SEALED`.

A passing configuration becomes only
`ELIGIBLE_FOR_RESEARCH_DIRECTOR_SEALED_REVIEW`. No sealed query is authorized here.

## 8. Search-memory / anti-rescue requirements

Before execution record:

- V1 internal family remains `REJECTED_DEVELOPMENT_NO_SEALED`;
- calendar V2 family remains `REJECTED_DEVELOPMENT_NO_SEALED`;
- all completed result files remain byte-identical;
- no V1 score tail or V1 probability distribution is consulted;
- Stage-1 gap/contiguity debt remains deferred and unmodified;
- cross-asset inversion remains forbidden;
- basis remains deferred;
- macro source-redesign budget remains exhausted;
- family budget is exactly 2 / 2;
- result-dependent forks = 0;
- sealed queries = 0;
- Champion = NONE;
- real money = false.

## 9. Mandatory report

For each configuration report:

- feature-valid N and coverage pooled/by fold;
- actionable LONG N;
- LONG action coverage pooled/by fold;
- selective LONG win rate pooled/by fold;
- `FULL_FOLD_UP_RATE` pooled/by fold;
- `FEATURE_VALID_FOLD_UP_RATE` pooled/by fold;
- enrichment pooled/by fold;
- 97.5% paired moving-block interval;
- discarded bootstrap replicate count/share;
- full-probability Brier and matched training-base-rate Brier;
- actionable mean p_up, empirical LONG win rate and calibration gap;
- fixed reliability bins for actionable LONGs;
- all ten advancement gates;
- model-fit accounting.

Also report:

- pre-result commit and hash identities;
- feature reconciliation with V1 definition;
- explicit proof that no V1 model outputs were used;
- family search-budget closure;
- prior-result integrity;
- magnitude deferred;
- sealed queries 0;
- Champion NONE;
- real money false.

## 10. Artifacts and validation

Produce:

- immutable Research Director calendar-review / V2-internal-family decision record;
- V2 internal feature identity/contract if needed, referencing the immutable V1 feature
  definition rather than rewriting it;
- search plan;
- two preregistrations;
- implementation / runner;
- deterministic causality and reconciliation tests;
- pre-execution admission artifact;
- **pre-result commit**;
- two result/trial artifacts;
- research/checkpoint reports;
- state update;
- archive this task;
- next task = Research Director review, with no automatic third V2 family.

Validation requires:

- backend tests PASS;
- frontend lint/typecheck/tests/build if touched;
- ruff check/format PASS;
- mypy PASS;
- `scripts/check.py --no-data` PASS;
- full installed-development-data replay PASS;
- deterministic result replay byte-identical;
- prior V1 + V2 artifacts byte-identical;
- clean tree;
- commit and push `main`;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE V2 INTERNAL STRUCTURE SELECTIVE V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, Research Director decision, experiment IDs,
feature set/reconciliation, causality proofs, fold set, model/calibration procedures,
pre-result commit/hash identities, model fits, feature-valid coverage, actionable LONG
N/coverage, selective win rates, full-fold and feature-valid UP rates, enrichment + 97.5%
intervals, bootstrap discard support, Brier/calibration, per-fold results, advancement gates,
classifications, family disposition/search budget, sealed eligibility, prior-result integrity,
magnitude, sealed queries, Champion, real money, validation, exact-head CI, next action.
