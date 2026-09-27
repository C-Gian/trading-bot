# G2-01 Engineering Validation V1

Status: **EXECUTOR COMPLETE — PENDING RESEARCH DIRECTOR GATE B RE-REVIEW** (rebuilt after the B-01/B-02 corrections; see `reports/checkpoints/G2-01-GATE-B-CORRECTIONS-DATA-PREFLIGHT-V1.md`)
Evidence class: **ENGINEERING VALIDATION — NOT PERFORMANCE EVIDENCE**
Machine-readable truth: `reports/validation/G2-01-ENGINEERING-VALIDATION-V1.json` (canonical,
replayed byte-for-byte by `python scripts/build_g2_validation.py --check`, which `scripts/check.py`
runs). Verbose log: `reports/validation/G2-01-ENGINEERING-VALIDATION-V1.log`.

## What was validated

| Area | Result |
|---|---|
| Synthetic end-to-end run (262 days, frozen constants) | 25,152 eligible 15m candles → 25,152 predictions and 25,152 decisions (continuous, including unavailable) |
| Forecast states exercised | NO_MODEL, WARMUP, MISSING_DATA, FORECAST_AVAILABLE, fallback `TRAINING_TARGET_BASELINE_UNVALIDATED`, then `PREQUENTIAL_CDF_UNCALIBRATED` |
| Model support | First fit at the first monthly boundary satisfying 10,000 rows **and** 180 days (2001-08-01); earlier boundaries recorded as `UNAVAILABLE_SUPPORT` |
| Policy/risk/execution | INSUFFICIENT_POLICY_EVIDENCE until both utility archives reach 2,000 residuals / 30 days; LONG and SHORT actions, one-position blocking, expiry exits, funding events |
| Scripted injections | zero-volume candle → `FORECAST_UNAVAILABLE_MISSING_DATA`; one missing 1m kline → incomplete bars, recursive reset, re-warm |
| Determinism | repeated-run fingerprint identical; replay in 97-minute and 1-day steps identical; prefix invariance of every record at two cursors |
| Cycle checkpoint §13 | all 13 tests PASS on the G2 adapter (full-size 128/48/48-path gates) |
| Exposed engineering window | ledger `G2-01-ENG-WINDOW-001`, BTCUSDT USD-M 2024-06-03..06-10: parser parity with the frozen G1 parser, 15m/1h/4h/1d aggregation parity, minute-grid/availability semantics, 8h funding grid, prefix and replay identity; only the 2024-06 object and the ≤2024 funding artifact opened |
| Backend tests | G2 modules: features, models/distribution, policy/execution, causality/records, cycle checkpoint, data boundary, API |
| Frontend | G2 replay + Home latest-state panel; tests assert the UI displays API actions and never derives them |

## Explicit negatives

No economic market run, no cumulative return/Sharpe/profit factor/ranking, no threshold or parameter
choice, no protected 2025+ observation (the loader rejects such intervals before any I/O), no G1
rescue, no cycle activation, no paper or real orders, sealed queries 0.

The seven-day exposed window cannot satisfy the 180-day training minimum; it produced no model fit and
no economic action by construction. Its per-candle records exist only for parity checks.
