# CURRENT TASK — RESEARCH-DIRECTOR-REVIEW-GENERATION-V2-REBASELINE

Status: AWAITING_RESEARCH_DIRECTOR_REVIEW

Executor HEAD under review: the commit that closed
`PREDICTIVE-GENERATION-V2-SELECTIVE-LONG-REBASELINE-V1` on `main`.

This is a review checkpoint, not an implementation work package. No coding agent may fit a
model, declare a Generation V2 hypothesis, open a family, fetch a source, change a frozen
threshold or produce a market prediction from this file. The first Generation V2 research work
package is written only after the Research Director has ruled.

## 1. What is on the table

`PREDICTIVE_RESEARCH_GENERATION_V1` is closed with disposition
`CLOSED_NO_DIRECTIONAL_ADMISSION_NO_SEALED`: five executed information families, ten consumed
configurations, none advanced, none sealed-eligible. The macro-vintage checkpoint remains a
source block and is not counted among the ten.

`PREDICTIVE_RESEARCH_GENERATION_V2` is open with zero candidates. This checkpoint fitted no
model, produced no market prediction and created no experiment record. Sealed queries 0,
Champion `NONE`, real money `false`.

Read, in this order:

1. `reports/checkpoints/PREDICTIVE-GENERATION-V2-SELECTIVE-LONG-REBASELINE-V1.md`;
2. `decisions/ADR-0028-GENERATION-V2-SELECTIVE-LONG-REBASELINE.md`;
3. `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V2.md` (Amendment B1);
4. `docs/contracts/ALFRED_OBSERVATION_DATE_GUARD_V1.md`;
5. `backend/app/predictive/selective_long.py` and
   `backend/tests/test_predictive_selective_long_scorer.py`;
6. `state/current_state.json`, keys `predictive_generation_v1_closure` and
   `predictive_generation_v2_objective`.

## 2. Decisions the Research Director owes this checkpoint

### 2.1 Confirm or amend the frozen V2 semantics

The scorer is frozen and synthetically proven, but no candidate has met it. Confirm, or amend
**before** the first candidate exists, since none of it may be weakened afterwards:

- the `p_up >= 0.60` action threshold, and that it is never tuned on development results;
- `FULL_FOLD_UP_RATE` as the primary control, including that it spans every directionally
  scorable eligible timestamp in a fold rather than only the candidate's feature-valid rows;
- the coverage and count floors (0.02 / 0.005 pooled and per-fold action coverage; 500 / 30
  pooled and per-fold actionable LONGs);
- the enrichment floor of +0.05 and the two calibration conditions;
- the discarded-replicate rule and the 1% `UNSTABLE_RESAMPLE_SUPPORT` cut-off.

### 2.2 Choose the first Generation V2 information family

Generation V2 inherits V1's search memory in full: every family disposition, all ten executed
results, every source block, the Stage-1 substrate debt, basis deferred, the exhausted macro
source-redesign budget and the ban on cross-asset inversion. No rejected V1 result becomes
evidence merely because the scorer changed.

Rule on which family opens V2, on a new hypothesis ID with a new search budget, and on whether
any V1 causal source infrastructure may be reused for it. A family that was rejected under V1
may be re-entered under V2 only as a new preregistered hypothesis with its own budget, never as
a rescue of the V1 result.

### 2.3 Declare the family's inference seed and multiplicity

The contract requires a fixed integer seed declared per family **before** execution, and
Bonferroni correction over the declared family size at familywise alpha 0.05. Both must appear
in the family's search plan before any fit.

### 2.4 Magnitude

`MAGNITUDE_STATUS = DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`. Confirm it stays deferred, and
that no user-facing "strength 0–100" is shown until a separate preregistered magnitude head
exists.

## 3. Permanent boundaries during review

Forbidden without a new Owner- or Director-authorized work package:

- fitting any model or producing any market prediction;
- weakening, re-cutting or re-choosing any frozen V2 threshold, including the 0.60 action
  threshold;
- letting the `FULL_FOLD_UP_RATE` control reach fitting, calibration, thresholding or fold
  selection;
- re-scoring, rescuing or reinterpreting any Generation V1 result under V2 semantics;
- editing, re-running or reclassifying any completed V1 result, source audit, admission,
  checkpoint report or residual record;
- a third macro source semantics, or retrofitting the ALFRED observation-date guard onto a
  finished experiment;
- `SHORT`, leverage, a magnitude head, sealed or post-cutoff data, a Champion, a prospective
  observer, credentials or real money.

## 4. Output of this checkpoint

A Research Director verdict recorded as a new immutable record, plus the first Generation V2
research work package written into `tasks/CURRENT_TASK.md`. No repository state changes until
then.
