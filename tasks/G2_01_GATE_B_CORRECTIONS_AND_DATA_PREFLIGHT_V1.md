# G2-01 Gate B Corrections and Data Preflight V1

Status: **ENGINEERING CORRECTION ACTIVE — ECONOMIC MARKET EXECUTION FORBIDDEN**

## Authority

- `reports/reviews/G2-01-GATE-B-RESEARCH-DIRECTOR-REVIEW-V1.md`
- `tasks/G2_01_IMPLEMENTATION_PACKAGE_V1.md`
- frozen G2 Gate-A contracts

Primary executor: Codex. Claude Code may execute as overflow.

## Objective

Close the bounded Gate-B corrections identified by the Research Director and complete the
non-economic exposed-data integrity preflight required before G2-02.

This task is not a scientific revision and consumes zero G2 development slots.

## 1. Fix risk-state freshness

Correct G2 risk/event bookkeeping without changing thresholds or trading semantics.

Acceptance:
- add explicit marked-equity visibility to risk state/event records where needed;
- ENTRY risk event reflects post-entry friction and the current causal mark;
- FUNDING risk event reflects post-funding equity/mark/drawdown;
- if funding alone crosses the 5% path-drawdown threshold, the lock is active at the same
  availability instant;
- EXIT risk event reflects the post-exit flat state and incurred exit friction;
- risk records remain deterministic and immutable;
- add focused tests for all above cases.

Do not change 0.25% risk, 1x notional cap, 5% drawdown, stop/expiry or action policy.

## 2. Fix Decision RiskSnapshot.position_open

`position_open` means actual open trade only.

An entry-pending state remains represented by `Decision.position_state == ENTRY_PENDING`; do not
overload the boolean.

Add a focused regression test.

## 3. Append ledger provenance qualification

Do not edit/delete `G2-01-ENG-WINDOW-001` or `G2-01-CHECKPOINT-001`.

Append a new `PROVENANCE_QUALIFICATION` record explaining:
- exact executor wall-clock values on those two records are not trusted as independent timing proof;
- append order is retained;
- the window had zero model fits, zero economic actions and no economic output;
- no evidence-class change results;
- future ledger timestamps are actual timezone-aware UTC system timestamps.

Use the actual UTC clock at execution time; do not round/invent a future time.

## 4. Exposed-data integrity preflight — 2020-2024 only

Create deterministic artifacts:

- `reports/validation/G2-02-DATA-INTEGRITY-PREFLIGHT-V1.json`
- `reports/validation/G2-02-DATA-INTEGRITY-PREFLIGHT-V1.md`

Audit only canonical exposed BTCUSDT USD-M 1m/funding sources through 2024-12-31.

Report at least:
- manifest months expected/present/read;
- missing minutes by month/year;
- duplicate timestamps;
- out-of-order timestamps;
- longest gap;
- gap-length distribution;
- incomplete 15m/1h/4h bars;
- count/share of 15m decision times unavailable under frozen G2 continuity/re-warm rules;
- separate coverage loss attributable to 4h context re-warm;
- funding timestamps, duplicates, missing expected settlements and off-grid settlements;
- whether the historical 8h funding-grid assumption is valid for the full exposed interval.

Forbidden:
- model fitting;
- forecasts used for scoring;
- LONG/SHORT economic decisions;
- P&L/return/Sharpe/profit factor;
- variant comparison or tuning;
- protected 2025+ observations.

If required exposed source objects are missing locally, report exact missing objects and classify
preflight BLOCKED; do not silently narrow the interval.

## 5. Pin contract filters

Retrieve the current BTCUSDT USD-M primary-source `exchangeInfo` snapshot without credentials.

Persist a small versioned raw/normalized snapshot or manifest record containing:
- retrieval UTC timestamp;
- endpoint/source identity;
- BTCUSDT contractType/status;
- PRICE_FILTER tickSize;
- applicable LOT_SIZE/MARKET_LOT_SIZE step/min/max;
- applicable minimum-notional filter;
- raw snapshot SHA-256.

Never derive tick/step from precision fields.

If primary-source access fails, classify this subcheck BLOCKED. Do not use remembered values.

## 6. Validation

Update the G2 validation/checkpoint artifacts only as needed to reflect the corrected code and
preflight.

Run:
- focused new tests;
- full `python scripts/check.py` with local data mode when available;
- frontend tests/build if affected.

Do not compute G2 economic performance.

## 7. Completion state

Leave:
`EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_GATE_B_REREVIEW`

Do not mark Gate B PASS.
Do not open G2-02.
Do not activate cycle terms.
Do not change validated_strategy/Champion/NO_TRADE.
