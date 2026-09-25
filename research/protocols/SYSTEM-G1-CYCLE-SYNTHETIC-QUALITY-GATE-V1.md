# System G1 Cycle Synthetic Quality Gate V1

Status: **FROZEN BEFORE EXECUTION**
Date: 2026-09-25
Authority: ADR-0045

## Purpose

Determine whether the already-implemented System G1 cycle method can distinguish sufficiently
persistent synthetic cyclic structure from pure synthetic noise **without using BTC market
performance**.

This is method validation, not alpha evidence.

## Frozen quality labels

For one scale:

### UNAVAILABLE

Any of:

- warm-up incomplete;
- active re-warm after gap;
- dominant period unavailable;
- causal projection unavailable.

### USABLE

All must hold:

- scale otherwise available;
- `explained_fraction >= 0.90` on the current completed input bar;
- same condition held on each of the immediately preceding two completed input bars;
- no gap/reset occurred inside the three-bar persistence window.

### WEAK

Scale is available but does not satisfy USABLE.

No other metric participates in the quality classification.

## Paths

For each frozen scale create deterministic synthetic ensembles using distinct documented seeds.

### White noise

Minimum 128 paths per scale.

Each path:

- Gaussian zero-mean white noise;
- length sufficient for normal warm-up plus at least 512 evaluated bars;
- amplitude normalized consistently with existing diagnostic conventions.

### Clean cycle

Minimum 48 paths per scale.

Cover equally:

- period near lower quartile of the frozen band;
- band midpoint;
- period near upper quartile.

Randomize deterministic phase across paths.

### Trend + cycle

Same period/phase design as clean cycle with a deterministic modest linear trend that the causal
preprocessing should remove.

### Additional diagnostics — non-gating

Retain:

- two-frequency mixture;
- amplitude decay;
- abrupt period change;
- missing observations.

They are reported but do not select or alter the frozen threshold.

## Metrics

Per path and scale:

- post-warm-up USABLE occupancy;
- longest USABLE streak;
- dominant-period median and relative error where truth exists;
- turn count / confirmation delay;
- any pre-confirmation/repainting violation;
- gap reset / re-warm identity;
- replay-speed identity.

Aggregate:

- median / p10 / p95 occupancy as relevant;
- period error distribution;
- failures by scale / fixture.

## Mandatory pass gates

Every scale must pass:

### Noise rejection

- white-noise median USABLE occupancy <= 0.05;
- white-noise p95 USABLE occupancy <= 0.15.

### Coherent retention

For both clean-cycle and trend+cycle ensembles:

- median USABLE occupancy >= 0.80;
- p10 USABLE occupancy >= 0.60;
- median relative dominant-period error <= 0.10.

### Integrity

- zero future-data / turn-confirmation violations;
- gap/reset semantics PASS;
- speed invariance PASS;
- independent ACP reconciliation PASS.

## Disposition

If all mandatory gates pass:

`CYCLE_SYNTHETIC_QUALITY_GATE_PASS_PENDING_RESEARCH_DIRECTOR_ACTIVATION`

If any mandatory gate fails:

`CYCLE_SYNTHETIC_QUALITY_GATE_FAIL_METHOD_NOT_READY`

Claude may not alter thresholds, add quality features, alter scale bands, alter ACP parameters or
search another cycle method after seeing the result.

Cycle remains excluded from decisions until a later Research Director adjudication explicitly
activates it.

No market data or market outcomes are permitted.
