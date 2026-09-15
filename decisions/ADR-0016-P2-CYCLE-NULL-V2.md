# ADR-0016 — P2 raw-return long-block Null V2

Status: ACCEPTED BEFORE V2 BLOCK-SUPPORT OR FIDELITY MEASUREMENT. Date: 2026-09-15.

## Context

Null V1 failed 28 immutable training-only fidelity checks by systematically
underrepresenting long-horizon absolute-return and volatility dependence inside the
primary 2–90 day band. The actual `BTC_TIME_CYCLE_STRUCTURE_V1` result remains
unobserved, so this is a methodological redesign rather than a result-driven change to
the structural hypothesis.

## Decision

Record `P2_NULL_V1_STATUS = FAILED_FIDELITY_REJECTED_FOR_INFERENCE` without altering any
V1 artifact. For future P2 calibration, use a stationary bootstrap directly on
training-only raw contiguous 4h log returns with expected block length exactly 1,080.
Use no AR or fitted volatility model, never cross or interpolate canonical gaps, retain
one joint nested-prefix chronology per replicate, and keep the V1 fidelity statistics
and thresholds immutable.

Measure actual donor support first. Every fold must retain at least 0.50 same-block
survival at lag 540 under the frozen geometric restart and forced-gap semantics. A
failure stops fidelity, compute and detectability without parameter substitution.

This redesign is one adaptive methodological decision and one result-dependent fork.
Accounting increments exactly once, from 14 to 15 adaptive decisions and from 11 to 12
result-dependent forks. Completed experiments remain 26; observed material economic
hypotheses remain 12; no P2 structural market result is consumed.

## Consequences

The new null is deliberately conservative: long observed training blocks can retain
regimes, heavy tails, nonlinear dependence and local pseudo-periodicity. The inferential
question becomes whether selected timing is more repeatable across chronology than the
dependent/local structure already present in those blocks. No local cycles are removed.

The P2 representation, band, GLS estimator, folds, diagnostics, injection definition,
budgets and power gate are unchanged. No sealed access, asset expansion, cycle trading,
or real-capital action is authorized.

