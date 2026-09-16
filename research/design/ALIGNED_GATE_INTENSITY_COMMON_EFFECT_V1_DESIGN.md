# ALIGNED_GATE_INTENSITY_COMMON_EFFECT_V1 — design and randomization protocol

Status: FROZEN DESIGN, NOT PREREGISTERED, NOT EXECUTED.

This is the **final authorized ALIGNED development descendant**. It is a new future
material hypothesis derived adaptively from the sparse-event power failure of
`ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1`. It does not change
`ALIGNED_PARTICIPATION_CONTINUATION_V1`, does not change the BTCUSDT spot V1 product, and
authorizes no execution.

If its power/inference gate fails, further historical ALIGNED descendant research becomes
`PARKED_DEVELOPMENT_SEARCH_EXHAUSTED` unless a Research Director explicitly reopens it.

## 1 — Why a descendant exists at all

The sparse design tested a binary indicator that fires only when all three ALIGNED gates
pass simultaneously. Across a 2.55M-row eligible panel that condition fired 3,380 times —
a 0.13% event rate — and the resulting design could resolve only ~44.9 bps/event against a
24.0 bps/event threshold.

The gate-intensity hypothesis keeps every frozen gate untouched and instead uses the
information already present in *partial* gate agreement, which is available on every
eligible asset-hour rather than on 0.13% of them.

## 2 — Frozen score

For every causally eligible asset-hour, using the exact existing three ALIGNED gates:

    GATE_INTENSITY = int(direction_pass) + int(breakout_pass) + int(participation_pass)

Allowed values: `0, 1, 2, 3`.

No weights. No continuous rescaling. No asset-specific normalization. No new thresholds.
No parameter fitting. No optimization.

The frozen consistency requirement, verified mechanically over the whole panel:

    ALIGNED_SIGNAL == 1  if and only if  GATE_INTENSITY == 3

The gate decomposition is a pure refactor of the frozen evaluator: identical windows
(25 hourly bars, 43 completed 4h bars), identical thresholds (prior-24h high, `U >= 2D`,
2x prior-24h mean volume), and it is verified row-for-row against the frozen
`FeatureSource` engine.

## 3 — Frozen future primary

Outcome is unchanged: 24-hour forward log-price return in bps, with the already-frozen
causal start (next completed tradable hourly open) and terminal (latest legitimate
tradable price at or before +24h, never interpolated) semantics.

    Y(i,t) = alpha_i + gamma_t + beta_gate * GATE_INTENSITY(i,t) + e(i,t)

Exactly one primary coefficient, `beta_gate`, with future directional claim
`beta_gate > 0`, in bps per additional satisfied gate.

No nonlinear gate-count model. No separate coefficient by score bucket. No gate
interaction rescue. No per-asset winner selection. Per-score row counts may be reported
because they contain no future-return result.

## 4 — Frozen economic threshold

    GATE_INTENSITY_MESI_BPS_PER_GATE = 8.0

Derivation: the governed informational lower bound for the full ALIGNED condition is
24 bps. Under the frozen linear intensity hypothesis the score-3 minus score-0 difference
is `3 * beta_gate`, so `24 / 3 = 8` bps per additional satisfied gate.

This is a necessary informational relevance threshold. It is not a claim that the product
earns 24 bps or 5% per year. It is not changed after power is measured.

## 5 — The retired placebo

The previous per-asset position-shift placebo is retired for inference because the same
position shift implied different calendar shifts by asset, cross-asset synchrony was not
preserved, the shift range was constrained by the shortest participant, and calibration
failed materially (9.2x size inflation). It is not reused as the primary randomization
procedure.

It also carried a participation rule — `epoch_decision_rows >= 504` — whose input is a
whole-sample epoch length. That rule is not point-in-time and is inadmissible as a design
filter; it is retired with the placebo and is not reintroduced here. The new design
applies **no** whole-sample asset filter: every instrument epoch participates.

## 6 — Calendar-synchronous randomization V1

The entire cross-sectional `GATE_INTENSITY` field moves together in calendar time.

For each development calendar year 2019..2024:

- shift by **whole UTC weeks**;
- one common **signed** week displacement applies to **all assets** in that year;
- minimum absolute displacement **2 weeks**, maximum **13 weeks**;
- no zero displacement;
- no circular wrap;
- a cell is used only where causal eligibility exists at **both** source and destination.

This preserves cross-asset score synchrony, hour-of-week and day-of-week structure,
year/regime membership, and asset identity.

The family is **1024 deterministic unique six-year shift vectors** generated from the
fixed preregistered seed `ALIGNED_GATE_INTENSITY_CALENDAR_RANDOMIZATION_V1` by a
counter-based SHA-256 draw over the 24 legal displacements. Every vector assigns one legal
non-zero shift to every year. The construction depends only on the seed and calendar
geometry and never on outcomes, signals, or asset identity.

## 7 — Randomization support gate (frozen before power)

Every accepted replicate must retain:

- at least **70%** of the zero-shift eligible design rows;
- at least **80%** of the eligible asset/instrument clusters;
- all six development years.

These are support and geometry checks only; they never inspect performance. Recorded per
replicate: row retention, asset-cluster retention, week-cluster retention, score-level
counts, year coverage.

If fewer than **512** of the 1024 frozen vectors satisfy the support rules,
`RANDOMIZATION_SUPPORT_STATUS = REDESIGN_REQUIRED` and the work stops. Thresholds are not
loosened and no second shift family is generated.

## 8 — Empirical randomization inference

The primary future inference is **empirical randomization**, not the failed analytic
two-way cluster p-value. For every accepted non-zero shift the pooled two-way-FE
`beta_gate` is computed on the shifted score; those non-zero values constitute the
prospective null calibration. The zero-shift beta is never calculated.

Prospective family size if later executed is **13** — neither sparse P1A nor the sparse
cross-section consumed an observed material hypothesis. Effective alpha is
`0.05 / 13`, one-sided positive, using conservative empirical order-statistic critical
values. Analytic clustered SE/t may be reported only as a diagnostic and may never
override the empirical randomization decision.

## 9 — Prospective power

Target power `0.80` at `MESI = 8.0` bps/gate. Because the fixed-effects estimator is
linear, power is calibrated by synthetic injection on **non-zero shifted designs only**,
with allowed slopes `0, 4, 8, 16, 32` bps/gate. An injected delta must be demonstrably
recovered as an exact additive shift in beta within numerical tolerance. No true
zero-alignment score/outcome covariance is computed.

## 10 — Power gate

`GATE_INTENSITY_POWER_GATE_STATUS = READY_FOR_PREREGISTRATION` requires all of
`DATA_SOURCE_STATUS`, `UNIVERSE_FEASIBILITY_STATUS`, `SURVIVORSHIP_STATUS`,
`EVENT_RECONCILIATION_STATUS`, `RANDOMIZATION_SUPPORT_STATUS` and
`RANDOMIZATION_INFERENCE_STATUS` equal to `PASS`, plus
`power_at_8_bps_per_gate >= 0.80`. Otherwise the status is `REDESIGN_REQUIRED`.

On `REDESIGN_REQUIRED` the executor may not change the score, weight gates, test 2-of-3,
test individual gates, add interactions, alter the horizon, alter the universe, lower
MESI, lower power, or try another placebo. It records
`ALIGNED_DEVELOPMENT_FAMILY_STATUS = PARKED_DEVELOPMENT_SEARCH_EXHAUSTED` and returns to
the Research Director.
