# CURRENT TASK — PREDICTIVE-STAGE2-OPEN-INTEREST-V1

Status: ACTIVE_PREDICTIVE_STAGE2_OPEN_INTEREST_RESEARCH_DIRECTOR_FROZEN

Starting HEAD: `371c43fe2b76aeecc60cb7ec36a821d5ab8178a3` on `main`.

Predecessor: `PREDICTIVE-STAGE2-SETTLED-FUNDING-V1` — Research Director review: **ACCEPTED**.
Both funding configurations are `NO_ADVANCE`, the family is
`REJECTED_DEVELOPMENT_NO_SEALED`, and neither configuration is sealed-eligible.

This work package continues `PREDICTIVE_RESEARCH_GENERATION_V1`. It does **not** revisit the
24h target, does **not** repair the Stage-1 substrate debt, and does **not** rescue any of the
four executed experiments. It tests one orthogonal Stage-2 question: whether the **quantity
of leveraged BTCUSDT perpetual positioning**, measured by historical open interest, contains
24h directional information.

Do not inspect sealed/post-cutoff BTC data. Do not use real money. Champion remains `NONE`.

## 1. Research Director decisions after Stage-2 funding closure

Record these decisions in state/checkpoint artifacts before execution:

1. `PREDICTIVE_RESEARCH_GENERATION_V1` **continues**. Four negative configurations across
   internal structure and settled funding are not sufficient reason to change the frozen 24h
   target. Changing horizon/target now would create a new research generation and is deferred.
2. Stage-1 canonical-hourly gap debt remains
   `DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH`. Do not repair gaps or relax the 169-bar rule in
   this checkpoint.
3. Admit one additional Stage-2 source family: BTCUSDT USD-M perpetual **open interest**.
   Choose open interest before basis because it measures quantity of leveraged exposure,
   whereas settled funding already tested a price/carry channel. Basis is not authorized here.
4. Stage-1 and settled-funding families remain `REJECTED_DEVELOPMENT_NO_SEALED`; their result
   files are immutable and their sealed eligibility remains false.

## 2. Source foundation — official Binance only, fail closed

This repository does not yet contain an admitted historical open-interest source. Build the
source foundation before any target-bearing model evaluation.

Allowed source class:

- official Binance USD-M Futures public historical data for BTCUSDT only;
- credential-free;
- development interval only, never after `2024-12-31T23:59:59.999Z`;
- prefer the official Binance public-data archive when it supplies historical metrics;
- no third-party vendor, scrape, reconstructed vendor mirror, current REST snapshot history,
  or undocumented backfill may substitute for unavailable official history.

The source audit must establish, from official schema/documentation or the archive itself,
that the record timestamp is a defensible point-in-time measurement/availability timestamp.
If that cannot be defended, classify the checkpoint `SOURCE_SEMANTICS_BLOCKED_NOT_EXECUTED`
before any target-bearing model fit.

Only fields needed for open interest may be admitted. In particular:

- admit timestamp + aggregate BTCUSDT perpetual open-interest quantity;
- do not admit long/short ratios, top-trader ratios, funding, mark price, index price, premium,
  basis or liquidation fields in this experiment;
- do not use open-interest *value/notional* as a feature if it mechanically embeds BTC price;
  keep the family interpretable as positioning quantity.

Create a tracked manifest and immutable canonical artifact with raw-source hashes, request or
archive identities, schema, cadence, first/last timestamps, duplicate/gap accounting and the
exact development ceiling. Add a predictive point-in-time contract under `docs/contracts/`.

### Expected source cadence and hourly state

The experiment expects an official **5-minute** historical OI series. If the admitted source
is not a genuine 5-minute series, stop at source audit with
`SOURCE_CADENCE_BLOCKED_NOT_EXECUTED`; do not redesign the experiment after inspecting market
outcomes.

For each hourly decision instant `T`, define the OI state as the latest official OI record
strictly earlier than `T`. A record timestamped exactly at `T` is unavailable. The selected
record must be no older than **10 minutes** at `T`; otherwise the state is unavailable. No
interpolation or forward fill beyond this as-of rule.

## 3. Pre-result source-coverage gate

Run this gate using only source timestamps/quality plus the already-frozen canonical decision
grid — no future-return values and no candidate predictions.

A calendar evaluation fold from the canonical 2020–2024 fold set is source-admissible only
when:

- at least 95% of its canonical eligible decision timestamps have a valid hourly OI state;
- at least 180 calendar days of source history exist before the fold start for training;
- training/evaluation retain the existing 24h purge/embargo semantics.

At least **3 full calendar evaluation folds** and at least **20,000 eligible evaluation
timestamps** must survive. Otherwise classify
`SOURCE_COVERAGE_BLOCKED_NOT_EXECUTED` before fitting a target-bearing model.

The included folds are the deterministic subset satisfying this rule; do not choose or drop
folds based on return labels or model performance.

## 4. Frozen OI feature set

If the source gate passes, build `PREDICTIVE_OPEN_INTEREST_FEATURES_V1` from hourly OI states
only. Let `O_t > 0` be the as-of OI state at decision hour `T`; all lookbacks are hourly states
constructed under §2.

Require valid states for every hour `T-24h ... T`. If any required state is unavailable or
non-positive, the feature vector is unavailable and the candidate abstains; type and count the
reason. No interpolation.

Exactly six features, in this order:

1. `OI_LOG_CHANGE_1H = log(O_T / O_T-1h)`
2. `OI_LOG_CHANGE_4H = log(O_T / O_T-4h)`
3. `OI_LOG_CHANGE_24H = log(O_T / O_T-24h)`
4. `OI_LOG_LEVEL_Z24 = z-score of log(O) over the 25 hourly states T-24h..T`
5. `OI_LOG_DIFF_VOL24 = population stddev of the 24 one-hour differences in log(O)`
6. `OI_LOG_TREND24 = OLS slope of log(O) on integer hour index 0..24 over T-24h..T`

For `OI_LOG_LEVEL_Z24`, if the population standard deviation is exactly zero, emit `0.0`.
For `OI_LOG_DIFF_VOL24`, zero is valid. No clipping, winsorization, sign inversion, thresholds,
interaction terms or price-derived feature may be added.

## 5. Frozen search family and hypotheses

Before any outer-evaluation candidate result, create and commit:

`research/protocols/PREDICTIVE-STAGE2-OPEN-INTEREST-SEARCH-PLAN-V1.json`

Family: `PREDICTIVE_STAGE2_OPEN_INTEREST_MODEL_FAMILY_V1`.

Execute exactly two configurations in this one work package, regardless of the first result:

1. `EXP-PRED-005-OPEN-INTEREST-LINEAR-DUAL-HEAD`
   - hypothesis `H-PRED-OI-001`;
   - direction: `StandardScaler + LogisticRegression(L2, C=1.0)`;
   - magnitude: `StandardScaler + Ridge(alpha=1.0)`.
2. `EXP-PRED-006-OPEN-INTEREST-HGBR-DUAL-HEAD`
   - hypothesis `H-PRED-OI-002`;
   - direction: `HistGradientBoostingClassifier`;
   - magnitude: `HistGradientBoostingRegressor(loss="squared_error")`;
   - `learning_rate=0.05`, `max_iter=200`, `max_leaf_nodes=15`,
     `min_samples_leaf=50`, `l2_regularization=1.0`, `max_bins=255`,
     `early_stopping=False`, `random_state=20260917`.

Both configurations use the same eligible universe, feature-validity rules and outer folds.
No hyperparameter search, threshold search, feature search or result-dependent early stop.
No third configuration is authorized.

Familywise alpha = 0.05, Bonferroni across the two configurations: alpha = 0.025 each; report
a central **97.5%** paired moving-block-bootstrap interval using the frozen 48h block design
and 10,000 replicates. Use a new deterministic seed `20260917` for this family's paired
bootstrap and record it before execution.

## 6. Training, calibration and outputs

Within each outer fold:

- expanding chronological training only;
- preserve the frozen 24h purge/embargo;
- feature fitting/scaling uses training only;
- split feature-valid training rows chronologically 80% base-fit / 20% calibration;
- preserve a 48h gap between base-fit and calibration rows;
- fit a training-only Platt map to the direction head's raw decision score;
- if either required directional class is absent on a fit side, fail closed for that fold;
- expose calibrated `P(declared direction correct)`, never a raw score;
- decision rule: declare `UP` when calibrated `p_up >= 0.5`, else `DOWN`; ties UP;
- magnitude target remains frozen `r_24h`;
- strength remains the training-only percentile rank required by the predictive contract.

No probability-based abstention threshold. Candidate abstention occurs only when source or
feature validity fails.

## 7. Primary metric, controls and MESI

Primary effect for each configuration:

`candidate actionable directional win rate - matched ALWAYS_UP win rate`

on the exact candidate-actionable timestamps.

MESI: **+0.015 absolute win-rate points** (+1.5 percentage points) over matched `ALWAYS_UP`.

Mandatory controls on the identical source-admissible universe:

- `ALWAYS_UP` — primary directional reference;
- fold-training majority/base-rate predictor — directional + calibration reference, fit on
  training only under Amendment A1;
- `PREVIOUS_24H_SIGN_PERSISTENCE` — descriptive required baseline only, never inverted;
- `ZERO_RETURN_MAGNITUDE` — magnitude reference.

The candidate must not be described as useful merely for beating 0.5 or a temporarily weak
training-majority control.

## 8. Advancement gate — all conditions must hold

For a configuration to advance, every condition must pass:

1. pooled candidate coverage >= 0.95 of the source-admissible eligible universe;
2. every included fold candidate coverage >= 0.90;
3. pooled matched delta vs `ALWAYS_UP` >= +0.015;
4. lower bound of the configuration's paired 97.5% interval vs `ALWAYS_UP` > 0;
5. candidate pooled win rate >= matched fold-training-majority/base-rate win rate;
6. candidate Brier score <= matched training-base-rate Brier score;
7. at least `ceil(2/3 * N)` included folds have non-negative candidate-minus-`ALWAYS_UP`
   delta, where `N` is the pre-result source-admissible fold count.

Magnitude MAE and signed magnitude-match are mandatory reporting companions and may never
rescue a failed directional gate.

Pass classifications:

- `ADVANCE_OPEN_INTEREST_LINEAR_V1`
- `ADVANCE_OPEN_INTEREST_HGBR_V1`

Fail classifications:

- `NO_ADVANCE_OPEN_INTEREST_LINEAR_V1`
- `NO_ADVANCE_OPEN_INTEREST_HGBR_V1`

After both execute, close the family. Do not select a post-hoc winner. Sealed eligibility is
allowed only for a configuration that passes **all** gates; this task does not itself query
sealed data or promote a Champion.

## 9. Causality and integrity proof obligations

Synthetic/deterministic tests must prove at minimum:

- a record stamped exactly at decision time is unavailable;
- an OI record older than 10 minutes makes that hourly state unavailable;
- no feature reads an OI record at or after `T`;
- every feature reads only states within `T-24h..T`;
- missing/non-positive states produce typed abstention, never interpolation;
- feature transformations reproduce hand-computed fixtures;
- source and feature availability are independent of future-return labels;
- train/calibration/evaluation separation is preserved;
- both model families are deterministic under frozen settings;
- baseline and candidate timestamps are matched correctly;
- result/classification is re-derived from numbers, not trusted from a stored string;
- rerunning from admitted artifacts reproduces committed results byte-for-byte where the
  repository's deterministic-report convention requires it.

## 10. Boundaries

- BTCUSDT only; no asset-universe expansion.
- Stage-2 open interest only; no basis, long/short ratios, CFTC, macro, news, sentiment or
  on-chain feature in this experiment.
- Do not combine OI with rejected Stage-1 features or rejected funding features.
- Do not change horizon, target, labels, folds, scorer, reliability bins, bootstrap block
  length, MESI or advancement semantics after results.
- No sealed or post-cutoff query.
- No tuned descendant of any rejected configuration.
- Stage-1 substrate debt remains deferred.
- Champion `NONE`; real money `false`.

## 11. Artifacts and state

At minimum create/update:

- official OI raw/archive artifacts and tracked manifest under existing data conventions;
- predictive OI contract under `docs/contracts/`;
- `research/protocols/PREDICTIVE-STAGE2-OPEN-INTEREST-SEARCH-PLAN-V1.json`;
- preregistration, trials and result records for EXP-PRED-005 and EXP-PRED-006;
- pre-execution admission artifact hashing source identity, preregistrations and code;
- implementation under `backend/app/predictive/` plus deterministic tests;
- comparison report under `reports/research/`;
- one checkpoint report;
- `state/current_state.json` updated once from observed truth;
- archive this task at completion and write the next Research-Director review task.

Preserve all four prior predictive experiment results byte-identically.

## 12. Validation and completion

- backend tests PASS;
- frontend validation PASS if touched;
- `scripts/check.py --no-data` PASS and full/data replay PASS when data are installed;
- ruff / format / mypy PASS;
- exact search-budget accounting;
- sealed queries 0;
- Champion `NONE`;
- real money `false`;
- clean tree;
- commit and push to `main`;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE STAGE2 OPEN INTEREST V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, Research Director decisions, Source identity
and point-in-time semantics, Source cadence/coverage gate, Included folds, Search-plan and
admission hashes, Experiment IDs, Feature set, Model/calibration procedures, Model fits,
Candidate win rates + coverage, Matched ALWAYS_UP, Matched training-base-rate, Primary deltas
+ 97.5% intervals, Calibration, Magnitude error, Per-fold deltas/coverage, Advancement gates,
Configuration classifications, Family disposition/search budget, Sealed eligibility, Prior
experiment integrity, Sealed queries, Champion, Real money, Validation, Exact-head CI, Next
action.
