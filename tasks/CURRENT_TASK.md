# CURRENT TASK — PREDICTIVE-INTERNAL-STRUCTURE-V1

Status: ACTIVE_PREDICTIVE_MODELLING

Predecessor: `PREDICTIVE-BASELINES-V1`
(see `reports/checkpoints/PREDICTIVE-BASELINES-V1.md`).

Governing documents: `governance/SCIENTIFIC_CONSTITUTION.md` Version 2.0,
`docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md` as amended by Amendment A1
(`decisions/ADR-0027-...`), and `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md` Stage 1.

This is the first checkpoint that may fit a predictor. It answers one question: does anything
in BTCUSDT's own price, volume and volatility structure predict the frozen 24h target better
than the baselines already recorded?

The bar is `ALWAYS_UP` at **0.5262**, not 0.5. Beating a coin is not a result.

## 1. Scope

- Stage 1 information only: internal price/return structure, volume/liquidity/volatility, and
  technical/microstructure features already governed by existing contracts. No Stage 2+ family.
- Features must be computed from bars with open time `<= T` and must pass the existing
  look-ahead guard in `app.predictive.labels.assert_causal`.
- Reuse the frozen substrate unchanged: `app.predictive.labels`, `folds`, `evaluation`,
  `baselines`. If a defect is found in them, fix it and re-run everything, including the
  baseline report — but a *change of design* to those modules is a new protocol version.
- Any tuning happens strictly inside a fold's training portion. The evaluation portion is
  unseen until candidate freeze.

## 2. Preregistration

This checkpoint **does** produce a predictive claim, so it requires a preregistration under
`research/experiments/<experiment_id>/` before execution, declaring:

- the hypothesis and the single primary metric;
- the feature set and how each feature is causally computed;
- the model family and its hyperparameters, or the search space and its trial budget;
- the minimum important effect in the primary metric, relative to `ALWAYS_UP`;
- multiplicity-family membership and search-budget consumption;
- the abstention/coverage policy, fixed before results.

Freeze it before any evaluation-fold number is observed.

## 3. Mandatory reporting

Everything in `PREDICTIVE_EVALUATION_CONTRACT_V1` §4, with each metric applying exactly when
the quantity it scores is declared. At minimum: win rate with sample size and coverage,
calibration if a probability is declared, magnitude MAE and the signed magnitude-match
diagnostic if a magnitude is declared, comparison against all four baselines on the identical
eligible universe, the dependence-aware interval, and every fold including unfavourable ones.

A candidate that beats 0.5 but not `ALWAYS_UP` is reported as not interesting, not as an edge.

## 4. Boundaries

- Stage 1 internal data only; no external or post-cutoff data; no sealed query.
- No change to the frozen labels, folds, bins, block length, seed or baseline definitions.
- No re-cutting folds, no coverage re-tuning, no threshold rescue after results.
- The `PREVIOUS_24H_SIGN_PERSISTENCE` sub-50% observation may **not** be inverted into a
  strategy; it is a recorded observation, and acting on it is result-driven adaptation.
- The prospective ALIGNED observer stays `SUSPENDED_BY_OWNER_OBJECTIVE_PIVOT` with its
  preserved evidence byte-identical.
- Champion remains `NONE`; real money remains `false`.

## 5. Artifacts

- preregistration, trials and result under `research/experiments/<experiment_id>/`;
- implementation under `backend/app/predictive/`;
- tests covering feature causality and the new scoring paths;
- a comparison report under `reports/research/`;
- `state/current_state.json` updated once;
- `reports/checkpoints/PREDICTIVE-INTERNAL-STRUCTURE-V1.md`;
- an ADR only for a material design decision;
- `tasks/CURRENT_TASK.md` updated at completion.

## 6. Validation

- backend tests PASS;
- frontend validation PASS if touched;
- `check.py --no-data` PASS;
- ruff / format / mypy PASS;
- no sealed queries;
- Champion `NONE`;
- real money `false`;
- working tree clean;
- commit and push to `main`;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE INTERNAL STRUCTURE V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, Hypothesis, Preregistration, Feature set,
Model family, Model fits, Win rate with coverage, Calibration, Magnitude error, Baseline
comparison, Uncertainty interval, Per-fold results, Terminal classification, Sealed queries,
Champion, Real money, Validation, Exact-head CI, Next action.
