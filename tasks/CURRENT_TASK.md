# CURRENT TASK — RESEARCH-DIRECTOR-REVIEW-STAGE-2-CLOSURE

Status: AWAITING_RESEARCH_DIRECTOR_REVIEW_NO_EXECUTOR_WORK_AUTHORIZED

Predecessor: `PREDICTIVE-STAGE2-SETTLED-FUNDING-V1` — executed, family disposition
`REJECTED_DEVELOPMENT_NO_SEALED`.

`PREDICTIVE_STAGE2_SETTLED_FUNDING_FAMILY_V1` is **closed**. Both predeclared configurations
were executed in one work package, the search budget is fully consumed, and nothing is
reserved.

## Where the predictive generation now stands

Four experiments have been executed on the frozen BTCUSDT 24h terminal target. None advanced.

| family | configuration | win rate | coverage | primary delta | 97.5% paired interval | classification |
| --- | --- | --- | --- | --- | --- | --- |
| Stage 1 internal | `INTERNAL_LINEAR_DUAL_HEAD_V1` | 0.4888 | 0.9357 | −0.0351 vs `ALWAYS_UP` | [−0.0608, −0.0080] | `NO_ADVANCE_INTERNAL_LINEAR_V1` |
| Stage 1 internal | `INTERNAL_HGBR_DUAL_HEAD_V1` | 0.4896 | 0.9357 | −0.0343 vs `ALWAYS_UP` | [−0.0575, −0.0100] | `NO_ADVANCE_INTERNAL_HGBR_V1` |
| Stage 2 funding | `FUNDING_LINEAR_DUAL_HEAD_V1` | 0.4855 | 0.99998 | −0.0093 vs base rate | [−0.0296, +0.0126] | `NO_ADVANCE_FUNDING_LINEAR_V1` |
| Stage 2 funding | `FUNDING_HGBR_DUAL_HEAD_V1` | 0.4941 | 0.99998 | −0.0006 vs base rate | [−0.0177, +0.0174] | `NO_ADVANCE_FUNDING_HGBR_V1` |

Both Stage-1 intervals lie entirely below zero against matched `ALWAYS_UP`. Both Stage-2
intervals straddle zero against the information-free base-rate control, and both candidates
sit clearly below matched `ALWAYS_UP` (−0.0415 and −0.0329). All four are worse-calibrated
than a constant training base rate, and three of four magnitude heads are worse than
predicting zero.

Two independent failure modes have been separated:

- **Stage 1** failed its coverage gates for a substrate reason — one missing canonical hourly
  bar invalidates the next 169 decision instants — *and* failed every directional condition.
- **Stage 2** passed both coverage gates at 0.99998 and failed on directional evidence alone.
  Coverage is therefore no longer a confound.

Both families are `REJECTED_DEVELOPMENT_NO_SEALED`; all four configurations are
`NOT_ELIGIBLE_REJECTED_DEVELOPMENT`.

## No executor work is authorized by this file

There is no preregistered experiment to run. Specifically forbidden without a new
Research-Director-frozen design:

- any tuned descendant of any of the four executed configurations;
- a third configuration in either closed family;
- a change to the frozen target, horizon, labels, folds, scorer, reliability bins, bootstrap
  parameters, MESI, alpha allocation or advancement conditions;
- acquiring or admitting open interest, basis, position ratios, CFTC, macro, news or on-chain
  data;
- repairing canonical hourly gaps or relaxing the Stage-1 contiguity rule;
- inverting or negating `PREVIOUS_24H_SIGN_PERSISTENCE`;
- any sealed or post-cutoff query.

Champion stays `NONE`. Real money stays `false`.

## Decisions the Research Director owns

1. **Another Stage-2 series.** Whether to admit a further derivatives series — open interest
   or basis — under its own preregistered incremental-information experiment, given that
   settled funding alone carried no directional information.
2. **Substrate debt.** Whether to pay down the Stage-1 canonical hourly gap defect under an
   independent protocol justified on its own terms. It may not be framed as a rescue of
   `EXP-PRED-001` or `EXP-PRED-002`, whose results stand as observed. Note that Stage 2 shows
   the defect was never the reason the directional evidence failed.
3. **The target itself.** Whether four rejections on a 24h terminal direction warrant
   revisiting the horizon or the prediction target, which would open a new research
   generation rather than another family inside this one.
4. **Generation disposition.** Whether `PREDICTIVE_RESEARCH_GENERATION_V1` continues with a
   Stage-3 family, pauses, or is recorded with an explicit disposition.

## If the Owner or Research Director asks for the next work package

Write it as a new `tasks/CURRENT_TASK.md` with a frozen design, exactly as the four executed
experiments were frozen: hypothesis, primary metric, MESI, matched control, evaluation design,
parameter/search space, trial budget and advancement gate all declared before execution, with
a pre-execution admission artifact binding the preregistration, the source identity and the
implementation hashes.

## Validation for any future package

Backend tests PASS; frontend validation PASS if touched; `check.py --no-data` PASS; ruff /
format / mypy PASS; deterministic result replay PASS with development data installed; exact
search-budget accounting; sealed queries 0; Champion `NONE`; real money `false`; clean tree;
commit and push to `main`; exact-head CI SUCCESS.
