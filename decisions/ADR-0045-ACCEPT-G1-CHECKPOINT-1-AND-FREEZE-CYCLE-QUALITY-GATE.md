# ADR-0045 — Accept System G1 Checkpoint 1; hold cycle activation pending synthetic quality gate

Status: ACCEPTED — Research Director, 2026-09-25

## Review basis

Reviewed remote Checkpoint 1 implementation at commits:

- `134c4c6a56cc86089c1c63769196732e9da439a9`
- `8fa5b15516c546850950ab9c30390be51e5cf66d`

Reviewed:

- implementation validation record;
- checkpoint report;
- cycle synthetic diagnostics;
- causal core / immutable records;
- signed LONG/SHORT reference ledger;
- prediction/decision/realization separation;
- fail-closed production action guard;
- replay API / synthetic vertical slice.

No real historical System G1 market outcome was inspected.

## Adjudication

Accept System G1 Checkpoint 1 infrastructure as **PASS**.

Accepted:

- fail-closed semantics now depend on `validated_strategy is null`, not historical PARKED state;
- old ALIGNED/predictive strategy code cannot silently reactivate;
- immutable event records / append-only identities;
- causal completed-bar availability and virtual clock;
- replay speed invariance;
- native LONG/SHORT signed accounting;
- funding/cost/risk mechanics;
- prediction issued separately from later realization;
- NO_TRADE persisted as first-class decisions;
- causal replay API/UI vertical slice;
- HotWindow/PostAnalysis isolation;
- six-scale ACP implementation reconciled with independent reference;
- cycle state remains excluded from decisions pending quality approval.

## Cycle finding

The cycle implementation is numerically correct enough for the frozen method family, but the first
synthetic diagnostics do **not** yet justify activation.

Key observations:

- coherent in-band fixtures show high explained fractions and low period error;
- white-noise fixtures can still occasionally generate high apparent spectral/projection quality;
- simple single-snapshot quality metrics overlap noise in their upper tails;
- persistence must therefore be part of the quality gate;
- the 3h abrupt-period-change fixture shows slow threshold-crossing adaptation, so adaptation is
  retained as a diagnostic rather than used to select another method/range.

No market/BTC outcome may be used to choose cycle quality thresholds.

## Frozen pre-gate quality rule

Before the additional synthetic diagnostic run, freeze:

A scale is `USABLE` only when:

1. normal warm-up is complete;
2. there is no active gap/re-warm state;
3. dominant period and projection exist;
4. `explained_fraction >= 0.90` on the current completed input bar and the immediately preceding
   **two** completed input bars for that scale.

Otherwise:

- ready + numerically valid projection => `WEAK`;
- insufficient warm-up / gap / missing projection => `UNAVAILABLE`.

The 0.90 threshold and 3-bar persistence may not be altered after the next synthetic gate result.

No `peak_band_fraction`, `mean_normalized_power`, period-change threshold or BTC-derived
amplitude filter is added to rescue the gate.

## Required synthetic gate

The next checkpoint must test this already-frozen rule across multiple deterministic synthetic paths.

Pass requirements, evaluated separately for each of the six scales:

### False activation on pure noise

Using at least 128 independent deterministic white-noise paths:

- median post-warm-up USABLE occupancy <= 5%;
- 95th percentile path-level USABLE occupancy <= 15%.

### Retention on coherent structure

Across deterministic random phases and periods spanning lower/middle/upper portions of the frozen
band, for both clean sinusoid and trend+cycle families:

- median post-warm-up USABLE occupancy >= 80%;
- 10th percentile path-level USABLE occupancy >= 60%;
- median dominant-period relative error <= 10%.

Amplitude-decay remains a required diagnostic but not a mandatory occupancy gate because low
amplitude without a declared noise model is not enough to define economic relevance.

### Causal integrity

- no turn confirmation before estimated turn;
- gaps reset persistence and require normal re-warm;
- same synthetic stream produces identical labels at every replay speed;
- reference ACP reconciliation remains exact within current numerical tolerance.

If any mandatory gate fails, cycle remains `METHOD_NOT_READY`. No threshold search/rescue is
authorized. The Research Director will then decide whether this creates a material G1 architecture
impasse requiring Astra.

## Execution-delay correction

Astra's adopted architecture specifies a **1-minute primary operational delay** after all required
inputs are available.

Checkpoint 1 correctly implemented delay semantics but left `RiskPolicy` default at 0 minutes.

The next synthetic checkpoint must change the System G1 primary default to 1 minute and add/adjust
tests. This is a pre-outcome contract correction, not an empirical optimization.

The future robustness delay stress remains +5 minutes relative to the frozen primary convention.

## Authorization boundary

Authorize only the synthetic cycle-quality gate and the one-minute default-delay correction.

Do not:

- inspect G1 historical BTC performance;
- fit the G1 forecaster;
- calculate P1/P2 returns;
- choose playbook thresholds;
- access post-cutoff/sealed data;
- activate cycle in decisions until the synthetic gate passes and the Director reviews it.

Champion NONE. Validated strategy NONE. Operational output NO_TRADE. Real money false.
