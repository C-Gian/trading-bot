# ALFRED observation-date guard V1

Status: frozen, prospective. Binding on every ALFRED use in
`PREDICTIVE_RESEARCH_GENERATION_V2` and later. See
[ADR-0028](../../decisions/ADR-0028-GENERATION-V2-SELECTIVE-LONG-REBASELINE.md).

This guard **does not** modify
[`POINT_IN_TIME_EXOGENOUS_DATA_V1`](POINT_IN_TIME_EXOGENOUS_DATA_V1.md),
[`PREDICTIVE_MACRO_VINTAGE_CONTEXT_V1`](PREDICTIVE_MACRO_VINTAGE_CONTEXT_V1.md) or
[`PREDICTIVE_MACRO_RELEASE_STATE_V1`](PREDICTIVE_MACRO_RELEASE_STATE_V1.md), and it does not
reopen, re-score or reinterpret any historical result those contracts governed. It applies
prospectively only.

## Why it exists

`PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1` recorded the residual source finding
`MACRO_RELEASE_STATE_FUTURE_DATED_OBSERVATION_V1`. Twenty rows of the admitted ALFRED
substrate — all `VIXCLS`, all on US market holidays, lead up to three days — carry an
`observation_date` later than their own `vintage_start`. The raw vintage retrieved for
2018-10-05 already contains an observation dated 2018-10-08.

The Generation V1 current-anchor rule took the latest observation *on or before* the decision
date, so it could never use such a row as the current level. The corrected V2 release-state
rule takes the greatest observation date present in the as-of-`T` snapshot and does not
additionally require that date to be at or before `T`. Over the included folds that exposed a
future-dated `VIXCLS` level at 624 of 43,642 evaluation instants (1.43%) and 480 of 55,516
training instants (0.87%).

The Research Director ruled that the committed negative macro result stands: a lookahead can
only flatter a candidate, and both macro configurations were rejected by wide margins, so the
defect cannot have manufactured the observed negative result. The gap is in the frozen
contract wording, not in the implementation of it, and it is closed here for future use
instead of being retrofitted onto a finished experiment.

## The guard

At decision timestamp `T`, a substrate row may enter a feature vector only when **both** hold:

1. `availability_time <= T`; and
2. `observation_date <= UTC_date(T)`.

Condition 1 is the existing causal-availability rule and is unchanged. Condition 2 is new: a
value describing a calendar day that has not yet ended at `T` may not be read, whatever the
source's own vintage labelling claims.

Both conditions apply to every anchor of a feature vector — current level, historical anchors
and exact-month anchors alike — and to every series, not only the ones observed to have
offending rows.

## What remains forbidden

- Current-revised substitution.
- Interpolation, forward-filling a missing observation onto a new observation date, and
  nearest-future substitution.
- Reading a later revision before its own `availability_time` is reached. A later vintage
  revision of an already-admissible observation remains usable, but only from its own
  availability boundary onward — condition 2 constrains the observation date, never the
  revision's visibility rule.
- Post-cutoff vintages and sealed access.

## Accounting

Any future ALFRED source audit bound by this guard must report, before any target-bearing fit:

- the count of substrate rows with `observation_date > vintage_start`, by series;
- the count of decision instants at which condition 2 excluded a row that condition 1 alone
  would have admitted, for evaluation and training separately;
- the resulting feature coverage, so a coverage change caused by this guard is visible rather
  than absorbed.

A feature vector blocked by condition 2 is unavailable, typed and counted, exactly like any
other missing anchor. It is never imputed.

## Scope

Prospective. Historical macro artifacts, results, audits and checkpoint reports remain
byte-identical and keep their recorded dispositions. This guard creates no new macro source
semantics version and does not revive the exhausted macro source-redesign budget of
`PREDICTIVE_RESEARCH_GENERATION_V1`.
