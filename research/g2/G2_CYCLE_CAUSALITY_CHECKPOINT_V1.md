# G2 Cycle Causality Checkpoint V1

Status: METHOD SELECTED; SHADOW-ONLY FOR G2-V0; ACTIVE POLICY USE NOT YET AUTHORIZED  
Date: 2026-09-27  
Checkpoint: CYCLE-CAUSALITY-01

## 1. Decision

G2 will not run a cycle-method tournament.

The sole candidate is the existing System G1 causal Autocorrelation Periodogram implementation:

- backend/app/g1/cycle.py
- research/protocols/SYSTEM-G1-CYCLE-METHOD-V1.md
- research/protocols/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.md
- reports/checkpoints/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.md
- decisions/ADR-0046-ACCEPT-G1-CYCLE-QUALITY-AND-ACTIVATE-CYCLE-COMPONENT.md

The G1 predictive/economic claim does not transfer. Only the measurement method and its synthetic
method-quality lineage are considered reusable.

G2-V0 treatment:
- record/display cycle state;
- zero forecast coefficients;
- zero utility coefficients;
- no cycle veto;
- reason code CYCLE_SHADOW_ONLY.

A later G2 development revision may activate at most two cycle-derived timing terms only under the
rules in this document.

## 2. Existing method

Method family:
causal Ehlers-style Autocorrelation Periodogram (ACP).

Current recursive pipeline:
1. two-pole causal high-pass;
2. SuperSmoother low-pass;
3. Pearson autocorrelation on trailing filtered data;
4. DFT-style sine/cosine projection across the fixed period band;
5. recursive power smoothing;
6. normalized power;
7. dominant-period center of gravity over power >= 0.5;
8. causal trailing projection at dominant period.

No centered filter, backward pass or future observation is part of the implementation.

Current G1 quality rule:
- UNAVAILABLE if warm-up/gap/dominant/projection invalid;
- USABLE only when explained_fraction >= 0.90 on current plus previous two completed input bars;
- otherwise WEAK.

These thresholds are historical frozen method-quality conventions. G2 does not retune them against
BTC P&L.

## 3. Existing actual-repository synthetic evidence

The frozen G1 gate already passed on the real implementation.

Recorded evidence includes:
- 128 white-noise paths per scale;
- 48 clean-cycle paths;
- 48 trend+cycle paths;
- two-frequency diagnostics;
- amplitude decay;
- abrupt period change;
- missing-observation/reset tests;
- replay-speed invariance;
- independent ACP reference reconciliation.

Recorded gating results:
- white-noise USABLE occupancy medians approximately 1.8%-2.5%;
- noise p95 approximately 4.7%-9.0%;
- clean coherent-cycle median/p10 USABLE occupancy 100%;
- dominant-period median relative error approximately 3.9%-4.6%;
- zero future turn-confirmation violations;
- gap/reset full re-warm PASS;
- replay-speed identity PASS;
- independent implementation reconciliation max difference 0.

Important limitation:
the clean and trend+cycle fixtures were effectively noise-free and the high-pass removes a linear
trend. The old gate did not establish robustness under additive noise.

Passing G1's gate proved method correctness under its declared fixtures. It did not prove BTC
predictive utility.

## 4. G2 supplemental numerical method check

For G2-00 the Research Director performed a supplemental, non-market numerical check of the exact
ACP/projection equations transcribed from the current implementation. This is not a substitute for
the G2-01 code-level regression tests; it closes method-design ambiguity before implementation.

Fixed noisy-cycle fixture:
- amplitude 1;
- Gaussian noise standard deviation 0.5;
- 48 paths per scale;
- true period = midpoint of each scale's frozen ACP band;
- warm-up respected;
- no market data.

Results:

| Scale | Median USABLE occupancy | P10 occupancy | Median dominant-period relative error | P90 period error |
|---|---:|---:|---:|---:|
| 45m | 0.674 | 0.598 | 0.056 | 0.063 |
| 3h | 0.799 | 0.738 | 0.042 | 0.047 |
| 1d | 0.861 | 0.804 | 0.065 | 0.076 |
| 4d | 0.876 | 0.818 | 0.066 | 0.074 |
| 1w | 1.000 | 0.990 | 0.036 | 0.039 |
| 4w | 0.926 | 0.873 | 0.059 | 0.071 |

Interpretation:
the existing quality rule abstains materially under noisy fast cycles instead of pretending every
sample is reliable, while retained dominant-period estimates remain reasonably close in this fixed
synthetic condition. These are method diagnostics, not BTC acceptance thresholds.

## 5. Pure trend without cycle

Fixed fixture:
- deterministic linear trend;
- no cyclical component;
- same warm-up and scale ranges.

Supplemental result:
- USABLE occupancy after warm-up = 0 for all six scales.

The ACP can still emit a numerical dominant-period candidate in some pure-trend states, but the
projection quality remains below the USABLE contract. Therefore the actionable quality state
correctly abstains.

This distinction is important: a numeric period is not a valid cycle merely because a periodogram
returns one.

## 6. Isolated jump fixture

Fixed fixture:
- constant level;
- one permanent step jump;
- no recurring cycle.

Supplemental result:
- USABLE occupancy after warm-up = 0 for all six scales;
- USABLE occupancy in the first 64 bars after the jump = 0 for all six scales.

This supports the intended abstention behavior for a non-periodic shock under this fixture.

## 7. Slowly changing frequency

Fixed chirp fixture:
- period changes continuously from the lower-middle to upper-middle portion of the frozen band;
- no market data.

Observed median dominant-period relative tracking error after warm-up:
- roughly 2.8%-4.2% across the six scales in the fixed deterministic fixture.

USABLE occupancy was 100% in this clean chirp fixture.

Interpretation:
the method can track a slowly moving synthetic period, but this does not establish a minimum
real-market stability or utility.

## 8. Prefix stability

A full synthetic path and an independently rerun prefix of the same path were compared.

Supplemental result:
- maximum absolute difference in dominant period, phase, explained fraction and derived amplitude
  before the prefix boundary = 0;
- quality labels were identical.

The production G2-01 test must repeat prefix invariance against the actual repository implementation,
including gap/reset state.

## 9. Phase lag

On clean midpoint-period sinusoids, the supplemental projection showed sub-input-bar median phase
offset in the fixed steady-state fixtures. Equivalent median offsets were below one input bar across
all six scales.

This is a diagnostic of the projection convention, not a promise about lag during regime changes.

G2 records two different latency concepts:
- FILTER/PHASE LAG: measured on synthetic fixtures and stored by method version;
- TURN CONFIRMATION LAG: the existing method intentionally requires a subsequent completed input bar
  before recording a confirmed turn.

The UI/reasoning must never present a confirmed turn as known at the earlier estimated extremum.

## 10. Required G2 amplitude field

The existing G1 CycleScaleState does not expose a projection-amplitude field required by Astra's G2
knowledge card.

G2 freezes the following diagnostic amplitude for implementation:

For projection window length L and DFT components re/im at the dominant period:

PROJECTION_AMPLITUDE = 2 * sqrt(re^2 + im^2) / L.

This is the amplitude of the fitted filtered sinusoidal component in filtered-price units. It is:
- descriptive;
- non-directional;
- not an alpha coefficient;
- not a replacement for explained_fraction.

Adding this output must not alter the existing ACP, phase, dominant period or quality label
semantics.

## 11. G2 period-stability field

Add descriptive:

PERIOD_STABILITY =
abs(dominant_period_t - dominant_period_(t-1))
/ max(dominant_period_(t-1), 1e-12).

If either period is unavailable:
PERIOD_STABILITY = null.

This field is recorded and may support later diagnostics. G2-V0 does not use it as a forecast or
policy term.

## 12. Frozen scale map

The measurement scale map remains:

| Nominal | Input | ACP range | Role in G2-V0 |
|---|---|---|---|
| 45m | 3m | 10..22 | shadow |
| 3h | 15m | 10..18 | shadow |
| 1d | 1h | 16..36 | shadow |
| 4d | 4h | 16..36 | shadow |
| 1w | 4h | 28..48 | shadow |
| 4w | 1d | 19..42 | shadow |

No economic comparison among alternative bands is authorized.

## 13. G2-01 exact method acceptance tests

Before cycle state can be classified AVAILABLE_FOR_RESERVED_REVISION, the actual G2 implementation
must pass all of:

1. byte/numeric parity with the frozen G1 ACP core for dominant period/phase/quality where the G2
   contract preserves semantics;
2. white-noise gate from the existing protocol;
3. clean coherent-cycle gate from the existing protocol;
4. additive-noise fixture fixed at amplitude 1 / noise sd 0.5 with finite outputs and explicit
   quality abstention;
5. pure linear trend: no USABLE state after warm-up;
6. isolated permanent jump: no USABLE state in the first 64 post-jump input bars;
7. slowly varying frequency: finite bounded period/phase outputs with no look-ahead;
8. prefix invariance: all pre-prefix outputs identical;
9. gap/incomplete-bar reset and full re-warm;
10. projection-amplitude field finite/non-negative whenever projection exists;
11. period-stability field exact according to this contract;
12. turn confirmed_at strictly later than its estimated extremum and never retroactively available;
13. replay-speed identity.

The additive-noise occupancy figures in this document are diagnostic references, not tuning targets.
A discrepancy triggers scientific review; it does not authorize parameter adjustment to recover the
reference numbers.

## 14. Checkpoint disposition

Current checkpoint state:

METHOD_SELECTED = EXISTING_CAUSAL_ACP  
METHOD_TOURNAMENT = FORBIDDEN  
G2_V0_RUNTIME_ROLE = SHADOW_ONLY  
FORECAST_COEFFICIENTS = 0  
POLICY_COEFFICIENTS = 0  
VETO_AUTHORITY = NONE  
PREDICTIVE_UTILITY = UNPROVEN

After G2-01 code-level tests:

- all tests pass -> AVAILABLE_FOR_RESERVED_REVISION;
- any causality/prefix/reset failure -> CYCLE_UNAVAILABLE;
- numerical disagreement needing a method change -> stop and Research Director review;
- no search for a second method inside G2.

This is sufficient for Gate A because the baseline behavior is fully defined even if cycle activation
never occurs.
