# AGGRESSIVE_BUY_FLOW_TRANSITION_V1 — frozen design

Recorded before admission, preregistration and any market result.

## Why leave price shapes

Three families have now produced the same shape of evidence. `FAM-TREND` was rejected
cost-dominated. `FAM-BREAKOUT` reached `INCONCLUSIVE` through `ALIGNED` at
`+0.1373934676 R` default. `FAM-PULLBACK-RECOVERY` reached `INCONCLUSIVE` through
`RECOVERY_CORE` at `+0.0003823075 R` default with `+0.1204381257 R` gross.

The recurring pattern is a real gross margin that default BTCUSDT Spot friction
consumes, on sparse and concentrated samples. Enumerating more price shapes is unlikely
to break that pattern, because they all read the same price path.

WP-007 therefore changes the information source rather than the shape, using fields the
accepted canonical dataset already carries and that no prior family has read:
`taker_base`, `taker_quote`, `volume`, `quote_volume`.

## Economic hypothesis (exactly one)

A transition from non-dominant to dominant exchange-reported taker buying in the
just-completed 1h bar, when the most recently available non-overlapping completed 4h
context is already buy-dominant, may indicate renewed aggressive demand with enough
next-day continuation to survive BTCUSDT Spot friction.

The claim is about **who was crossing the spread**, not about where price sits relative
to a level, a mean or a prior high.

## Feature semantics, stated conservatively

`taker_buy_base_share = sum(taker_base) / sum(volume)` over a completed UTC-aligned
bucket, per `docs/contracts/ORDER_FLOW_FEATURES_V1.md`.

It is Binance's exchange-reported taker buy base asset volume share — a venue-level
proxy for aggressive buy-side participation. It is **not** market-wide order flow, not
investor intent, not signed cross-venue demand, and no correlation it shows would
establish causality.

`0.5` is the accounting balance point: taker-buy base volume equals half of total base
volume. It is read off the field's definition, not fitted. No alternate threshold is
authorized, and testing 0.51, 0.52, 0.55 or 0.60 would be numeric parameter search.

## Exact as-of context

At UTC hourly decision boundary `t`:

- current signal hour `[t-1h, t)`;
- previous signal hour `[t-2h, t-1h)`;
- 4h context: the most recent completed UTC-aligned 4h bucket whose close is at or
  before `t-1h`, i.e. opening at `floor((t-5h)/4h)*4h`.

That constraint guarantees the context **never contains the current 1h signal bar**.

Honest staleness: the context closes between 1 and 4 hours before `t`. At `t = 13:00`
the context is `[08:00, 12:00)` and is 1 hour stale; at `t = 16:00` it is the same
bucket and is 4 hours stale. The slower context is deliberately lagging — it is a
background condition, not a co-timed confirmation — and it can miss a regime change that
occurred inside the last four hours.

All three buckets must be complete, unquarantined and actually traded. Nothing is
filled, and an ineligible bucket produces no signal rather than a substituted one.

## The two frozen variants

**Variant 1 — FLOW_CORE (PRIMARY, fixed before results).** Emit LONG iff:

1. previous completed 1h `taker_buy_base_share <= 0.5`;
2. current completed 1h `taker_buy_base_share > 0.5`;
3. most recent non-overlapping completed 4h context `taker_buy_base_share > 0.5`.

No price condition whatsoever.

**Variant 2 — FLOW_PRICE_RESPONSE.** `FLOW_CORE` and
`current_completed_1h_close > current_completed_1h_open`.

Its scientific role is to test whether the flow transition is more informative when
price responded positively during the same completed hour. This is the only price
condition in the family. There is no breakout, no SMA, no persistence ratio, no volume
multiple and no pullback rule.

## Fixed geometry and profiles

Stop `reference * 0.98`, target `reference * 1.04`, maximum hold 1,440 minutes, one
active LONG position, no leverage, no SHORT. Reference price is the current completed 1h
close. Exactly four profiles per variant: `DEFAULT`, `ZERO`, `DOUBLE`, `DELAY_1H`.
Eight profile evaluations in total, zero numeric parameter variants.

## Falsification

`DEVELOPMENT_EVALUATION_V1` applied unchanged over the six exposed 2019–2024 folds. The
family conclusion follows the primary `FLOW_CORE`, never whichever variant scores
better. Even a `PROMISING_DEVELOPMENT_ONLY` outcome yields no Champion, no sealed query
and no paper trading.

## Regime attribution

This family declares no price-regime attribution. Its only slower-context condition is
already required for emission, so a regime split on it would be constant. Trades are
recorded as `UNCLASSIFIED` rather than being labelled with a regime the rule never
consults.
