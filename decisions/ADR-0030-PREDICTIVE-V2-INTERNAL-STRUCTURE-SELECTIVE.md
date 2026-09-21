# ADR-0030 — Second Generation V2 family re-enters causal internal market structure

Status: **ACCEPTED BEFORE EXECUTION** (2026-09-22)

Builds on [ADR-0028](ADR-0028-GENERATION-V2-SELECTIVE-LONG-REBASELINE.md) and
[ADR-0029](ADR-0029-PREDICTIVE-V2-DETERMINISTIC-CALENDAR.md) without changing the target,
scorer, threshold, advancement conditions or inference contract.

## Research Director ruling on the first V2 family

`PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1` is accepted as a **negative** Generation V2 family
result. Its disposition remains `REJECTED_DEVELOPMENT_NO_SEALED` and both configurations
remain `NOT_ELIGIBLE_REJECTED_DEVELOPMENT`. Nothing in it may be tuned, rethresholded,
reweighted or reused as model evidence.

## Decision

The Research Director admits exactly one new family,
`PREDICTIVE_V2_INTERNAL_STRUCTURE_SELECTIVE_FAMILY_V1`, as the second market-model family of
`PREDICTIVE_RESEARCH_GENERATION_V2`.

The V2 action threshold remains `p_up >= 0.60`; all ten V2 advancement conditions remain
unchanged; `FULL_FOLD_UP_RATE` remains the primary enrichment control; and magnitude remains
`DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`.

The family contains exactly two configurations, both executed unless a genuine
integrity/software defect blocks execution:

- `V2_INTERNAL_LINEAR_V1` / `EXP-PRED-V2-003-INTERNAL-LINEAR`;
- `V2_INTERNAL_HGBR_V1` / `EXP-PRED-V2-004-INTERNAL-HGBR`.

Their models, calibration, features, folds, inference seed `20260922` and search budget are
frozen in
`research/protocols/PREDICTIVE-V2-INTERNAL-STRUCTURE-SELECTIVE-SEARCH-PLAN-V1.json` before any
fit or outer prediction.

## Rationale

Generation V1 asked of internal structure: *was the declared direction right on every hour?*
It failed. Generation V2 asks a substantively different prospective question: *under the
frozen selective scorer, is there a high-confidence subset of hours where a `LONG` beats the
ambient fold?* A family can fail the first question and still be the right place to ask the
second, because an always-declare scorer averages a possible selective edge away against the
hours the model never wanted to act on.

The family re-enters internal market structure **only** for that reason. No Generation V1
score, reliability-bin tail, fold-specific score distribution or threshold reconstruction
informed this design, and none may inform its execution. The deciding fact is the shape of
the question, not the shape of a stored V1 probability tail.

## Preserved boundaries

The eighteen causal quantities, their order, their two named degenerate values and the
169-bar availability rule are inherited **unchanged** from
`PREDICTIVE_INTERNAL_CAUSAL_FEATURES_V1`. The V2 identity
`PREDICTIVE_V2_INTERNAL_CAUSAL_FEATURES_V1` names that definition and rewrites none of it;
reuse is proved on fixed fixtures rather than asserted.

The Stage-1 substrate debt remains **deferred and unrepaired**. A decision instant with an
incomplete 169-bar lookback stays feature-unavailable, is counted, and is excluded from every
rate. No fold is removed because its feature availability is low, and feature availability
never redefines the primary control.

Generation V1 remains closed as `CLOSED_NO_DIRECTIONAL_ADMISSION_NO_SEALED`; its internal
family remains `REJECTED_DEVELOPMENT_NO_SEALED`. All ten V1 result artifacts, both first-family
V2 result artifacts and the V2 calendar family report are hash-bound by the pre-result
admission and must remain byte-identical. No V1 fitted model, probability or prediction
artifact is loaded by the V2 runner.

Cross-asset inversion remains forbidden, basis remains deferred, and the macro source-redesign
budget remains exhausted. No SHORT, magnitude estimator, post-cutoff/sealed data, Champion,
prospective observer or real money is authorized. Sealed queries remain zero.

## Consequences

The family consumes exactly two new V2 configurations with zero result-dependent forks. A
passing configuration is only `ELIGIBLE_FOR_RESEARCH_DIRECTOR_SEALED_REVIEW`; it does not query
sealed data in this work package. If neither passes, the family disposition is
`REJECTED_DEVELOPMENT_NO_SEALED`. There is no automatic third V2 family: the next action is
Research Director review.
