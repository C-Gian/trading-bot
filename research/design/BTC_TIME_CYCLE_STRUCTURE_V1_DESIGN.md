# BTC Time Cycle Structure V1 — frozen structural design

Status: DESIGN ONLY. No preregistration, implementation, market-result execution, or
economic strategy is authorized.

## Primary structural hypothesis

Exactly one primary is allocated:

`BTC_TIME_CYCLE_STRUCTURE_V1`

> Does BTCUSDT exhibit repeatable / quasi-persistent cyclic timing structure beyond what
> is expected from an appropriately dependence-preserving null?

This tests the **time layer only** on the canonical BTCUSDT development dataset. It does
not test the whole Ciclica Evoluta / Analisi Evoluta methodology. A future failure may
reject this frozen timing representation, but must never be reported as “Ciclica Evoluta
disproved.”

## Representation rationale before method selection

### Price, log-price, or log-return

Raw price is rejected for the primary because its changing scale and stochastic trend
can create low-frequency spectral concentration unrelated to repeatable timing.
Log-price makes proportional moves comparable but remains non-stationary and would need
a trend estimate whose endpoint behavior can manufacture cycles. The primary therefore
uses contiguous **4-hour close-to-close log returns**. Differencing log-price removes
the level trend without a fitted two-sided smoother; a sinusoidal log-price component
still appears in returns with a deterministic phase shift and period.

Only a 4-hour return whose two endpoint 4-hour bars are complete and consecutive is
eligible. Gaps are omitted, never interpolated. Exact timestamps are retained.

### Detrending

No HP filter, centered moving average, polynomial fitted across validation, or other
two-sided price detrending is allowed. Within each training or validation segment,
returns receive only an intercept removal performed inside that segment. Scaling used
by the synthetic effect definition is estimated on training data only. This prevents
future observations and trend-window choices from selecting the result.

### Frequency / period band

The frozen primary band is **2 through 90 UTC days**, inclusive (12 through 540 four-hour
intervals). Periods shorter than two days are excluded to avoid making this foundation
test a microstructure or intraday-calendar search. Periods longer than 90 days are
excluded because a one-year outer fold contains fewer than about four repetitions and
cannot credibly establish repeatability. The bounds are fixed before cycle-result
inspection and are not moved after observation.

The deterministic frequency grid uses Fourier spacing `1 / T_train` with oversampling
factor 4, clipped to the frozen band. Grid construction is repeated from each training
span's timestamps; it is not refined around a promising result.

### Spectral estimator

A floating-mean generalized Lomb–Scargle estimator is selected because eligible 4-hour
returns remain timestamped but can be irregular around canonical gaps. It avoids
inventing returns through interpolation. At each frequency it fits only an intercept,
sine, and cosine. No harmonics, taper menu, wavelet family, or post-result estimator
switch is allowed.

### Colored/dependent-noise null

White-noise and shuffled-return nulls are rejected because BTC returns can be serially
dependent, heavy-tailed, and volatility-clustered. The frozen null is an **AR-sieve plus
residual stationary-block bootstrap**:

1. Within each outer fold's training segment, choose AR order by BIC from the fixed set
   0..42 four-hour lags.
2. Fit the selected AR model using training data only.
3. Resample centered AR residuals in stationary blocks with expected length 42 four-hour
   observations (seven days), preserving local residual/volatility dependence.
4. Simulate training and validation chronology from the fitted colored-noise model,
   apply the original eligible-timestamp masks, and rerun the complete frequency
   selection/evaluation pipeline.

The AR-order search is part of null calibration, not a cycle-frequency rescue. The same
fixed candidate orders and block rule apply to every replicate.

### Chronological selection/evaluation separation

Use the six fixed annual outer validation folds 2019–2024 from
`DEVELOPMENT_WALK_FORWARD_V1`. For each fold, training is expanding and strictly earlier
than validation. The last 90 days before validation are embargoed from frequency
selection, matching the longest tested period. No validation frequency, phase, amplitude,
or score may influence training selection or a later fold's frozen rules.

Within training, select exactly one period: the grid frequency with maximum generalized
Lomb–Scargle power, with the longer period winning an exact tie. In validation, evaluate
generalized Lomb–Scargle power only at that selected frequency. Validation may estimate
the sine/cosine coefficients at the already selected frequency; it may not search a new
frequency. The primary statistic is the eligible-observation-weighted mean of the six
validation powers. Its one-sided p-value is its rank against the null replicates produced
by the complete repeated pipeline.

## Multiplicity and primary decision

- Structural primary hypotheses: **1**.
- Family alpha: **0.05**, one-sided.
- Frequency selection is multiplicity, not a collection of hypotheses. The max-frequency
  selection is rerun inside every null and synthetic replicate, so the primary null
  calibrates the whole selection procedure.
- Diagnostics do not alter the primary alpha, threshold, period, or classification.
- A future primary classification is `SUPPORTED_FROZEN_TIME_REPRESENTATION` only if its
  corrected p-value is at most 0.05 and the pre-execution detectability gate passed.
  Otherwise it is `NOT_SUPPORTED_FROZEN_TIME_REPRESENTATION`. Neither classification is
  an economic claim.

## Frozen diagnostic budget

Maximum diagnostics: **2**, both non-rescuing.

1. `QUASI_PERSISTENCE_BARTELS_V1`: one frozen Bartels-style phase/quasi-persistence
   diagnostic at the training-selected period only. It cannot search other frequencies,
   change the primary, or authorize a successor.
2. `CROSS_FOLD_PERIOD_STABILITY_V1`: report the dispersion of the six training-selected
   periods and the count within a predeclared ±10% relative-period tolerance of the
   preceding fold. It is descriptive and cannot rescue the primary.

Any diagnostic-inspired successor is a new structural or economic hypothesis with a
new prospective record and search budget.

## Prospective detectability design

Detectability is assessed before the actual primary statistic is computed.

- Null replicates: 4,999, generated by the frozen dependent-noise mechanism above.
- Synthetic replicates: 2,000 per period/effect-scale cell.
- Deterministic random seed: 20260915, with child streams derived from the replicate,
  fold, period, amplitude, and phase identifiers.
- Injected component: add `A sin(2πt/P + φ)` to simulated **log-price**, then difference
  it to produce the synthetic 4-hour log returns given to the unchanged pipeline.
- Period handling: `P` is frozen to 3, 7, 14, 30, and 60 UTC days for power curves. This
  calibration grid samples the interior of the primary band and is not a result search.
- Phase handling: phase is balanced over 16 fixed equally spaced values on `[0, 2π)`;
  replicate assignment is deterministic. Phase is never selected for advantage.
- Structural effect scale: `SNR_cycle = RMS(injected return component) /
  training_RMS(null return innovation)`. Curves use SNR values 0, 0.10, 0.25, 0.50,
  0.75, and 1.00. This is a structural signal-to-noise scale, **not an economic MESI**.
- Target power: **0.80** at corrected alpha 0.05.
- Multiple-frequency correction: every replicate reconstructs its training grid, selects
  its maximum-power training frequency, freezes it, and evaluates only that frequency
  in the chronological outer validation. The null critical value therefore includes the
  entire selection procedure.
- Prospective output: detection probability and binomial uncertainty by injected period
  and SNR, plus the minimum SNR reaching 0.80 where estimable. No actual BTC primary
  statistic, selected period, phase, or cycle conclusion may be emitted by power prep.

The pre-result gate passes only if power is at least 0.80 at `SNR_cycle = 0.50` for every
frozen calibration period. This is a conservative structural resolution benchmark, not
an Owner economic threshold. If any period fails, status is `REDESIGN_REQUIRED` and the
actual BTC cycle result remains unavailable. The threshold and effect grid may not be
changed after the power curves are seen merely to obtain passage.

## Explicit exclusions

This checkpoint implements none of: swing, volume, inverse, vincolo, raccordo, target,
cycle-based trading, final-algorithm weighting, or ALIGNED tuning. It executes zero
material economic hypotheses. A later rule that turns any structural cycle finding into
a trade is a new `MATERIAL_ECONOMIC_HYPOTHESIS` requiring its own preregistration, Owner
MESI translation, realistic costs/execution, multiplicity accounting, and power gate.

Source attribution follows
`docs/canonical/CYCLE_RESEARCH_SOURCE_BOUNDARY_V1.md`. Every operational choice in this
design is `RECONSTRUCTED`, not an official Marini implementation.
