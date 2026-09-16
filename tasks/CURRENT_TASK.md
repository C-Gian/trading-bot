# CURRENT TASK — PREDICTIVE-BASELINES-V1

Status: ACTIVE_PREDICTIVE_FOUNDATION

Predecessor: `PREDICTIVE-RESEARCH-REBASELINE-V1`
(see `reports/checkpoints/PREDICTIVE-RESEARCH-REBASELINE-V1.md`).

Owner authorization: the prediction-first objective is Owner-authorized in
`decisions/ADR-0026-PREDICTION-FIRST-RESEARCH-OBJECTIVE.md` and
`governance/SCIENTIFIC_CONSTITUTION.md` Version 2.0.

This is the first implementation checkpoint of `PREDICTIVE_RESEARCH_GENERATION_V1`. It is a
foundation, not a model. It must prove that labels are causal and that the evaluation
implementation is correct **before** any model complexity and before any external
information family.

Do not train a predictor. Do not admit a new information family. Do not inspect sealed
post-cutoff BTCUSDT market data. Do not authorize real money.

## 1. Scope

Implement, under `backend/app/predictive/`:

1. **Deterministic label construction** for the frozen target in
   `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md` §1:
   `r_24h = log(close[t+24h] / close[t])` at 1h closed-bar UTC decision timestamps over the
   canonical 1m development dataset, strictly within the development cutoff.
   - eligibility, admissibility and `NEUTRAL` handling exactly as §1 specifies;
   - every exclusion typed and counted; no silent drop;
   - no interpolation across canonical gaps.
2. **The evaluation implementation** for §3–§7: win rate, coverage, sample accounting,
   Brier score and the fixed-bin reliability table, magnitude MAE and median absolute
   error, the signed magnitude-match diagnostic with its deterministic zero rules, the
   dependence-aware moving-block bootstrap interval, and per-fold reporting.
3. **The four required baselines** of §5, scored on the identical eligible universe:
   `TRAINING_UP_BASE_RATE`, `ALWAYS_UP`, `PREVIOUS_24H_SIGN_PERSISTENCE`,
   `ZERO_RETURN_MAGNITUDE`.
4. **Chronological folds** with purge and embargo of at least the label horizon on both
   sides of every boundary. Standard random K-fold remains forbidden.

## 2. Causality proof obligations

The checkpoint is not complete unless the following are proven by deterministic tests, not
asserted in prose:

- a label at decision timestamp `t` uses no bar at or before `t` other than `close[t]`, and
  no bar after `t + 24h`;
- shifting the input series forward in time changes the label set in exactly the expected
  way, and shifting it backward is detected;
- a feature computed at `t` from a deliberately leaked future bar is caught by an explicit
  look-ahead guard;
- the last admissible decision timestamp is exactly one horizon before the end of the
  canonical coverage, and timestamps after it are excluded and counted;
- canonical gaps produce inadmissible labels rather than interpolated ones;
- a `NEUTRAL` truth is never counted as a win and never silently dropped.

## 3. Evaluation-correctness proof obligations

Prove the scorer on synthetic fixtures with known answers before it touches market data:

- a perfect predictor scores win rate 1.0 with coverage 1.0;
- an always-wrong predictor scores 0.0;
- a predictor that abstains everywhere but one correct timestamp scores win rate 1.0 with
  near-zero coverage, and the report makes that visible;
- Brier score and the reliability table reproduce hand-computed values on a fixture;
- the magnitude-match diagnostic returns `+100` on exact match, `+10` on a ten-times miss in
  either direction, the negative of that on a wrong direction, and excludes-and-counts each
  of the three near-zero classes;
- the moving-block bootstrap interval is wider than the naive Wilson interval on
  deliberately overlapping labels;
- every baseline is scored on the identical eligible universe as the model under test.

## 4. Preregistration

This checkpoint produces no predictive claim, so it needs no experiment preregistration.
It must, however, freeze in a protocol record under `research/protocols/`:

- the fold boundaries and the purge/embargo width;
- the moving-block bootstrap block length;
- the reliability-table bin edges;
- the eligible-universe definition.

These are declared before any baseline number is observed on market data, and are not
revised afterwards.

## 5. What may be observed

Baseline numbers on development-period data may be observed and recorded. They are
reference points, not a result: no baseline is a candidate, no baseline is promoted, and no
Champion is created. Record them as a baseline report, not as an experiment result.

If a baseline reveals a defect in labels or scoring, fix the defect and re-run; that is not
a result-dependent adaptation because no predictive hypothesis is under test.

## 6. Boundaries

- No model fit of any kind. No sklearn estimator, no optimizer, no hyperparameter search.
- No new information family; internal canonical price data only.
- No sealed query. No post-cutoff market data.
- No change to any historical experiment record or terminal classification.
- No change to the frozen ALIGNED strategy semantics.
- The prospective ALIGNED observer stays `SUSPENDED_BY_OWNER_OBJECTIVE_PIVOT`; its
  preserved evidence stays byte-identical.
- Champion remains `NONE`; real money remains `false`.

## 7. Artifacts

At minimum:

- `backend/app/predictive/` implementation modules;
- `backend/tests/` covering every obligation in §2 and §3;
- `research/protocols/PREDICTIVE-BASELINES-V1.json`;
- a baseline report under `reports/research/`;
- `state/current_state.json` updated once;
- one checkpoint report under `reports/checkpoints/PREDICTIVE-BASELINES-V1.md`;
- an ADR only if a material design decision is taken;
- `tasks/CURRENT_TASK.md` updated at completion to the next checkpoint.

## 8. Validation

- backend tests PASS;
- frontend validation PASS if touched;
- `check.py --no-data` PASS;
- ruff / format / mypy PASS;
- no sealed queries;
- no model fit;
- Champion `NONE`;
- real money `false`;
- working tree clean;
- commit and push to `main`;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE BASELINES V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, Labels implemented, Eligible timestamps,
Admissible labels, NEUTRAL count, Excluded-and-counted breakdown, Causality proofs,
Evaluation-correctness proofs, Baseline win rates with coverage, Baseline magnitude MAE,
Fold design, Model fits, Sealed queries, Champion, Real money, Validation, Exact-head CI,
Next action.
