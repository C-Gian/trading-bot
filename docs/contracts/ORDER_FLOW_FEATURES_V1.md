# Order-flow features V1

Status: active for WP-007 onward. Canonical data is never modified by this contract.

## What the fields are

The accepted canonical 1m Parquet carries four exchange-reported volume fields per
minute, exactly as published in the official Binance Spot monthly kline archives:

- `volume` — total base asset volume;
- `quote_volume` — total quote asset volume;
- `taker_base` — taker **buy** base asset volume;
- `taker_quote` — taker **buy** quote asset volume.

`taker_base` is the portion of `volume` in which the buyer was the aggressor, i.e. the
buy side crossed the spread. The remainder, `volume - taker_base`, is the portion in
which the seller was the aggressor.

## What the derived feature means

The single derived feature this contract authorizes is

```
taker_buy_base_share = sum(taker_base) / sum(volume)
```

over a completed UTC-aligned bucket, undefined (null) when the denominator is zero.

It is **Binance's exchange-reported taker buy base asset volume share** — a proxy for
aggressive buy-side participation on that one venue.

It is explicitly **not**:

- complete market-wide order flow;
- investor intent or conviction;
- signed net demand across exchanges;
- evidence of causality, however strong a correlation may look.

Any interpretation that goes beyond "on this venue, in this completed interval, this
fraction of traded base volume was buyer-aggressed" is unsupported.

## The 0.5 balance point

`0.5` is the accounting balance point: taker-buy base volume equals exactly half of
total base volume, so aggressive buying and aggressive selling contributed equally.

It is chosen from the definition of the field, not fitted to returns. No alternate
threshold is authorized. Testing 0.51, 0.52, 0.55 or 0.60 would be numeric parameter
search and is forbidden.

## Aggregation rules

A bucket's share is the **ratio of summed taker volume to summed total volume**, never
the mean of minute-level ratios. Minute ratios are undefined for zero-volume minutes
and would weight a one-trade minute equally with a heavy one.

For every UTC-aligned bucket the substrate records:

- `source_minutes` — how many canonical 1m rows fall in the bucket;
- `complete` — `source_minutes` equals the bucket width in minutes (60 or 240);
- `volume`, `quote_volume`, `taker_base`, `taker_quote` — sums;
- `taker_buy_base_share` — the ratio above, or null when `volume == 0`;
- `quarantined` — the bucket is touched by a known off-grid source interval;
- `eligible` — `complete and not quarantined and taker_buy_base_share is not null`.

Incomplete, quarantined and zero-volume buckets are **ineligible**. Nothing is filled,
interpolated, clamped or repaired. A missing minute stays missing.

## Integrity gate

No order-flow market experiment may run until
`reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json` reports `PASS`. The audit covers
every canonical 1m row and verifies:

- the canonical byte hash and row count match the accepted manifest;
- the maximum open time is at or before the development cutoff, with zero post-cutoff
  rows and no post-cutoff bytes read;
- all four fields are finite and non-negative;
- `taker_base <= volume` and `taker_quote <= quote_volume`, reported both exactly and
  against a documented float-parity tolerance of `1e-9` absolute plus `1e-12` relative;
- zero-volume and zero-quote-volume row counts;
- zero-volume rows carry zero taker volume;
- no taker ratio falls outside `[0, 1]` — and a violation would be **counted and
  reported, never clamped**;
- timestamps remain strictly increasing and unique;
- missing minutes match the accepted manifest and remain unfilled;
- the WP-004 source-grid quarantine reproduces exactly.

If material violations exist, the counts and examples are preserved, no order-flow
market experiment runs, the research stage is `PARTIAL`, and the accepted canonical
dataset is left untouched.

## Source provenance sample

The flow fields are independently re-verified against the immutable raw Binance
archives. The selection rule is frozen before inspection and uses **only** archive
labels and row counts — never a market value, and never an outcome:

- one deterministic minute per calendar quarter with available raw data, the month and
  the row index both chosen by SHA-256 of the rule identity and the quarter label;
- **every** off-grid row in both known anomaly archives (`2017-12`, `2018-02`).

Comparison uses the same parsing semantics as acquisition — Python `float()` applied to
the raw CSV text — so a mismatch means a real pipeline defect rather than a formatting
difference. No third-party data is used.

## Derived substrate identity

The derived buckets live in a separate versioned substrate,
`BTCUSDT-SPOT-ORDERFLOW-DEV-v1`, with its own tracked manifest under `data/manifests/`.
The canonical dataset and its manifest are unchanged.

A production feature builder and an independent oracle that shares no aggregation code
must reconcile exactly — bucket counts, eligible counts, sampled values, edge buckets,
anomaly buckets and content hashes — before any market result is produced.
