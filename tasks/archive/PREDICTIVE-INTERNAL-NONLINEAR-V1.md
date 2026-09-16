# CURRENT TASK — PREDICTIVE-INTERNAL-NONLINEAR-V1

Status: ACTIVE_PREDICTIVE_MODELLING_RESERVED_CONFIGURATION

Predecessor: `PREDICTIVE-INTERNAL-STRUCTURE-V1` — executed, terminal classification
`NO_ADVANCE_INTERNAL_LINEAR_V1`, pending Research Director review.

Governing documents:

- `governance/SCIENTIFIC_CONSTITUTION.md` Version 2.0;
- `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md`, Amendment A1;
- `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`, Stage 1;
- `research/protocols/PREDICTIVE-BASELINES-V1.json`;
- `research/protocols/PREDICTIVE-STAGE1-INTERNAL-SEARCH-PLAN-V1.json`.

This checkpoint executes the **second and last** configuration of
`PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1`. That configuration —
`INTERNAL_HGBR_DUAL_HEAD_V1` — was frozen in full **before** the linear result was observed,
in commit `54dc831`, and is scheduled regardless of that result. The scientific design below
is not open for redesign; it is read from the committed search plan.

## 1. What is already frozen

`research/protocols/PREDICTIVE-STAGE1-INTERNAL-SEARCH-PLAN-V1.json`, configuration 2:

- experiment id `EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD`;
- direction head `HistGradientBoostingClassifier`, magnitude head
  `HistGradientBoostingRegressor` with squared-error loss;
- learning_rate 0.05, max_iter 200, max_leaf_nodes 15, min_samples_leaf 50,
  l2_regularization 1.0, max_bins 255, early_stopping False, random_state 20260916;
- the **identical** 18-feature causal set, feature validity rules, outer folds, 80/48h
  calibration split, training-only Platt calibration, action rule and scoring semantics as
  `INTERNAL_LINEAR_DUAL_HEAD_V1`;
- no hyperparameter search, no threshold search, no feature redesign.

Multiplicity is already allocated: familywise alpha 0.05, Bonferroni, **alpha 0.025** for
this configuration, central 97.5% paired interval. This checkpoint consumes Stage-1
configuration 2 of 2 and leaves 0 remaining.

The primary effect, the MESI of **+0.015** absolute win-rate points versus matched
`ALWAYS_UP`, the paired fold-stratified 48h moving-block bootstrap (10,000 replicates, seed
20260916) and the five advancement conditions are unchanged from
`PREDICTIVE-INTERNAL-STRUCTURE-V1` §6–§7. The pass classification is
`ADVANCE_INTERNAL_HGBR_V1` and the fail classification is `NO_ADVANCE_INTERNAL_HGBR_V1`.

## 2. Open question for the Research Director, before execution

`PREDICTIVE-INTERNAL-STRUCTURE-V1` failed both coverage gates for a substrate reason, not a
model reason: a single missing or incomplete canonical hourly bar invalidates the next 169
decision instants, so 5,106 of 64,323 admissible labels carry no feature vector, and
2019–2021 coverage lands at 0.884 / 0.859 / 0.890 against a 0.90 per-fold gate.

The reserved configuration shares the feature set and its validity rules exactly, so it will
abstain on exactly the same timestamps and will fail the same two coverage gates for the same
reason, before any question about nonlinearity is reached.

The executor must **not** resolve this. Changing the window rule, the gap policy or the
coverage thresholds after observing the linear result is post-result adaptation. The Research
Director decides, before execution, one of:

1. execute unchanged and accept that the two coverage conditions are predeclared failures
   whose cause is recorded, reading the directional conditions as the informative part; or
2. preregister a separate, explicitly reasoned coverage-policy amendment that applies to both
   Stage-1 configurations and restates why it is not a rescue; or
3. classify the checkpoint `REDESIGN_REQUIRED` and re-cut the Stage-1 substrate question in a
   new protocol version.

Execute option 1 by default if no direction is given, and report which option was taken.

## 3. Execution

1. Create `research/experiments/EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD/preregistration.json`
   from the committed search plan, changing nothing it already freezes.
2. Implement the HGBR heads beside the linear ones, reusing the frozen feature builder, fold
   builder, scorer and paired-inference module without modification.
3. Add synthetic tests for the new heads: determinism under the fixed random_state, the same
   training-only calibration separation proven for the linear head, and the same fail-closed
   behaviour when a split side lacks both directional classes.
4. Produce a pre-execution admission artifact hashing the new preregistration and the
   implementation.
5. Only then run the development-period outer evaluation once.
6. Report the complete Predictive Evaluation Contract, the paired 97.5% interval, the five
   advancement conditions, and a direct comparison against both the linear candidate and the
   canonical baselines.

## 4. Boundaries

- Stage 1 internal canonical BTCUSDT data only; no external information family.
- No post-cutoff or sealed data; sealed queries stay 0.
- No change to `PREDICTIVE-BASELINES-V1` or to `PREDICTIVE-INTERNAL-STRUCTURE-V1` results.
- No tuned descendant of the linear candidate, and no third Stage-1 model family.
- `PREVIOUS_24H_SIGN_PERSISTENCE` may not be inverted or negated into a feature.
- Champion stays `NONE`. Real money stays `false`.

## 5. Validation

Backend tests PASS; frontend validation PASS if touched; `check.py --no-data` PASS; ruff /
format / mypy PASS; deterministic result replay PASS with development data installed; exact
search-budget accounting; sealed queries 0; Champion `NONE`; real money `false`; clean tree;
commit and push to `main`; exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE INTERNAL NONLINEAR V1: PASS|PARTIAL|FAIL`

Then concise fields: Starting HEAD, Ending HEAD, Experiment ID, Hypothesis,
Preregistration/admission hash, Coverage-policy option taken, Model/calibration procedure,
Model fits, Candidate win rate + coverage, Matched ALWAYS_UP win rate, Primary delta + 97.5%
paired interval, Comparison against the linear candidate, Calibration, Magnitude error,
Per-fold deltas/coverage, Advancement gates, Terminal classification, Stage-1 search budget,
Sealed queries, Champion, Real money, Validation, Exact-head CI, Next action.
