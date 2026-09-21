# CURRENT TASK — RESEARCH-DIRECTOR-REVIEW-STAGE3-MACRO-RELEASE-STATE-CLOSURE

Status: AWAITING_RESEARCH_DIRECTOR_REVIEW

Executor HEAD under review: the commit that closed
`PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1` on `main`.

This is a review checkpoint, not an implementation work package. No coding agent may execute a
new experiment, fit a model, fetch a source, change a gate or open a new family from this file.
The next executor work package is written only after the Research Director has ruled.

## 1. What is on the table

`PREDICTIVE_STAGE3_MACRO_RELEASE_STATE_FAMILY_V1` executed both preregistered configurations
and both failed the frozen seven-condition gate:

- `EXP-PRED-009-MACRO-RELEASE-STATE-LINEAR` — `NO_ADVANCE_MACRO_RELEASE_STATE_LINEAR_V1`;
- `EXP-PRED-010-MACRO-RELEASE-STATE-HGBR` — `NO_ADVANCE_MACRO_RELEASE_STATE_HGBR_V1`;
- family `REJECTED_DEVELOPMENT_NO_SEALED`, sealed eligibility
  `NOT_ELIGIBLE_REJECTED_DEVELOPMENT` for both.

Five information families have now been tested and rejected on the frozen BTCUSDT 24h target:
internal market structure, settled funding, open interest, cross-asset breadth and strict
point-in-time macro release state. Ten predictive configurations are consumed. Champion is
`NONE`, sealed queries are 0, real money is `false`.

Read, in this order:

1. `reports/checkpoints/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1.md`;
2. `reports/research/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1.md`;
3. `reports/validation/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1-RESIDUAL-SOURCE-FINDING.json`;
4. `reports/validation/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1-SOURCE-AUDIT.json`;
5. `docs/contracts/PREDICTIVE_MACRO_RELEASE_STATE_V1.md`;
6. `state/current_state.json`, key `predictive_stage3_macro_release_state`.

## 2. Decisions the Research Director owes this checkpoint

### 2.1 The residual source finding

`MACRO_RELEASE_STATE_FUTURE_DATED_OBSERVATION_V1` is recorded, not repaired. Twenty `VIXCLS`
rows of the admitted ALFRED substrate carry an `observation_date` later than their own
`vintage_start`, so the frozen V2 rule — greatest observation date in the as-of-`T` snapshot —
admits a level stamped up to two days ahead at 624 of 43,642 evaluation instants (1.43%) and
480 of 55,516 training instants (0.87%).

The frozen contract text is silent on the case, so the executed implementation is compliant
with what was frozen. Decide:

- whether the negative result stands as recorded (a lookahead can only flatter a candidate, and
  both candidates were rejected by wide margins);
- whether any future contract reusing these semantics must add an explicit
  `observation_date <= decision_date` condition, and under what version identity;
- whether the ALFRED substrate itself needs a separate, source-only integrity amendment.

The finding may not be used to reinterpret the negative result upward, and no configuration may
be re-executed against a known result.

### 2.2 The macro family

The macro source design is closed for `PREDICTIVE_RESEARCH_GENERATION_V1`: one source-semantics
remediation was authorized and consumed, and a third redesign is forbidden. Confirm the family
is parked, or record a different disposition explicitly.

### 2.3 The generation

Five orthogonal information families have produced no directional admission on the frozen 24h
target, four of them at essentially full coverage, so substrate quality explains none of it.
The Director must rule on what that means for
`PREDICTIVE_RESEARCH_GENERATION_V1`: continue with a further Stage-3 family, revisit the target
or horizon under a new generation, reconsider the deferred magnitude head, or stop.

The `2020` fold again dominates the pooled damage for both configurations, as it did for
cross-asset breadth, and again carries the most lopsided matched base rate. It was admitted
before any result existed and may not be removed retrospectively; whether it should shape a
future design is a Director decision.

## 3. Permanent boundaries during review

Forbidden without a new Owner- or Director-authorized work package:

- editing, reclassifying or re-executing any completed predictive result;
- a third macro source semantics in this generation;
- lowering or re-cutting any completed gate, fold set or coverage threshold;
- feature pruning, threshold search or inversion of any rejected family;
- a magnitude head, basis, or Stage-1 substrate repair;
- current-revised macro data, interpolation or future vintages;
- sealed or post-cutoff BTC access;
- a Champion, a prospective observer, credentials or real money.

## 4. Output of this checkpoint

A Research Director verdict recorded as a new immutable record, plus the next executor work
package written into `tasks/CURRENT_TASK.md`. No repository state changes until then.
