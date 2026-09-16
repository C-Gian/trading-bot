# Cross-section sparse closure + ALIGNED gate-intensity power gate V1

Status: COMPLETED_NEGATIVE_PREREQUISITE_PENDING_RESEARCH_DIRECTOR_REVIEW

Starting HEAD: `ac1c5ff57af9d233cb9648ed5de92c36be3de90c` on local `main`.

No true zero-alignment or zero-shift effect was computed for either hypothesis. No sealed
data was queried, no post-cutoff data was used, the BTCUSDT product is unchanged and real
money remains false.

## Sparse cross-section closure

Research Director disposition for `ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1`:
**`POWER_BLOCKED_INFERENCE_CALIBRATION_FAILED_NOT_EXECUTED`**
(`reports/reviews/CROSS-SECTION-SPARSE-POWER-BLOCK-REVIEW.md`, ADR-0020).

It is not `REJECT`, not `INCONCLUSIVE` market evidence, and not evidence that
`beta <= 0`. Controlling facts: MESI 24.0 bps/event, MDE 44.872236 bps/event, power at
MESI 0.211674 against a 0.80 target, and an analytic inference whose placebo rejected at
3.55% against a nominal 0.385%. No same-hypothesis inference rescue is authorized and all
feasibility artifacts are preserved.

## Event reconciliation

| quantity | support artifact | power panel | difference |
| --- | ---: | ---: | ---: |
| raw ALIGNED signals | 3,380 | 3,378 | 2 |
| asset clusters with events | 259 | 258 | 1 |

The difference is explained by exactly one typed deterministic rule:
`epoch_decision_rows < 504`, the participation requirement of the retired position-shift
placebo. It excluded 35 instrument epochs; exactly one of them, `RIFUSDT#2021-01-07`
(230 rows), carried signals, and it carried exactly the two missing events, both
enumerated with their decision hours. The rule is not discretionary and not
performance-dependent.

A second typed item accounts for the intensity field being 169 rows larger than the
outcome panel: the outcome panel additionally requires a valid 24h forward return, it is a
strict subset, and it loses **no** signal (3,380 on both sides).

**The reconciliation nevertheless fails closed.** The rule's input is the epoch's total
decision-row count over the whole development window, which is not knowable at decision
time, and for 6 of the 35 excluded epochs it is co-determined by in-window delisting.
`EVENT_RECONCILIATION_STATUS = FAIL_CLOSED_NON_POINT_IN_TIME_PARTICIPATION_RULE`. The rule
never touched the frozen universe, the frozen signal counts or any market result, and it
is retired together with the placebo that required it.

## Frozen gate-intensity descendant

`ALIGNED_GATE_INTENSITY_COMMON_EFFECT_V1` is the final authorized ALIGNED development
descendant and remains `DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED`.

    GATE_INTENSITY = int(direction_pass) + int(breakout_pass) + int(participation_pass)

Unweighted, integer, values `0..3`, no new threshold, no parameter fitting, no
optimization, ALIGNED itself unchanged. The gate decomposition is a pure refactor of the
frozen evaluator and is verified row-for-row against the frozen `FeatureSource` engine.

Verified mechanically over the whole panel (2,556,535 rows, 390 instrument epochs):

| intensity | rows |
| --- | ---: |
| 0 | 2,210,069 |
| 1 | 293,370 |
| 2 | 49,716 |
| 3 | 3,380 |

`ALIGNED_SIGNAL == 1` exactly when `GATE_INTENSITY == 3`: 3,380 on both sides.

One primary coefficient `beta_gate` in the same two-way fixed-effects panel with the
unchanged 24h forward outcome. `GATE_INTENSITY_MESI_BPS_PER_GATE = 8.0`, derived as
`24 / 3`. Prospective family size 13, alpha `0.05 / 13` one-sided, target power `0.80`.

## Calendar-synchronous randomization

The retired per-asset position-shift placebo is not reused, and its whole-sample
participation rule is not reintroduced — every instrument epoch participates.

`CALENDAR_SYNCHRONOUS_WHOLE_WEEK_YEAR_SHIFT_V1` moves the entire cross-sectional score
field together: one common signed whole-UTC-week displacement per development year shared
by every asset, magnitude 2..13 weeks, never zero, no circular wrap, eligibility required
at both source and destination. 1,024 unique six-year vectors were generated from the
fixed seed by counter-based SHA-256 over the 24 legal displacements; family SHA-256
`7e135af46a20c30d8c1f19e39d56b663254ab293b007c84a694437e82e8cf12d`. Construction depends
only on the seed and calendar geometry.

## What was deliberately not run

`EVENT_RECONCILIATION_STATUS` is a frozen prerequisite of the power gate. Because it
failed closed, the checkpoint stopped at its own safe stop: the randomization support gate
and the prospective power stages were **not** run. `RANDOMIZATION_SUPPORT_STATUS` and
`RANDOMIZATION_INFERENCE_STATUS` are `NOT_RUN_BLOCKED`, and no accepted-vector count, no
shifted beta, no empirical null and no power number exists for this hypothesis.

Measuring power after a prerequisite had already failed would have produced exactly the
result-dependent framing the governance forbids, so it was not measured.

## Gate

| prerequisite | status |
| --- | --- |
| DATA_SOURCE_STATUS | PASS |
| UNIVERSE_FEASIBILITY_STATUS | PASS |
| SURVIVORSHIP_STATUS | PASS |
| EVENT_RECONCILIATION_STATUS | FAIL_CLOSED_NON_POINT_IN_TIME_PARTICIPATION_RULE |
| RANDOMIZATION_SUPPORT_STATUS | NOT_RUN_BLOCKED |
| RANDOMIZATION_INFERENCE_STATUS | NOT_RUN_BLOCKED |

`GATE_INTENSITY_POWER_GATE_STATUS = REDESIGN_REQUIRED`, and therefore
`ALIGNED_DEVELOPMENT_FAMILY_STATUS = PARKED_DEVELOPMENT_SEARCH_EXHAUSTED`.

Nothing was rescued inside the checkpoint: the score was not changed, gates were not
weighted, 2-of-3 and individual gates were not tested, no interaction was added, the
horizon and universe were untouched, MESI and power were not lowered, and no other
placebo was tried.

The park is an inherited reconciliation defect in a retired calibration panel, not a
demonstrated power failure of the gate-intensity design. That design is frozen and
unmeasured, so a Research Director who reopens it starts from a clean preregistration.

## Accounting

As a result-dependent descendant this consumed one adaptive decision and one
result-dependent fork: adaptive decisions 15 → 16, result-dependent forks 12 → 13.
Completed experiments remain 26, known observed material economic hypotheses remain 12,
sealed queries remain 0, Champion remains `NONE`, genuine completed paper trades remain 0,
and real money remains false. Product remains `BTCUSDT_SPOT_V1` with no multi-asset
trading, Analyze Market surface, allocation logic or order path.

Next action: RESEARCH DIRECTOR REVIEW.
