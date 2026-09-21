# ADR-0029 — First Generation V2 family is deterministic UTC calendar context

Status: **ACCEPTED BEFORE EXECUTION** (2026-09-21)

Builds on [ADR-0028](ADR-0028-GENERATION-V2-SELECTIVE-LONG-REBASELINE.md) without changing
its target, scorer, threshold, advancement conditions or inference contract.

## Decision

The Research Director admits exactly one new family,
`PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FAMILY_V1`, as the first market-model family of
`PREDICTIVE_RESEARCH_GENERATION_V2`.

The V2 action threshold remains `p_up >= 0.60`; all ten advancement conditions remain
unchanged; `FULL_FOLD_UP_RATE` remains the primary enrichment control; and magnitude remains
`DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION`.

The family contains exactly two configurations, both executed unless an integrity/software
defect blocks the family:

- `V2_CALENDAR_LINEAR_V1` / `EXP-PRED-V2-001-CALENDAR-LINEAR`;
- `V2_CALENDAR_HGBR_V1` / `EXP-PRED-V2-002-CALENDAR-HGBR`.

Their models, calibration, features, folds, inference seed and search budget are frozen in
`research/protocols/PREDICTIVE-V2-DETERMINISTIC-CALENDAR-SEARCH-PLAN-V1.json` before any fit or
outer prediction.

## Rationale

Deterministic calendar state is new information not tested as a Generation V1 predictive
family. It requires no external acquisition, publication-lag assumption or as-of
reconstruction, and directly tests whether recurring UTC temporal regimes contain selective
LONG opportunities. It is cheap to test and therefore easy to over-search, so the feature set
and two-configuration family are closed in advance.

The representation is reconstructed by this project from elementary UTC calendar state. It is
not an implementation of, or evidence about, Ciclica Evoluta or Analisi Evoluta. No historical
cycle or cross-section result is imported as evidence.

## Preserved boundaries

Generation V1 remains closed as `CLOSED_NO_DIRECTIONAL_ADMISSION_NO_SEALED`. All ten V1 result
artifacts, the macro source block and its residual source finding are hash-bound by the
pre-result admission artifact and must remain byte-identical. No V1 probability, tail,
reliability bin or reconstructed action participates in family selection or fitting.

Cross-asset inversion remains forbidden, Stage-1 substrate debt and basis remain deferred, and
the macro source-redesign budget remains exhausted. No SHORT, magnitude estimator,
post-cutoff/sealed data, Champion, prospective observer or real money is authorized. Sealed
queries remain zero.

## Consequences

The family consumes exactly two new V2 configurations. A passing configuration is only
`ELIGIBLE_FOR_RESEARCH_DIRECTOR_SEALED_REVIEW`; it does not query sealed data in this work
package. If neither passes, the family disposition is `REJECTED_DEVELOPMENT_NO_SEALED`. There
is no automatic second V2 family: the next action is Research Director review.
