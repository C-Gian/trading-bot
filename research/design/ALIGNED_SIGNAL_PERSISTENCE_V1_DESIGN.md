# ALIGNED_SIGNAL_PERSISTENCE_V1 — frozen design (not a preregistration)

Status: DESIGN ONLY. No preregistration, no runnable candidate, no executed experiment.

This document freezes the design of a **future** material economic hypothesis so that its
prospective power can be measured before any outcome is observed. It is not authority to
execute. Execution requires a preregistration that the Research Director authorizes after
the power gate passes.

## Future hypothesis

`ALIGNED_SIGNAL_PERSISTS_TO_120H_V1`

> Does the frozen ALIGNED signal contain positive directional information that persists
> to five days, beyond matched random timing exposure?

If executed, P1A would become the 13th observed material economic hypothesis. It has not
been executed and the family remains at 12 observed hypotheses.

## Primary horizon

**120 hours**, frozen before any P1A outcome was inspected. The hypothesis is about
five-day multi-day persistence, so the horizon is fixed by the scientific question, not
selected from a menu of candidates.

24h is retained only as the already-exposed historical reference and reproduction
diagnostic. 48h, 72h and 168h are **not** in the design and no horizon search is
performed. Adding a horizon later would be a new hypothesis consuming new search budget.

## Signal semantics

The frozen `ALIGNED_PARTICIPATION_CONTINUATION_V1` / `ALIGNED` decision logic is used
unchanged (`app.research.continuation.FeatureSource.decision`, feature version
`CONTINUATION_FEATURES_V2`, delay 0). No stop, target, volume, trend or breakout
parameter is touched.

Events are **raw signal events**: every hourly decision instant whose ALIGNED conditions
fire is an event. Portfolio occupancy never suppresses an event, because this is an
information study rather than an execution study. The historical development run
suppressed 70 of 195 emitted conditions through its one-position-at-a-time rule; that
rule has no role here.

Signal generation uses only information available at the signal instant: the ALIGNED
feature windows end at the decision instant, and every required 1h/4h bar must be
complete and contiguous or the clock is ineligible.

## Informational outcome definition

- Primary measurement: **120h forward BTCUSDT price return in basis points**.
- Start price: the governed causally tradable **next 1m open** — the canonical 1m bar
  whose `open_time` equals the signal instant, the same entry convention the frozen
  engine uses for `NEXT_1M_OPEN`.
- Terminal price: the **close of the 1m bar opening at signal + 7199 minutes**, so the
  terminal instant is exactly signal + 7200 minutes = signal + 120h. This mirrors the
  frozen engine's expiry convention and is fixed before any result exposure.
- No stop, no target, no trailing logic, no one-position-at-a-time rule, no R
  denominator.
- Identical hypothetical entry/exit cost assumptions apply to signal and placebo timing,
  so they cancel; the primary differential effect is expressed in **excess bps**.

An event is admissible only when all 7200 minute bars from the signal instant onwards are
present and contiguous. Missing minutes are never forward-filled or imputed.

## Fold and time rules

The six fixed annual development folds of `DEVELOPMENT_WALK_FORWARD_V1` are retained. No
model is fitted in P1A, so no training purge is invented. Instead:

- causal ALIGNED feature availability is enforced per clock;
- the fixed next-1m start convention is enforced per event;
- the complete 120h outcome must be contained inside the evaluation fold, so the last
  admissible decision instant of each fold is `validation_end_exclusive − 120h`
  (27 December 00:00 UTC) rather than the 24h-horizon `31 December 00:00 UTC`;
- no forward fill across invalid data;
- no access to any minute after the development cutoff `2024-12-31T23:59:00Z`.

### Event-count reduction caused by the longer containment

| stage | events |
| --- | --- |
| conditions emitted on the historical 24h-containment signal window | 195 |
| conditions emitted on the 120h-containment signal window | 193 |
| raw events retained after complete 120h outcome containment | **180** |

The 96-hour shorter signal window costs 2 events; incomplete 120h forward minute paths
cost a further 13, concentrated in the 2019–2021 gap-affected folds.

## Matched timing control

Naive event IID, historical positive-ACF ESS, ordinary event-index Newey–West and
independently resampled random events are all rejected: the first three misstate
dependence, and the last destroys ALIGNED's temporal clustering.

The control is a **deterministic within-fold circular calendar shift**
(`DETERMINISTIC_WITHIN_FOLD_CIRCULAR_CALENDAR_SHIFT_V1`):

1. For each fold, construct the eligible hourly decision grid — every hourly instant in
   `[validation_start, validation_end_exclusive − 120h]` with a complete causal ALIGNED
   feature history requirement checked per clock and a complete 120h forward outcome.
2. Construct the frozen binary raw-ALIGNED signal sequence on that grid.
3. Generate placebo sequences by circularly shifting the whole signal sequence by a
   common displacement `s` within each fold, modulo that fold's grid length.
4. Shift zero is never used in prep and is rejected by the API.
5. The minimum absolute circular displacement is **168 positions**, strictly greater than
   the 120h primary horizon. Consecutive grid instants are at least one hour apart, so a
   displacement of `d` positions always moves an event by at least `d` hours of calendar
   time; 168h leaves a 48h margin beyond the horizon in both circular directions.

The same displacement rule applies to every fold. Admissible displacements are
`s ∈ [168, K_min − 168]` where `K_min` is the shortest fold grid, which also guarantees
the 168-position minimum in the longer folds.

The shift preserves the number of signals, the within-fold clustering and cyclic order
structure, annual market exposure, the horizon and signal sparsity. Because the grid
contains only outcome-eligible instants, **every** shifted event has a defined outcome,
so the event count is preserved exactly under every admissible shift.

All deterministic admissible shifts are enumerated. No random seed is used and no subset
is selected.

## Primary future statistic

If P1A is later authorized, its primary effect is

> mean 120h forward return in bps at the frozen ALIGNED raw events
> **minus**
> the central matched timing-control expectation

where the central estimator is frozen as the **arithmetic mean of placebo event-mean
returns** over the admissible shift set. The directional claim is positive excess only.

The actual zero-shift statistic is not calculated in this prep, and the prep command
cannot calculate it.

## Multiplicity

- Family alpha: 0.05.
- Documented observed material family: 12 hypotheses.
- P1A would be the 13th, so the prospective gate uses the conservative first-rank
  familywise threshold `alpha_effective = 0.05 / 13 ≈ 0.0038461538`.
- Basis: Holm's first-rank threshold equals `alpha / m`; no existing deterministic Holm
  governance in this repository proves a stricter requirement.
- Unquantified pre-repository exposure is **not** converted into a numeric family size.
  The documented family remains a lower bound.

## Economic significance

The Owner policy is +5 percentage points annualized net excess return versus a matched
control, i.e. 500 bps/year (`governance/ECONOMIC_SIGNIFICANCE_POLICY_V1.json`).

Translated prospectively at the already-exposed ALIGNED development cadence of 125
resolved DEFAULT trades over six fixed annual folds:

```
reference cadence        = 125 / 6 = 20.8333333333 trades/year
P1A_INFORMATION_MESI_BPS = 500 / (125 / 6) = 24.0 bps per event
```

24 bps/event is a **necessary informational lower bound** for a mechanism operating at
approximately the historical ALIGNED product cadence. It is **not** sufficient evidence
that a 120h execution strategy would deliver +5 percentage points/year: longer holding
may suppress future executable signals, which is a P1B question. The MESI may not be
lowered because a power result is unfavourable.

## Power gate

Using only non-zero admissible shifted sequences:

- the null distribution is the set of admissible placebo pooled event-mean returns;
- it is centred deterministically on the frozen central estimator;
- the one-sided critical value at `alpha_effective` is the `(K+1)`-th largest placebo
  pooled mean with `K = floor(alpha_effective × (M + 1)) − 1`, matching a randomization
  p-value of `(1 + #{placebo ≥ statistic}) / (1 + M)`;
- empirical power under an injected `+Δ` bps/event shift is the fraction of admissible
  placebo draws whose required displacement is strictly below `Δ`;
- the empirical MDE is the smallest multiple of 1e-6 bps strictly greater than the
  `ceil(0.80 × M)`-th smallest required displacement.

`POWER_GATE_STATUS = READY_FOR_PREREGISTRATION` only when power at the frozen MESI is at
least 0.80, the randomization resolution supports the effective alpha, and every
integrity test passes. Otherwise `REDESIGN_REQUIRED`.

The measured outcome is recorded in
`reports/power/P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-V1.json`.

## Leakage safeguards

- Every aggregation runs through `placebo_pooled_mean_bps`, which rejects any circular
  displacement below 168 positions, zero included.
- The prep command exposes no unshifted aggregate; there is no code path from it to one.
- No artifact may contain the actual zero-shift 120h ALIGNED mean, the actual
  ALIGNED-minus-placebo effect, a true P1A p-value, or any classification of P1A
  performance. `assert_no_result_leakage` fails closed on those keys.
- No future actual outcome artifact exists.
