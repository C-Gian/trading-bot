# Checkpoint — PREDICTIVE-GENERATION-V2-SELECTIVE-LONG-REBASELINE-V1

Status: **COMPLETE**. Governance and deterministic-evaluation rebaseline only.

Starting HEAD `1d37f35895f4ca45cc41d99ac6033d1336063020`. No predictive model was fitted, no
market prediction was produced, no experiment record was created, and no sealed or post-cutoff
data was queried. Sealed queries remain 0, Champion remains `NONE`, real money remains `false`.

## 1. Generation V1 closes

`PREDICTIVE_RESEARCH_GENERATION_V1` is closed with disposition
`CLOSED_NO_DIRECTIONAL_ADMISSION_NO_SEALED`, recorded immutably in
[ADR-0028](../../decisions/ADR-0028-GENERATION-V2-SELECTIVE-LONG-REBASELINE.md).

Five genuinely executed information families were tested against the frozen BTCUSDT 24h
terminal direction target: internal market structure, settled funding, open interest,
cross-asset breadth, and strict point-in-time macro release state. Ten predictive
configurations were consumed — `EXP-PRED-001` through `EXP-PRED-010`. None advanced. None is
sealed-eligible.

`PREDICTIVE-STAGE3-MACRO-VINTAGE-V1` is a source block, not a market-result family: 0 fits,
0 outer predictions, 0 configurations consumed. It is not counted among the ten.

The closure does **not** establish that BTCUSDT is unpredictable. It establishes that the
tested always-declare 24h formulations failed to add credible directional information over
their frozen controls. Four of the five families passed coverage cleanly, so substrate quality
explains none of it.

No V1 result may be rescued by inversion, thresholding, fold removal, hyperparameter search,
feature pruning or re-execution. Every V1 result file, source audit, admission, checkpoint
report and residual record remains byte-identical.

## 2. Ruling on the macro residual source defect

The committed negative macro result **stands as recorded**. The defect exposed future-dated
`VIXCLS` observation labels at 1.43% of evaluation instants and 0.87% of training instants; a
lookahead can only flatter a candidate, and both macro configurations were rejected by wide
margins, so it cannot have manufactured the observed negative result.

Neither macro result is re-run or rewritten. The wording gap is closed prospectively by
[`ALFRED_OBSERVATION_DATE_GUARD_V1`](../../docs/contracts/ALFRED_OBSERVATION_DATE_GUARD_V1.md),
which requires, at decision timestamp `T`, both `availability_time <= T` **and**
`observation_date <= UTC_date(T)`. Later vintage revisions remain usable only from their own
availability time; current-revised substitution, interpolation and nearest-future substitution
remain forbidden. No old macro contract or historical artifact is modified, and the exhausted
macro source-redesign budget is not revived.

## 3. Generation V2 opens

`PREDICTIVE_RESEARCH_GENERATION_V2` tests **selective directional prediction** rather than
universal hourly classification, under
[`PREDICTIVE_EVALUATION_CONTRACT_V2`](../../docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V2.md)
(Amendment B1). The change is preregistered here, after V1 closure, for candidates that do not
yet exist, and is never applied retrospectively to a V1 model score.

Target, cadence and horizon are deliberately unchanged — BTCUSDT spot, each completed UTC 1h
bar, 24h terminal, `r_24h = log(close[T+24h] / close[T])`. Changing selectivity and horizon at
once would confound the two.

**Action policy, frozen:** every candidate emits a calibrated `p_up = P(r_24h > 0)` at every
feature-valid eligible timestamp; `LONG` iff `p_up >= 0.60`, otherwise `NO_TRADE`; exactly 0.60
acts `LONG`. A model that cannot emit calibrated probabilities may not participate. No `SHORT`.
The threshold may never be tuned on development results.

**Primary metric:** `SELECTIVE_LONG_WIN_RATE = UP truths / actionable LONG predictions`, never
reported without actionable `N`, action coverage, per-fold distribution, interval and
calibration.

**Primary control:** `FULL_FOLD_UP_RATE`, the UP frequency over every directionally scorable
eligible timestamp in the same fold, computed without candidate action selection. The primary
effect is the enrichment `SELECTIVE_LONG_WIN_RATE - FULL_FOLD_UP_RATE`. Evaluation-fold truth
enters this control for scoring only and is never visible to fitting, calibration, threshold
choice or fold selection. A secondary `FEATURE_VALID_FOLD_UP_RATE` is reported per fold so an
enrichment that is really a source-coverage artifact stays visible.

## 4. The ten frozen advancement conditions

| # | Condition | Threshold |
| --- | --- | --- |
| 1 | pooled LONG action coverage | >= 0.02 |
| 2 | every fold LONG action coverage | >= 0.005 |
| 3 | pooled actionable LONG count | >= 500 |
| 4 | every fold actionable LONG count | >= 30 |
| 5 | pooled selective LONG win rate | >= 0.60 |
| 6 | pooled enrichment over `FULL_FOLD_UP_RATE` | >= +0.05 |
| 7 | enrichment interval lower bound | > 0 |
| 8 | folds with non-negative enrichment | >= `ceil(2N/3)` |
| 9 | full-probability Brier over feature-valid outer rows | <= matched `TRAINING_UP_BASE_RATE` Brier |
| 10 | action calibration gap among actionable LONGs | <= 0.05 |

All must hold; no secondary metric rescues one; none may be weakened after a V2 candidate
result. Conditions 1–4 refuse a cosmetically high win rate built from a handful of actions,
5–8 test directional enrichment, 9–10 require the displayed probabilities to mean what they
claim.

## 5. Dependence-aware inference

Fold-stratified moving-block bootstrap, 48h blocks, 10,000 replicates, a fixed integer seed
declared per family before execution, blocks never crossing a fold boundary, and both the
selected LONG win rate and the same-fold full-universe UP rate recomputed on every replicate so
the enrichment interval is genuinely paired. Abstentions, `NO_TRADE` rows, feature-invalid rows
and canonical gaps keep their hour slot and contribute no record, so nothing is pulled into
adjacency. A replicate that draws no actionable LONG is discarded and counted; above a 1%
discard share the interval is `UNSTABLE_RESAMPLE_SUPPORT` and condition 7 fails closed.
Familywise alpha 0.05, Bonferroni over the declared family size. Reliability bins are inherited
from V1 unchanged.

## 6. Deterministic scorer and synthetic proofs

`backend/app/predictive/selective_long.py` implements the freeze and nothing else: the action
policy, the counting rules, the pooled and per-fold summaries, the enrichment interval and the
ten conditions. It fits no model and reads no market data.

`backend/tests/test_predictive_selective_long_scorer.py` pins its behaviour with 23 hand-worked
synthetic cases before any candidate exists, including: exact `p_up = 0.60` acts `LONG`;
anything below is `NO_TRADE`; an exact-zero truth is counted but never a win; a feature-invalid
row leaves every rate alone; a perfect selective predictor passes; an always-wrong selector
fails the directional conditions; one flawless action fails the coverage and count floors; 1%
pooled coverage fails the 2% gate; a 60% hit rate inside a 60% fold shows zero enrichment and
fails; 65% against a 55% fold passes the effect conditions; overconfident 0.90 probabilities
against a 0.65 hit rate fail action calibration; an extreme-probability model fails the
full-probability Brier condition; pooled rates are recomputed from counts and never averaged;
and the bootstrap is bit-identical for a fixed seed and moves with a different one.

## 7. Magnitude and search memory

`MAGNITUDE_STATUS = DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`. Magnitude remains a required
product goal and is not a V2 advancement head; a separate preregistered magnitude head is
required before any user-facing "strength 0–100" is shown.

Search memory carries forward in full: every V1 family disposition, all ten executed
configuration results, every source block, the adaptive-search and search-burden records, the
Stage-1 substrate debt, basis deferred, the exhausted macro source-redesign budget, the ban on
cross-asset inversion, and sealed queries 0. New V2 hypotheses receive new IDs and new budgets,
and no rejected V1 result becomes evidence merely because the scorer changed.

## 8. Validation

Prior V1 result files and the macro residual finding byte-identical; 0 new predictive model
fits; 0 new market predictions; sealed queries 0; Champion `NONE`; real money `false`. Backend
tests, frontend lint/typecheck/tests/build, ruff check and format, mypy,
`scripts/check.py --no-data` and the full installed-development-data validation all pass, and
the deterministic synthetic scorer tests pass.

Next: `RESEARCH_DIRECTOR_REVIEW_GENERATION_V2_REBASELINE`.
