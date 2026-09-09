# PERSISTENT_TREND_PULLBACK_RECOVERY_V1 — frozen design

Recorded before implementation, admission, preregistration and any market result.

## Economic hypothesis (exactly one)

During an already persistent multi-day uptrend, an hourly close recovering above its
one-day mean after the previous hour was at or below that mean may identify a
temporary countertrend weakness ending, offering a better continuation entry than
buying a fresh high.

The claim is about **when** to join an existing trend, not about whether trends
exist. It is falsifiable by the frozen DEVELOPMENT_EVALUATION_V1 terminal rule.

## Why this is a different mechanism, not a breakout descendant

- There is **no** close-above-prior-high requirement anywhere in the primary rule.
- There is **no** SMA24 > SMA168 membership rule; the fast/slow mean-crossing family
  is untouched.
- The anchored entry event is a **recovery transition** — a state change from
  at-or-below the one-day mean to above it — not a level being exceeded.
- Breakout and SMA-membership families select bars that are already extended.
  This family deliberately selects bars that were recently weak.

The distinction is asserted here and then tested, not assumed: the proposal is
submitted to the SEARCH_MEMORY_V2 novelty gate before any market result exists, and a
DUPLICATE, PARAMETER_VARIANT, NEAR_DUPLICATE or conflicting-root classification blocks
execution outright.

## Inherited primitive

The 4h persistent-up descriptor is **inherited unchanged** from the frozen WP-004
declaration and is not independent new evidence:

- 43 completed contiguous 4h closes give 42 close-to-close changes;
- `U` is the sum of positive changes, `D` the absolute sum of negative changes;
- persistent-up holds iff `U >= 2*D` and `U + D > 0`.

Bar eligibility, source-grid quarantine, contiguity and cutoff semantics are also
inherited unchanged from `CONTINUATION_FEATURES_V2`, so both families share one
data-quality universe.

## Definitions at hourly decision boundary t

`SMA24_t` is the arithmetic mean of the 24 completed 1h closes ending with the
just-closed current bar. `SMA24_prev` is the arithmetic mean of the 24 completed 1h
closes ending one hour earlier. Both windows must be complete and contiguous, which
requires exactly 25 completed contiguous hourly bars ending at `t - 1h`.

`previous_close` and `previous_1h_high` come from the bar opening at `t - 2h`.
The reference price is the current completed 1h close.

## The two frozen variants

**Variant 1 — RECOVERY_CORE (PRIMARY, fixed before results).** Emit LONG iff
`previous_close <= SMA24_prev`, `current_close > SMA24_t`, and `persistent_up(t)`.

**Variant 2 — RECOVERY_CONFIRM.** `RECOVERY_CORE` and `current_close >
previous_1h_high`.

No volume condition, no breakout condition, no SMA168, no alternate SMA period, no
pullback-depth threshold. Zero numeric parameter variants are authorized.

## Fixed geometry and profiles

Stop `reference * 0.98`, target `reference * 1.04`, maximum hold 1,440 minutes,
one active position, LONG only, no leverage. Exactly four profiles per variant:
`DEFAULT`, `ZERO`, `DOUBLE`, `DELAY_1H`. Eight profile evaluations in total.

## Falsification

`DEVELOPMENT_EVALUATION_V1` is applied unchanged. The family conclusion follows the
primary `RECOVERY_CORE` variant, never whichever variant scores better. Even a
`PROMISING_DEVELOPMENT_ONLY` outcome yields no Champion, no sealed query and no
paper trading.
