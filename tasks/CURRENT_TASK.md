# CURRENT TASK — PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1

Status: ACTIVE_PREDICTIVE_STAGE3_RESEARCH_DIRECTOR_FROZEN

Starting HEAD for the scientific design: `421c5dfcf8581fa447aeaedabd80499de4567c88` on `main`.

Predecessor: `PREDICTIVE-STAGE2-OPEN-INTEREST-V1` — Research Director review: **ACCEPTED**,
family disposition `REJECTED_DEVELOPMENT_NO_SEALED`.

Governing documents:

- `governance/SCIENTIFIC_CONSTITUTION.md` Version 2.0;
- `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md`, Amendment A1;
- `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`, Stage 3 `CROSS_ASSET_CONTEXT`;
- `research/protocols/PREDICTIVE-BASELINES-V1.json`.

Research Director decisions frozen before any Stage-3 result:

1. `PREDICTIVE_RESEARCH_GENERATION_V1` **continues**. Six rejected configurations across
   internal structure, settled funding and open interest do not yet justify changing the
   frozen 24h terminal target. A horizon/target change would open a new research generation
   and is deferred.
2. Stage-1 canonical-hourly gap debt remains
   `DEFERRED_SUBSTRATE_DEBT_NOT_A_RESCUE_PATH`. Do not repair gaps or relax the 169-bar rule
   in this checkpoint.
3. Stage-2 basis is **not authorized now**. It is deferred, not rejected. After null results
   from funding (carry/price channel) and open interest (positioning-quantity channel), the
   expected incremental information from another derivatives/carry series is lower than the
   value of testing an orthogonal cross-asset channel.
4. Open Stage 3 with **crypto cross-sectional breadth/context** using the already-governed
   official Binance spot USDT cross-section. The BTCUSDT prediction target remains the only
   product target; other assets are context features only.
5. No prior Stage-1/Stage-2 result, feature, fitted model or rejected candidate may be combined
   into this family. The incremental control is information-free because no predictive family
   has yet been admitted.

No executor may alter these decisions after observing a number.

## 1. Scientific question

Family:

`PREDICTIVE_STAGE3_CROSS_ASSET_BREADTH_FAMILY_V1`

Root hypothesis:

`H-PRED-XB-001 — contemporaneous, point-in-time crypto-market breadth available at the BTC
hourly decision instant contains information about BTCUSDT's frozen 24h terminal direction
beyond an information-free chronological base-rate control.`

The family contains exactly two predeclared configurations, both direction/probability only:

1. `CROSS_ASSET_BREADTH_LINEAR_V1` — experiment
   `EXP-PRED-007-CROSS-ASSET-BREADTH-LINEAR`;
2. `CROSS_ASSET_BREADTH_HGBR_V1` — experiment
   `EXP-PRED-008-CROSS-ASSET-BREADTH-HGBR`.

Both are executed in this checkpoint if and only if the source-admission gate passes. The
second executes regardless of the first result. No third configuration, threshold rescue,
feature redesign or parameter search is authorized.

Magnitude is deliberately **not declared** in this information-family admission checkpoint.
The generation has not yet established directional information, and fitting another magnitude
head would add search/computation without answering the admission question. This does not
change the product objective: magnitude/strength will be reintroduced only after a source
family earns directional admission.

## 2. Source and point-in-time admission — must pass before any model result

Candidate source identity:

`data/manifests/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.json`

Use only the existing official-Binance spot archive substrate already represented by that
manifest and its integrity tooling. Historical cross-section research results are not
predictive evidence and must not be imported into this experiment.

Before constructing any prediction or reading any outer-evaluation result, create a new
predictive source contract and a source-audit/admission artifact proving all of the following:

- no post-cutoff BTCUSDT or cross-asset market data is accessed;
- every context value at decision instant `T` uses only bars whose information is available
  at or before `T`;
- BTCUSDT itself is excluded from every cross-sectional feature;
- leveraged-token exclusions and symbol parsing follow the already-governed manifest rules;
- there is **no future-survival filter**, no requirement based on an asset's eventual sample
  length, and no whole-sample participation threshold;
- specifically, do not revive any historical rule equivalent to requiring a fixed total-row
  count over the complete sample (including the retired 504-row/epoch participation idea);
- a symbol becomes usable only from the data actually observed for that symbol by `T`;
- missing endpoint bars make that symbol unavailable for that decision instant; there is no
  interpolation, forward fill, nearest-bar substitution or reconstruction;
- source-universe membership is recomputed point-in-time at every decision instant and may
  grow or shrink causally;
- cross-sectional statistics are equal-weighted; no market-cap, future-volume or survivor
  weighting is introduced.

If the existing manifest/tooling cannot support those claims without using future
information, classify the checkpoint `SOURCE_BLOCKED_CROSS_ASSET_PIT_SEMANTICS` and stop
before model fitting.

### Source-only coverage gate

For each canonical eligible BTC decision timestamp, build the cross-asset feature vector
without looking at `r_24h` or its direction. A timestamp is source-feature-available only
when at least **30 non-BTC USDT spot assets** have all required complete endpoint bars.

An evaluation fold is admitted only when:

- source-feature coverage is at least 0.95 over that fold's canonical eligible BTC decision
  timestamps; and
- the source supplies at least 180 calendar days of causal pre-fold history usable for model
  training.

The source gate passes only with at least **5 chronological evaluation folds** and at least
**40,000 source-feature-available evaluation timestamps** in total. Fold inclusion is decided
from source availability only, never from returns, labels, model scores or win rates.

If this gate fails, classify `SOURCE_BLOCKED_CROSS_ASSET_COVERAGE` and stop before model
fitting. A source block consumes no predictive model configuration, creates no candidate and
is not a negative market result.

## 3. Frozen feature set

Create `PREDICTIVE_CROSS_ASSET_BREADTH_FEATURES_V1` with exactly eight features in this order.
At each BTC decision instant `T`, for every point-in-time-eligible non-BTC asset compute log
returns using complete hourly endpoint bars only:

- `r_1h = log(close[T] / close[T-1h])`;
- `r_24h_trailing = log(close[T] / close[T-24h])`;
- `r_168h_trailing = log(close[T] / close[T-168h])`.

The same asset set must possess all four required endpoint bars (`T`, `T-1h`, `T-24h`,
`T-168h`) and is then used for all eight statistics:

1. `BREADTH_UP_SHARE_1H` — fraction with `r_1h > 0`;
2. `BREADTH_UP_SHARE_24H` — fraction with `r_24h_trailing > 0`;
3. `BREADTH_UP_SHARE_168H` — fraction with `r_168h_trailing > 0`;
4. `CROSS_MEDIAN_RETURN_1H` — median `r_1h`;
5. `CROSS_MEDIAN_RETURN_24H` — median `r_24h_trailing`;
6. `CROSS_MEDIAN_RETURN_168H` — median `r_168h_trailing`;
7. `CROSS_MAD_RETURN_24H` — median absolute deviation from the cross-sectional median
   `r_24h_trailing`;
8. `CROSS_MAD_RETURN_168H` — median absolute deviation from the cross-sectional median
   `r_168h_trailing`.

No BTC price/return, funding, open-interest, order-flow, macro, calendar, news, sentiment or
on-chain feature is included. Universe size may be reported as source accounting but is not a
model feature. No clipping, winsorization, rank transform or feature selection.

Feature causality must be proven with deterministic synthetic tests, including insertion of a
future-only asset/bar that must not change the feature vector at `T`.

## 4. Folds, fitting and calibration

Reuse the frozen chronological BTC label substrate and evaluation scorer unchanged. Random
K-fold is forbidden. Use only source-admitted folds from §2; training is expanding
chronologically with the existing 24h purge/embargo semantics.

For each outer fold, among feature-valid training rows:

- chronological 80% base-fit / 20% probability-calibration split;
- 48h embargo between base-fit and calibration portions;
- calibration uses training-only rows;
- outer evaluation is unseen until candidate freeze;
- ties at calibrated `p_up = 0.5` declare `UP`;
- the candidate declares UP/DOWN whenever a valid feature vector exists; abstention is only
  source/feature unavailability.

### Configuration A — linear

Direction base estimator:

- `StandardScaler` fitted on base-fit rows only;
- `LogisticRegression`;
- L2 penalty;
- `C=1.0`;
- `fit_intercept=True`;
- `solver="lbfgs"`;
- `max_iter=2000`;
- `tol=1e-8`;
- no class weights.

Probability calibration: training-only Platt logistic map on the base estimator's raw
`decision_function`, using the same fixed calibration procedure already proven in the
prediction-generation infrastructure. No threshold search.

### Configuration B — nonlinear

Direction base estimator:

`HistGradientBoostingClassifier` with exactly:

- `learning_rate=0.05`;
- `max_iter=200`;
- `max_leaf_nodes=15`;
- `min_samples_leaf=50`;
- `l2_regularization=1.0`;
- `max_bins=255`;
- `early_stopping=False`;
- `random_state=20260917`.

No input scaling. Probability calibration is the same training-only Platt procedure. No
hyperparameter or threshold search.

Fail closed before outer scoring if a required training/calibration side lacks both
directional classes.

## 5. Controls, primary effect and multiplicity

Matched information-free control:

`TRAINING_UP_BASE_RATE`, fitted separately on each fold's chronological feature-valid
training rows and scored on the exact candidate-actionable evaluation timestamps.

Absolute reference:

`ALWAYS_UP`, scored on those same timestamps.

`PREVIOUS_24H_SIGN_PERSISTENCE` remains a descriptive canonical baseline only and may not be
inverted or used as a feature.

Primary effect for each configuration:

`candidate directional win rate - matched TRAINING_UP_BASE_RATE win rate`.

Minimum important effect (MESI): **+0.015 absolute win-rate points**.

Search family size = 2. Familywise alpha = 0.05. Bonferroni per-configuration alpha = 0.025.
The paired primary-effect interval is therefore the central **97.5%** fold-stratified
moving-block-bootstrap interval, using the frozen 48h block length and 10,000-replicate
infrastructure. The two configurations consume exactly 2 of 2 family slots.

## 6. Advancement gate

All conditions are mandatory for a configuration to advance to Research Director review:

1. pooled candidate coverage >= 0.95;
2. every source-admitted evaluation fold candidate coverage >= 0.90;
3. pooled matched primary delta >= +0.015;
4. lower bound of the paired 97.5% interval > 0;
5. candidate pooled win rate >= matched `ALWAYS_UP` win rate on identical timestamps;
6. candidate Brier score <= matched `TRAINING_UP_BASE_RATE` Brier score;
7. at least `ceil(2N/3)` source-admitted folds have non-negative candidate-minus-base-rate
   directional delta, where `N` is the number of source-admitted folds.

No secondary metric may rescue a failed gate. Do not tune a descendant from fold-level,
reliability-bin or disagreement observations.

Terminal classifications per configuration:

- `ADVANCE_CROSS_ASSET_BREADTH_LINEAR_V1` / `NO_ADVANCE_CROSS_ASSET_BREADTH_LINEAR_V1`;
- `ADVANCE_CROSS_ASSET_BREADTH_HGBR_V1` / `NO_ADVANCE_CROSS_ASSET_BREADTH_HGBR_V1`.

If neither advances, family disposition is `REJECTED_DEVELOPMENT_NO_SEALED`. If one or both
advance, disposition is `ADVANCE_TO_RESEARCH_DIRECTOR_REVIEW`; do not create a Champion,
query sealed data, start an observer or choose a post-hoc winner.

## 7. Pre-execution freeze and artifacts

Before any model outer-evaluation number exists, create and commit:

- `docs/contracts/PREDICTIVE_CROSS_ASSET_BREADTH_CONTEXT_V1.md`;
- `research/protocols/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-SEARCH-PLAN-V1.json`;
- both experiment preregistrations under `research/experiments/`;
- a source audit and pre-execution admission artifact that bind source identity, contract,
  preregistrations and implementation hashes;
- deterministic tests proving point-in-time universe membership, endpoint causality, no
  future-survival filter, feature identity and calibration separation.

Commit this admission checkpoint **before** executing either outer evaluation. Then execute
both configurations once if the source gate passed.

At completion produce:

- immutable result/trial records for each configuration;
- `reports/research/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1.{json,md}`;
- `reports/checkpoints/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1.md`;
- one update to `state/current_state.json`;
- archive this task and set the next `tasks/CURRENT_TASK.md` to Research Director review.

## 8. Boundaries

- BTCUSDT remains the sole prediction/product target.
- No new asset is authorized for trading.
- No Stage-1, funding or open-interest feature may enter the candidate.
- No basis, CFTC, macro, calendar, news, sentiment or on-chain source is admitted here.
- No sealed or post-cutoff query.
- No change to target, horizon, labels, scorer, bins, bootstrap block, MESI or existing
  experiment records.
- No Stage-1 substrate repair.
- Champion remains `NONE`.
- Real money remains `false`.

## 9. Validation

- backend tests PASS;
- frontend validation PASS if touched;
- `check.py --no-data` PASS;
- ruff / format / mypy PASS;
- deterministic replay with installed development data PASS;
- source audit reproducible from the tracked manifest and existing local artifact;
- prior six predictive results and family dispositions unchanged;
- exact family-search accounting;
- sealed queries 0;
- Champion `NONE`;
- real money `false`;
- working tree clean;
- commit and push to `main`;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE STAGE3 CROSS ASSET BREADTH V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, Research Director decisions, Source identity
and PIT audit, Source coverage gate, Included folds, Search-plan/admission hashes, Experiment
IDs, Feature set and point-in-time universe rule, Model/calibration procedures, Model fits,
Candidate win rates + coverage, Matched base-rate win rates/Brier, Matched ALWAYS_UP win
rates, Primary deltas + 97.5% intervals, Calibration, Per-fold deltas/coverage, Advancement
gates, Configuration classifications, Family disposition/search budget, Sealed eligibility,
Prior experiment integrity, Sealed queries, Champion, Real money, Validation, Exact-head CI,
Next action.
