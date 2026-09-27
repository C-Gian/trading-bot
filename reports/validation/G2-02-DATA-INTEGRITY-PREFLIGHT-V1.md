# G2-02 Data Integrity Preflight V1

Status: **EXECUTED — NON-ECONOMIC**
Ledger declaration: `G2-02-DATA-PREFLIGHT-DECLARATION-001` (appended before any preflight read)
Machine-readable truth: `reports/validation/G2-02-DATA-INTEGRITY-PREFLIGHT-V1.json`
(recomputed byte-for-byte by `python scripts/build_g2_data_preflight.py --check` in data mode).

Scope: canonical BTCUSDT USD-M 1m monthly objects and the settled-funding artifact,
2020-01-01T00:00Z to 2025-01-01T00:00Z (exclusive), read through the phase-bounded loader.
No model fit, forecast scoring, action, P&L/return metric, variant comparison or 2025+ observation.

## Source objects

- Months expected / in manifest / read: 60 / 60 / 60
- Objects missing locally: 0; protected objects opened: False

## 1m grid

| Metric | Value |
|---|---|
| Expected minutes | 2,630,880 |
| Valid minutes | 2,630,880 |
| Missing minutes | 0 |
| Duplicate / out-of-order / off-grid / invalid / outside-month rows | 0 in total |
| Gap runs / longest gap | 0 / None |
| Incomplete (partial) 15m / 1h / 4h bars | 0 / 0 / 0 |
| Absent 15m / 1h / 4h windows | 0 / 0 / 0 |
| Valid zero-volume minutes by year | {'2020': 2, '2021': 59, '2022': 64, '2023': 118, '2024': 89} |

Per-month and per-year counts are in the JSON (`klines.by_month`, `klines.by_year`).

## Frozen G2-V0 state availability at 15m decision instants

| Metric | Value |
|---|---|
| Decision instants | 175,392 |
| Unavailable (all) | 1,551 (0.8843%) |
| Initial warm-up (until 2020-01-17T00:00:00+00:00) | 1,535 |
| Unavailable after initial warm-up | 16 (0.0092%), reasons {'FORECAST_UNAVAILABLE_MISSING_DATA': 16} |
| 4h context re-warm decisions after warm-up | 0 (sole cause: 0) |
| ATR14 unavailable after warm-up | 0 |

The post-warm-up unavailability comes only from 15m candles with zero base volume (taker imbalance
undefined, never zero-filled). The re-warm risk flagged at the G2-01 checkpoint does not materialize
in the canonical exposed data: the archive has no missing minute, so no recursive reset occurs.

## Funding

| Metric | Value |
|---|---|
| Records in interval / expected 8h settlements | 5481 / 5481 |
| Missing expected settlements | 0 |
| Off-grid settlements | 0 |
| Duplicate settlement minutes / exact duplicate timestamps | 0 / 0 |
| Timestamp precision | {'EXACT': 3078, 'SUB_SECOND_OFFSET': 2403} (sub-second exchange stamps map to the settlement minute) |
| Historical 8h grid assumption valid 2020-2024 | **True** |

## Observation for Research Director review (no action taken)

The archive's 332 valid zero-volume minutes (flat OHLC) may be venue placeholders during
maintenance or outage rather than traded minutes. G2-V0 treats them as valid bars under the frozen
rules; only 15m candles made entirely of zero volume become unavailable (16 decisions). Whether
zero-volume minutes need an explicit data-quality classification is a question for G2-02
governance; no rule was changed here.
