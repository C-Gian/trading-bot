# CURRENT TASK — PREDICTIVE-GENERATION-V2-SELECTIVE-LONG-REBASELINE-V1

Status: ACTIVE_GOVERNANCE_AND_EVALUATION_REBASELINE_NO_MARKET_MODEL_EXECUTION

Starting HEAD: `1d37f35895f4ca45cc41d99ac6033d1336063020` on `main`.

This checkpoint closes `PREDICTIVE_RESEARCH_GENERATION_V1` and opens
`PREDICTIVE_RESEARCH_GENERATION_V2` around the Owner's actual product objective:
a calibrated BTCUSDT LONG / NO_TRADE predictor that acts only when the evidence is strong
enough, rather than being forced to declare UP or DOWN every hour.

No predictive model may be fitted in this checkpoint. No sealed/post-cutoff BTC data may be
queried. This is a design, governance and deterministic-evaluation checkpoint only.

## 1. Research Director verdict on Generation V1

Record an immutable review/decision artifact with all of the following:

1. `PREDICTIVE_RESEARCH_GENERATION_V1` is closed with disposition
   `CLOSED_NO_DIRECTIONAL_ADMISSION_NO_SEALED`.
2. Five genuinely executed information families were tested on the frozen 24h terminal
   direction target: internal market structure, settled funding, open interest, cross-asset
   breadth and strict point-in-time macro release state.
3. Ten predictive configurations were consumed. None advanced. None is sealed-eligible.
4. The earlier macro-vintage V1 checkpoint is a source block, not a market-result family, and
   must not be counted among the ten executed configurations.
5. Sealed queries remain 0. Champion remains `NONE`. Real money remains `false`.
6. V1 does **not** establish that BTC is unpredictable. It establishes that the tested
   always-declare 24h formulations failed to add credible directional information over their
   frozen controls.
7. Do not rescue any V1 result by inversion, thresholding, fold removal, hyperparameter search,
   feature pruning or re-execution.

## 2. Research Director ruling on the macro residual source defect

Accept the committed negative macro result as standing. The residual VIX defect exposed future-
dated observation labels to 1.43% of evaluation instants and therefore could only have made the
candidate look better, not create the observed wide negative margins.

Do not re-run or rewrite either macro result.

Create a prospective source-only guard for all future ALFRED use:

`docs/contracts/ALFRED_OBSERVATION_DATE_GUARD_V1.md`

It must require, at decision timestamp T:

- `availability_time <= T`; and
- `observation_date <= UTC_date(T)`.

Later vintage revisions remain usable only once their own availability time is reached.
Current-revised substitution, interpolation and nearest-future substitution remain forbidden.

Do not modify the old macro contracts or historical result artifacts. The new guard applies
prospectively to Generation V2 and later.

## 3. Why Generation V2 changes the evaluation question

Generation V1 forced nearly every eligible hour into a directional declaration. That is useful
for testing universal classification, but it is not the desired V1 product behaviour.

The Owner wants:

- `LONG` when the bot has sufficiently strong evidence BTC will be higher 24h later;
- otherwise `NO_TRADE`;
- a probability that has an empirical calibration meaning;
- later, a separate estimate of movement strength/magnitude.

Generation V2 therefore tests **selective directional prediction** rather than universal
hourly classification.

The scientific change is preregistered now, after V1 closure, and is not applied
retrospectively to any V1 model score.

## 4. Frozen Generation V2 target and action semantics

Product/prediction universe remains BTCUSDT spot only.

Decision cadence remains each completed UTC 1h bar.

Primary forecast horizon remains **24h terminal** for Generation V2. This deliberately changes
only selectivity/action semantics first; it does not simultaneously search a new horizon.

Truth at decision timestamp T:

`r_24h = log(close[T+24h] / close[T])`.

- `UP` if `r_24h > 0`;
- `DOWN` if `r_24h < 0`;
- exact zero is `NEUTRAL`, counted explicitly and excluded from directional wins.

Every candidate model must produce a calibrated `p_up = P(r_24h > 0)` for every feature-valid
eligible timestamp.

Action policy is frozen:

- `LONG` iff calibrated `p_up >= 0.60`;
- otherwise `NO_TRADE`.

Exactly 0.60 is a product/scientific threshold chosen before any Generation V2 candidate is
run. It may not be tuned on development results.

A model that does not emit calibrated probabilities may not participate.

Generation V2 does not authorize SHORT.

## 5. Primary metric: selective LONG win rate with enrichment control

For candidate LONG actions:

`SELECTIVE_LONG_WIN_RATE = UP truths / actionable LONG predictions`.

Win rate may never be reported without:

- actionable N;
- action coverage = LONG actions / feature-valid eligible timestamps;
- chronological distribution by fold;
- confidence interval;
- calibration diagnostics.

The primary causal/predictive question is not merely whether LONGs win above 50%. It is whether
the model **enriches** for UP outcomes relative to the contemporaneous fold environment.

Primary matched control:

`FULL_FOLD_UP_RATE` = UP frequency over all directionally scorable eligible timestamps in the
same evaluation fold, without using candidate action selection.

Primary effect:

`SELECTIVE_LONG_WIN_RATE - FULL_FOLD_UP_RATE`.

This control may use evaluation-fold truth for scoring only; it is never visible to fitting,
calibration or thresholding.

Secondary references:

- training-only `TRAINING_UP_BASE_RATE`;
- `ALWAYS_UP` full-fold win rate;
- previous 24h sign persistence, descriptive only and never inverted.

## 6. Frozen Generation V2 advancement semantics

A future Generation V2 candidate may advance only if **all** of the following hold:

1. pooled LONG action coverage >= 0.02;
2. every included fold LONG action coverage >= 0.005;
3. pooled actionable LONG count >= 500;
4. every included fold actionable LONG count >= 30;
5. pooled selective LONG win rate >= 0.60;
6. pooled enrichment over `FULL_FOLD_UP_RATE` >= +0.05 absolute;
7. lower bound of the dependence-aware primary interval > 0;
8. at least `ceil(2*N_folds/3)` folds have non-negative enrichment;
9. full-probability Brier score over all feature-valid outer rows <= matched
   `TRAINING_UP_BASE_RATE` Brier;
10. among actionable LONGs,
    `abs(mean_predicted_p_up - empirical_LONG_win_rate) <= 0.05`.

These thresholds are frozen in this checkpoint and may not be weakened after any V2 candidate
result.

The purpose of conditions 1-4 is to prevent a cosmetically high win rate from a tiny number of
cherry-picked actions. Conditions 5-8 test actual directional enrichment. Conditions 9-10
require the displayed probabilities to mean what they claim.

## 7. Dependence-aware inference

Create a Generation V2 evaluation contract or Amendment B1 under
`docs/canonical/` that freezes:

- fold-stratified moving-block bootstrap;
- 48h block length;
- 10,000 replicates;
- a fixed seed declared per future family before execution;
- bootstrap recomputation of both selected LONG win rate and same-fold full-universe UP rate;
- paired enrichment interval;
- exact handling of NEUTRAL truths and abstentions;
- fixed reliability bins inherited from V1 unless an explicit versioned change is justified
  here before candidate execution.

Add deterministic hand-worked/synthetic tests covering at least:

- perfect selective predictor;
- always-wrong selector;
- selector with 1 action: excellent win rate but fails N/coverage gates;
- selector with 1% pooled coverage: fails the 2% gate;
- selector with 60% hit rate but no enrichment versus a 60% fold base rate: fails enrichment;
- selector with 65% hit rate versus 55% fold base rate: passes the directional effect pieces;
- overconfident 0.90 probabilities with 0.65 empirical hit rate: fails action calibration;
- exact threshold p_up=0.60 acts LONG;
- p_up<0.60 is NO_TRADE;
- exact-zero truth counted but not a win;
- bootstrap determinism.

No development-market candidate result is part of this checkpoint.

## 8. Magnitude / strength disposition

Magnitude remains a required product goal but is **not yet** a Generation V2 advancement head.

Record:

`MAGNITUDE_STATUS = DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`.

Reason: every V1 magnitude head that was executed failed to beat zero-return magnitude, and
forcing a magnitude search before a directional signal exists would expand search burden
without evidence.

Once a V2 directional candidate advances development, the next research package must define a
separate preregistered magnitude/strength head before any user-facing "strength 0-100" is shown.

## 9. Search-memory carryover

Generation V2 is not a reset of scientific memory.

Carry forward explicitly:

- all V1 family dispositions;
- all ten executed V1 configuration results;
- all source blocks;
- all adaptive-search/search-burden records;
- Stage-1 substrate debt;
- basis deferred;
- macro source redesign budget exhausted;
- cross-asset inversion forbidden;
- sealed queries 0.

New V2 hypotheses receive new IDs and new search budgets. They may reuse causal source
infrastructure, but no rejected V1 result becomes evidence merely because the scorer changed.

## 10. Required repository changes

This checkpoint must:

1. archive the current Research-Director review task;
2. create an immutable Research Director V1-closure / V2-opening decision record;
3. create `ALFRED_OBSERVATION_DATE_GUARD_V1.md`;
4. version/update the predictive evaluation contract for selective LONG semantics;
5. update `governance/SCIENTIFIC_CONSTITUTION.md` only where needed to reference Generation V2
   without deleting or rewriting Version 2.0 history;
6. update `state/current_state.json` with one canonical V1 closure record and one V2 current
   objective record;
7. implement deterministic evaluation/scorer utilities and synthetic tests only;
8. create no market-model experiment, no model fit and no outer prediction;
9. write the next `tasks/CURRENT_TASK.md` as
   `RESEARCH-DIRECTOR-REVIEW-GENERATION-V2-REBASELINE` unless validation finds a defect that
   requires fail-closed handling.

## 11. Validation and invariants

Require:

- prior V1 result files byte-identical;
- macro residual finding byte-identical;
- 0 new predictive model fits;
- 0 new market predictions;
- sealed queries 0;
- Champion `NONE`;
- real money `false`;
- backend tests PASS;
- frontend validation PASS if touched;
- ruff check/format PASS;
- mypy PASS;
- `scripts/check.py --no-data` PASS;
- installed-development-data validation PASS without generating a V2 candidate result;
- deterministic synthetic scorer tests PASS;
- clean tree;
- commit and push to `main`;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE GENERATION V2 SELECTIVE LONG REBASELINE: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, V1 generation disposition, V1 executed
families/configurations, macro residual ruling, ALFRED future guard, V2 objective, target/horizon,
probability/action definition, selective win-rate metric, primary enrichment control, action
coverage/N gates, calibration gates, inference contract, magnitude disposition, search-memory
carryover, model fits, market predictions, sealed queries, Champion, real money, validation,
exact-head CI, next action.
