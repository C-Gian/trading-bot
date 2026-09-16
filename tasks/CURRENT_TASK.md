# CURRENT TASK — RESEARCH-DIRECTOR-REVIEW-STAGE-1-CLOSURE

Status: AWAITING_RESEARCH_DIRECTOR_REVIEW_NO_EXECUTOR_WORK_AUTHORIZED

Predecessor: `PREDICTIVE-INTERNAL-NONLINEAR-V1` — executed, terminal classification
`NO_ADVANCE_INTERNAL_HGBR_V1`.

`PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1` is **closed**. Both predeclared configurations
have been executed, the search budget is fully consumed, and nothing is reserved.

## What Stage 1 established

| configuration | experiment | win rate | coverage | matched delta | 97.5% paired interval | classification |
| --- | --- | --- | --- | --- | --- | --- |
| `INTERNAL_LINEAR_DUAL_HEAD_V1` | `EXP-PRED-001` | 0.4888 | 0.9357 | −0.0351 | [−0.0608, −0.0080] | `NO_ADVANCE_INTERNAL_LINEAR_V1` |
| `INTERNAL_HGBR_DUAL_HEAD_V1` | `EXP-PRED-002` | 0.4896 | 0.9357 | −0.0343 | [−0.0575, −0.0100] | `NO_ADVANCE_INTERNAL_HGBR_V1` |

Matched `ALWAYS_UP` on the same timestamps: 0.5239. Canonical full-universe reference bar:
0.5262.

Both multiplicity-adjusted intervals lie entirely below zero. This is not an absence of
evidence — it is evidence that both configurations are worse than always predicting UP, on
the 18 frozen causal internal price, volume and volatility features, over 2019–2024.

The two configurations declared a side on the identical 48,953 timestamps and agreed on
79.75% of them. The nonlinear head's disagreements bought +0.0008 of win rate while costing
calibration (Brier 0.2546 vs 0.2534) and magnitude accuracy (MAE 2.4081 pp vs 2.3042 pp, both
worse than the 2.2635 pp of `ZERO_RETURN_MAGNITUDE`). Added capacity fitted noise.

Both checkpoints also failed both coverage gates, for one substrate reason: a single missing
or incomplete canonical hourly bar invalidates the next 169 decision instants, so 5,106 of
64,323 admissible labels carry no feature vector and 2019–2021 coverage is 0.884 / 0.859 /
0.890. The Research Director ruled option 1 before execution — execute unchanged, gates
unwaived — and that ruling is recorded in both the preregistration and the admission artifact
of `EXP-PRED-002`.

## No executor work is authorized by this file

There is no preregistered experiment to run. Specifically forbidden without a new
Research-Director-frozen design:

- any tuned descendant of either Stage-1 configuration;
- a third Stage-1 model family;
- a change to the feature set, the feature-validity rules, the window rule or the gap policy;
- a change to the coverage thresholds, the MESI, the alpha allocation or the advancement
  conditions;
- inverting or negating `PREVIOUS_24H_SIGN_PERSISTENCE`;
- admitting any external information family;
- any sealed or post-cutoff query.

Champion stays `NONE`. Real money stays `false`.

## Decisions the Research Director owns

1. **Substrate.** Whether the canonical hourly gap structure should be repaired, or the
   169-bar contiguity requirement relaxed, so that coverage becomes achievable. This is a
   substrate decision that must be preregistered on its own terms. It may not be framed as a
   rescue of `EXP-PRED-001` or `EXP-PRED-002`, whose results stand as observed.
2. **Direction.** Whether to open Stage 2 of `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`
   and admit a new information family, now that internal structure alone has been tested and
   rejected, or to close the predictive generation's Stage-1 line entirely.
3. **Disposition.** Whether `PREDICTIVE_STAGE1_INTERNAL_MODEL_FAMILY_V1` is recorded as
   `REJECTED` rather than merely closed, and whether either configuration is eligible for any
   future sealed evaluation (on the present evidence, neither is).

## If the Owner or Research Director asks for the next work package

Write it as a new `tasks/CURRENT_TASK.md` with a frozen design, exactly as
`PREDICTIVE-INTERNAL-STRUCTURE-V1` was frozen: hypothesis, primary metric, MESI, evaluation
design, parameter/search space, trial budget and advancement gate all declared before
execution, with a pre-execution admission artifact binding the preregistration and the
implementation hashes.

## Validation for any future package

Backend tests PASS; frontend validation PASS if touched; `check.py --no-data` PASS; ruff /
format / mypy PASS; deterministic result replay PASS with development data installed; exact
search-budget accounting; sealed queries 0; Champion `NONE`; real money `false`; clean tree;
commit and push to `main`; exact-head CI SUCCESS.
