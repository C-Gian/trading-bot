# WP-007 — canonical taker-field integrity audit

DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE. No canonical data was
modified. No post-cutoff byte was read. No third-party data was used.

Machine-readable artifact: `reports/validation/WP-007-ORDER-FLOW-INTEGRITY.json`.
Contract: `docs/contracts/ORDER_FLOW_FEATURES_V1.md`.

## Verdict

**PASS** — 0 material violations across all 3,870,559 canonical 1m rows.

The four exchange-reported flow fields are therefore admissible as a feature substrate.
This is a data-integrity verdict only; it says nothing about whether the fields carry
economic information.

## Dataset identity

- manifest `BTCUSDT-SPOT-1M-DEV-v1`, content hash `02168b73…`
- canonical byte hash matches the accepted manifest exactly
- 3,870,559 rows, matching the accepted row count
- maximum open time `2024-12-31T23:59:00Z`, exactly the development cutoff
- 0 post-cutoff rows; 0 post-cutoff bytes read

## Field validity, every row

| Check | Result |
|---|---|
| finite `volume`, `quote_volume`, `taker_base`, `taker_quote` | all true |
| negative values, any field | 0 |
| `taker_base > volume`, exact | 0 |
| `taker_base > volume`, beyond tolerance | 0 |
| `taker_quote > quote_volume`, exact | 0 |
| `taker_quote > quote_volume`, beyond tolerance | 0 |
| maximum base excess | 0.0 |
| maximum quote excess | 0.0 |
| taker ratio outside `[0, 1]` on traded rows | 0 |
| ratios clamped or repaired | 0 |
| zero-volume rows | 24,003 |
| zero-quote-volume rows | 24,003 |
| zero-volume rows carrying non-zero taker volume | 0 |
| tradable rows (`volume > 0`) | 3,846,556 |

The containment tolerance is documented as `1e-9` absolute plus `1e-12` relative.
Both sides of each identity are independent decimal strings parsed by the acquisition
script's `float()`, and correct rounding is monotone, so an exact violation would have
indicated a real source or pipeline defect rather than a formatting artifact. There
were none, at either strictness.

The 24,003 zero-volume minutes are genuine no-trade minutes: each carries zero taker
volume too, so no ratio is fabricated for them. They are ineligible by definition
rather than by repair.

## Timestamps, gaps and quarantine

- strictly increasing and unique: true
- 34 gap intervals covering 8,560 missing minutes, matching the accepted manifest
- missing minutes remain **unfilled**; nothing is interpolated
- 1 sub-minute interval exists inside the known off-grid anomaly and is quarantined
  rather than treated as a negative gap
- the WP-004 source-grid quarantine reproduces exactly: 21,602 off-grid rows, 363
  quarantined 1h buckets, 92 quarantined 4h buckets, 0 repairs or fills

## Source provenance sample

The selection rule `WP007-ORDER-FLOW-SAMPLE-V1` was frozen before inspection and uses
only archive labels and row counts — never a market value and never an outcome. The
plan hash is recorded in the artifact so the selection cannot be retrofitted.

- 30 calendar quarters from `2017Q3` to `2024Q4`, one deterministic minute each; the
  month and the row index are both chosen by SHA-256 of the rule identity and the
  quarter label
- **every** off-grid row in both known anomaly archives (`2017-12`, `2018-02`):
  21,602 rows
- 32 archives opened in total, every one hash-verified against the accepted manifest
  before it was read

Result: **21,632 raw rows re-verified, zero field mismatches** across `volume`,
`quote_volume`, `taker_base` and `taker_quote`, using the same `float()` parsing
semantics as acquisition.

The 21,602 anomaly rows matter because they are the only interval where the source
timestamps are malformed. Their flow payloads reconcile exactly, which is consistent
with the WP-005 finding that the anomaly is a timestamp-grid property of the official
archives and not a payload defect. Those buckets remain quarantined regardless.

## What this does and does not license

It licenses building a derived order-flow feature substrate from these fields under
`ORDER_FLOW_FEATURES_V1`.

It does not license any economic claim. `taker_buy_base_share` is Binance's reported
taker buy base volume share — a venue-level proxy for aggressive buy-side
participation. It is not market-wide order flow, not investor intent, not signed
cross-venue demand, and correlation with forward returns would not establish causality.
