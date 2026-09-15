# ADR-0015 — the frozen P2 cycle null fails its predeclared fidelity gate

Status: ACCEPTED. Date: 2026-09-15. Checkpoint: `P2-CYCLE-FOUNDATION-POWER-GATE-PREP`.

## Context

`BTC_TIME_CYCLE_STRUCTURE_V1` is frozen in
`research/design/BTC_TIME_CYCLE_STRUCTURE_V1_DESIGN.md`. Its dependent-noise null is a
training-only AR sieve, order chosen by BIC over the fixed set 0..42, driving a
stationary residual block bootstrap with expected block length 42 four-hour
observations, that is seven days.

The primary statistic is the eligible-observation-weighted mean of six outer validation
generalized Lomb-Scargle powers, each scored at a frequency chosen by training alone
inside the frozen 2-90 day band. Its p-value is the rank of that statistic against
replicates of the complete procedure, so the null's dependence structure sets the
critical value. If the null is less dependent than BTCUSDT actually is at periods
inside the band, the critical value is too low and the test is anti-conservative.

The checkpoint therefore required the null to be shown adequate *before* the actual
cycle result could be exposed, with the tolerances fixed first.

## Decision

Two decisions are recorded.

**1. `NULL_FIDELITY_V1` thresholds were preregistered, then measured.**

`reports/power/P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json` was written and committed
in `f33d9e6`, before any fidelity value existed. It fixes 21 statistics per fold across
five families — marginal dispersion and tails, return autocorrelation over lags 1-6,
absolute-return autocorrelation at 7, 15, 30, 60 and 90 days, dispersion of 1-, 7- and
30-day log realized volatility, and variance ratios at 2, 7, 30 and 90 days — together
with a materiality rule for each. The block length stayed frozen at 42 throughout and
was not tuned after the discrepancy was seen.

**2. The frozen null materially fails, so `NULL_FIDELITY_STATUS = REDESIGN_REQUIRED`
and the actual cycle result stays unobserved.**

28 of 126 preregistered checks fail, and the failures are systematic rather than
scattered. In every one of the six folds the null loses almost all of the observed
volatility dependence at horizons longer than its own seven-day block. Taking DEV-2024's
training window as the representative case, the null median retains this share of the
observed absolute-return autocorrelation:

| lag | horizon | observed | null median | retained |
| --- | --- | --- | --- | --- |
| 42 | 7 days | 0.1498 | 0.0415 | 28% |
| 90 | 15 days | 0.1288 | 0.0185 | 14% |
| 180 | 30 days | 0.1144 | 0.0084 | 7% |
| 360 | 60 days | 0.0767 | 0.0057 | 7% |
| 540 | 90 days | 0.0511 | 0.0068 | 13% |

The 90-day lag passes only because the observed value is already small enough for the
predeclared absolute-gap escape; it is not evidence that the null holds up there. Four
further failures are short-memory return autocorrelation at lags 1 and 2 in DEV-2019,
DEV-2020 and DEV-2022, where a BIC-selected AR(7) does not reproduce the observed sample
autocorrelation within the predeclared 0.05 tolerance.

The simulator itself was checked against the fitted model and is faithful: an
independent long simulation of the fitted AR(7) reproduces the same autocorrelation as
the block-bootstrap path, so the gap is a property of the frozen null, not of its
implementation.

This is the failure mode the gate was written to catch. Every lag from 7 days upward
lies inside the frozen 2-90 day band, so the null becomes artificially low-dependence at
exactly the frequencies the primary searches. A block bootstrap cannot carry dependence
much beyond its own block length, and BTCUSDT volatility is dependent far beyond seven
days.

## Consequences

- `P2_POWER_GATE_STATUS = REDESIGN_REQUIRED`. The frozen synthetic detectability curves
  were not computed, because the checkpoint forbids spending them on a null that has
  already failed.
- No actual BTCUSDT training-selected period, outer validation power, pooled statistic,
  structural p-value or market classification exists. `P2` remains
  `DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED`.
- The other two prerequisite gates passed and their work is reusable.
  `JOINT_REPLICATION_STATUS = PASS`: one replicate is one realization of the whole
  chronology, so the six nested training prefixes are literally the same simulated slots
  and each fold's validation slots reappear in later folds' training. That construction
  is measurably wider than the forbidden independent concatenation — pooled SD ratio
  1.070, adjacent-fold frequency agreement 0.660 against 0.393.
  `COMPUTATIONAL_STATUS = PASS`: the exact frozen budget of 4,999 null replicates and
  2,000 synthetic replicates per period/SNR cell projects to about 11 minutes and 437
  MiB, with no replicate, period, phase or grid reduction and no approximation.
- No remedy is attempted inside this checkpoint. The band, representation, estimator,
  block length, SNR gate and null are unchanged, and the executor did not search for a
  block length that would pass.
- The Research Director owns the next decision: a new null design and version for
  `BTC_TIME_CYCLE_STRUCTURE_V1`, or an explicit acceptance that the frozen null's
  limitation is tolerable and why.

## Alternatives not taken

- Lengthening the bootstrap block until the fidelity checks pass. Forbidden: it would
  choose a null parameter from an observed discrepancy, and the checkpoint freezes the
  42-observation block for this test.
- Loosening the tolerances after seeing them fail. Forbidden for the same reason; the
  committed preregistration hash is bound into the fidelity artifact.
- Running the detectability curves anyway and reporting power against a null already
  known to be inadequate. That would spend the frozen budget on a critical value that
  cannot support the primary inference.
