# System G1 Cycle Method Contract V1

Status: **METHOD FAMILY FROZEN — SYNTHETIC VALIDATION REQUIRED BEFORE ACTIVE USE**
Date: 2026-09-25
Generation: SYSTEM_G1

## Purpose

Represent cyclical structure as one causal multi-scale context/timing family without:

- selecting the historically best timeframe;
- using future extrema;
- centred/future-backward smoothing;
- inventing an AI cycle theory;
- treating six scales as six independent votes.

The cycle family may qualify timing. It cannot override price invalidation, data quality, occupancy
or risk vetoes.

## Documentary basis

Primary method family: John F. Ehlers-style causal digital-signal-processing cycle analysis.

The period/quality measurement is based on the **Autocorrelation Periodogram** described in Ehlers'
cycle work and the official September 2016 Stocks & Commodities implementation companions.

Key documentary constraints adopted:

- causal high-pass + SuperSmoother preprocessing;
- Pearson autocorrelation over past values;
- sine/cosine spectral projection of the autocorrelation sequence;
- dominant-period center of gravity over material normalized spectral power;
- no full-series/future-backward processing.

The official MESA technical-paper index explicitly warns against an older pure-sine-wave Dominant
Cycle derivation on noisy market data. G1 does not implement that deprecated construction.

References for implementation review:

- https://www.mesasoftware.com/TechnicalArticles.htm
- https://traders.com/Documentation/FEEDbk_docs/2016/09/TradersTips.html
- Ehlers, *Cycle Analytics for Traders* (2013), Autocorrelation / spectral chapters.

The project does not copy a trading strategy from those sources; it adopts a documented causal
measurement family.

## Fixed scale hierarchy

Scales are frozen for G1 before market outcomes:

| Nominal scale | Input bars | Nominal samples | ACP period search |
|---|---:|---:|---:|
| 45m | completed 3m | 15 | 10..22 |
| 3h | completed 15m | 12 | 10..18 |
| 1d | completed 1h | 24 | 16..36 |
| 4d | completed 4h | 24 | 16..36 |
| 1w | completed 4h | 42 | 28..48 |
| 4w | completed 1d | 28 | 19..42 |

These bands are structural design ranges around each nominal scale, not historically selected
periods.

All bars are UTC and completed before use.

## Preprocessing and spectrum

For each scale, use the Ehlers Autocorrelation Periodogram construction with:

- `period1` = search lower bound;
- `period2` = search upper bound;
- Pearson averaging length = 3;
- causal high-pass/SuperSmoother preprocessing;
- autocorrelation lags through `period2`;
- DFT-style sine/cosine projection over periods `period1..period2`;
- recursive spectral-power smoothing coefficient 0.2;
- normalized power at each candidate period;
- dominant period = spectral-power center of gravity over periods whose normalized power is
  `>= 0.5`.

Implementation must be numerically reconciled against an independent reference implementation on
synthetic fixtures before use.

No MESA optimizer, FFT period winner, alternate ACP range or alternate smoothing constant is
allocated.

## Orientation / phase-like state

G1 does **not** require an exact degree-valued phase estimate to trade.

The initial active cycle state uses a causal trailing projection at the current ACP dominant period:

- use only the preprocessed observations available through the current scale bar;
- project the trailing `round(dominant_period)` samples onto sine/cosine components;
- derive a normalized cycle coordinate and its one-step causal slope;
- preserve the projection angle diagnostically when numerically stable;
- label the angle `PHASE_ESTIMATE_DIAGNOSTIC`, never a probability or guaranteed turn time.

If the projection is unstable or support is insufficient, phase is null and the scale remains
available only as weak/unavailable context.

No phase may be reconstructed with future samples.

## Turn confirmation

A cycle turn is not actionably recorded at the historical extremum itself.

A `CONFIRMED_UP_TURN` or `CONFIRMED_DOWN_TURN` requires:

1. a local change of sign in the causal projected cycle slope; and
2. one subsequent completed input bar that does not reverse that sign.

The event stores:

- estimated historical turn time;
- later confirmation/availability time.

Only the confirmation time can affect prediction/trading.

## Quality

Cycle quality is a measurement of spectral concentration/support, not forecast probability.

Before any historical market-performance run, the implementation must pass a frozen synthetic
fixture suite covering:

- clean sinusoid inside band;
- two-frequency mixture;
- linear trend + cycle;
- white noise;
- abrupt period change;
- amplitude decay;
- missing observations/gaps.

The synthetic gate will freeze deterministic quality labels:

- UNAVAILABLE;
- WEAK;
- USABLE.

Those label thresholds may be selected only from the synthetic method-validation fixtures and
numerical stability requirements, never from BTC returns or G1 trading outcomes.

Until that synthetic gate is completed, all live/replay cycle states are
`METHOD_NOT_READY` and cannot affect conviction or trade eligibility.

## Warm-up

Per scale, minimum warm-up is:

`max(4 * period2, 128)` completed input bars.

A scale is UNAVAILABLE before warm-up and after a gap that invalidates the recursive state until the
declared re-warm rule is satisfied.

Long-scale live states must not be silently populated from protected history across a data gap.

## Multi-scale output

Each CycleState contains per scale:

- nominal scale;
- input resolution;
- search range;
- dominant period in input bars and wall-clock units;
- normalized spectral-power vector/hash;
- quality;
- projected coordinate;
- optional diagnostic phase;
- slope direction;
- last confirmed turn + confirmation time;
- warm-up/readiness;
- data-gap state;
- method version;
- limitations.

The family summary must preserve individual scale disagreement.

## G1 timing qualifier mapping

The exact active qualifier is frozen as follows, subject to the synthetic quality gate:

- **FAST**: 45m + 3h scales.
- **INTERMEDIATE**: 1d + 4d scales.
- **SLOW**: 1w + 4w scales.

A playbook receives:

- `CYCLE_SUPPORTS_LONG` only when FAST is rising/confirmed-up and no USABLE INTERMEDIATE scale is
  confirmed-down; SLOW disagreement is reported but is not a veto.
- `CYCLE_SUPPORTS_SHORT` symmetrically.
- otherwise `CYCLE_MIXED_OR_WEAK`.

A group contributes only USABLE scales. If a group has no USABLE scale it is UNKNOWN.

Cycle support is a timing corroboration only. It can help distinguish MEDIUM from HIGH conviction
where the playbook contract requires it; it cannot create a trade without the price/structure
trigger.

No numeric weight or majority score is used.

## Anti-repainting / replay rules

- issued CycleState records are immutable;
- revisions create new later states;
- full-series centered filters and `filtfilt`-style forward/backward processing are forbidden;
- the same recursive implementation runs in live-style and historical replay adapters;
- replay speed must not change cycle results.

## Relation to prior cycle work

The old P2 cycle programme used a different 4h-return 2–90 day structural spectral question and was
blocked on its frozen null/support methodology before market-cycle performance was established.

That evidence remains preserved.

This G1 cycle family is a contextual causal state contract, not a restart of the blocked P2 null
design and not evidence that cycles are profitable.

## Authorization

Synthetic implementation/validation is permitted only under a Checkpoint-1 task.

No historical G1 performance comparison is authorized by this contract.
