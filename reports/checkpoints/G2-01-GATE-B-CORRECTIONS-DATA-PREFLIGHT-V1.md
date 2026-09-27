# G2-01 Gate B Corrections and Data Preflight V1 — Executor Checkpoint

Status: **EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_GATE_B_REREVIEW**
Executor: Claude Code (overflow) · Task: `tasks/G2_01_GATE_B_CORRECTIONS_AND_DATA_PREFLIGHT_V1.md`
Review addressed: `reports/reviews/G2-01-GATE-B-RESEARCH-DIRECTOR-REVIEW-V1.md`

Engineering correction only: no scientific revision, zero G2 development slots consumed, no G2
economic run, no protected 2025+ observation. Validated strategy NONE · Champion NONE · NO_TRADE.

## B-01 — Risk-state freshness

- `RiskStateEvent` now records `equity` (realized), `marked_equity` and `mark_basis`, all after the
  event at its own availability instant.
- ENTRY: post-entry friction; marked at the fill price (`ENTRY_FILL_PRICE`).
- FUNDING: post-funding equity re-marked at the settlement price proxy; if funding alone crosses the
  5% path drawdown, `DRAWDOWN_STOP_TRIGGERED` and the lock occur at the same instant, and the
  decision at that instant carries `PATH_DRAWDOWN_STOP_ACTIVE`.
- EXIT: flat post-exit state, equity after exit friction (`FLAT_AFTER_EXIT`).
- Thresholds, sizing, stops, expiry and policy are unchanged. In the synthetic run the actions and
  trades are identical to the reviewed commit; only record content (and so the fingerprint) changed.

## B-02 — `RiskSnapshot.position_open`

It now means an actual open trade. ENTRY_PENDING stays in `Decision.position_state` (still blocked by
`POSITION_ALREADY_OPEN`). `RiskSnapshot` also exposes `marked_equity`.

## B-03 — Ledger provenance

`G2-01-PROVENANCE-QUALIFICATION-001` appended (originals untouched) with the actual UTC clock;
the preflight declaration `G2-02-DATA-PREFLIGHT-DECLARATION-001` and this checkpoint's completion
record also use actual timezone-aware UTC timestamps.

## Exposed-data integrity preflight (2020-2024)

`reports/validation/G2-02-DATA-INTEGRITY-PREFLIGHT-V1.{json,md}`: all 60 manifest objects present
and read; 2,630,880 / 2,630,880 valid minutes; no missing, duplicate, out-of-order or off-grid rows;
no incomplete 15m/1h/4h bar; frozen-state unavailability 1,551 decisions (1,535 initial warm-up;
16 after warm-up, all zero-volume candles); 4h context re-warm loss 0; funding 5,481 / 5,481 expected
8h settlements, none missing/duplicated/off-grid → the 8h grid assumption is valid for 2020-2024.
Observation: 332 zero-volume minutes may be venue placeholders (see the report).

## Pinned contract filters

`data/manifests/BTCUSDT-USDM-EXCHANGEINFO-SNAPSHOT-V1.json` from
`https://fapi.binance.com/fapi/v1/exchangeInfo` (credential-free), retrieval
2026-09-27T19:29:54Z, raw SHA-256 `4964a8bc…a635`: PERPETUAL / TRADING, tickSize 0.10,
LOT_SIZE step 0.001 / min 0.001 / max 1000, MARKET_LOT_SIZE step 0.001 / min 0.001 / max 120,
MIN_NOTIONAL 50. Filters come from the filter objects only (`pinned_market_filters`, hash-verified).
Note: the response `serverTime` (≈19:15Z) predates the retrieval time, consistent with upstream
caching; both values are recorded unmodified. The full raw response is kept locally
(git-ignored) under `data/raw/binance/exchangeinfo/`.

## Validation

New tests: `test_g2_preflight_filters.py` and B-01/B-02 cases in `test_g2_policy_execution.py`.
G2 validation artifact rebuilt (status, cycle classification recorded as the Research Director's
`AVAILABLE_FOR_RESERVED_REVISION`, code identities). `scripts/check.py` runs both replays.

Gate B remains a Research Director decision; G2-02 is not opened; cycle stays SHADOW_ONLY.
