# Checkpoint — IMPLEMENT-SYSTEM-G1-DEVELOPMENT-V1

Status: `SYSTEM_G1_DEVELOPMENT_IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_REVIEW`
Authority: Constitution 4.0; ADR-0046; `research/protocols/SYSTEM-G1-DEVELOPMENT-V1.md`.
Identities: `reports/validation/SYSTEM-G1-DEVELOPMENT-IMPLEMENTATION-V1.json` (protocol, decision,
code, configuration, source bindings; re-derived by `scripts/check.py`).

No real historical G1 outcome was read, no forecaster was fitted on BTC, no P1/P2 performance was
computed, no market data was fetched, no sealed query was made.

## Implemented (`backend/app/g1/`)

| Area | Module | Notes |
|---|---|---|
| Cycle activation | `cycle.py` | ADR-0046 qualifier (FAST/INTERMEDIATE/SLOW); role ACTIVE; math, labels, bands unchanged (gate replays identically; preserved artifact hash-pinned) |
| Shared indicators | `indicators.py` | 4h Wilder ADX/DI 14 (25/20), 1h EMA20/50, 15m Wilder ATR14, session VWAP (quote/base), previous-day high/low, daily EMA20 vs 3 days earlier, RVOL (prior-20 median, ≥1.20), taker imbalance sign |
| P1 / P2 | `playbooks.py` | P1 per-direction arming state machine (EMA20 touch, 4-candle window, reclaim trigger, 0.25 ATR stop, 2R); P2 excursion ≥0.25 ATR + same-candle re-entry, VWAP objective, ≥1.50R |
| Conflict / conviction / configs | `playbooks.py` | opposite → PLAYBOOK_CONFLICT; same side → larger RR, tie P1; S-full LOW/MEDIUM/HIGH; exactly seven configurations |
| Forecaster | `forecaster.py` | 96×15m prior risk, 9 cells, annual expanding training with exact 4h purge, `w=n/(n+256)`, mixture P/mean/median/q10/q90, status `..._NOT_CALIBRATED`; never gates trades |
| Engine | `development.py` | one causal pass; shared recognition/forecast; one ledger per book (7 configs; 48bp and +5m stress books); 1m primary delay; unresolved end-state closed unscorable |
| Scoring / adjudication | `scoring.py` | Phase-A eligibility + automatic selection (tie → smallest ID); Phase-B support/economic/robustness/prediction gates; frozen disposition ordering |
| Staged runner + guard | `batch.py`, `scripts/run_g1_development.py` | refuses without `system_g1_development.historical_execution_authorized` + existing decision record; Phase B only after a verified Phase-A artifact, selection re-derived from its table, write-once artifacts, no preview |
| Source bindings | `sources.py` | USD-M 1m official klines (60 objects 2020-01..2024-12; OHLC, base, quote, taker-buy base) + settled funding; spot not required; identity only |
| Replay/UI | `service.py`, `frontend/src/Replay.tsx` | two synthetic development runs (S_FULL, S0) with grouped signals, six-scale cycle + groups, MarketState, P1/P2 setups (stop/objective/RR), conviction, not-calibrated status; production stays NO_TRADE |

Synthetic tests: 155 (149 backend across the G1 suites, 6 frontend replay tests), after the ADR-0047 correction.

## Implementation choices for Director review (not specified verbatim by the protocol)

1. Missing data: a whole missing higher-timeframe bar resets that recursive indicator (normal
   re-warm); an INCOMPLETE bar also resets it, is never consumed and publishes UNAVAILABLE
   (corrected by ADR-0047, see below). VWAP is unavailable after any missing session minute. The previous-day boundary
   requires a COMPLETE previous UTC day. RVOL needs 20 contiguous COMPLETE prior candles.
2. P1 daily rule: an UNAVAILABLE daily state cannot be verified as "not opposing" and fails.
3. P1 may trigger on the arming candle (the window counts the arming candle); the trigger's
   "previous candle" must be a completed 15m candle.
4. A playbook whose plan is vetoed (P1 ATR missing; P2 VWAP missing, objective on the wrong side, or
   RR < 1.50) is a recognized base trigger for conviction but not a proposal, so it cannot create a
   PLAYBOOK_CONFLICT.
5. HIGH conviction = exactly one complete (playbook, direction) pair; two complete pairs in the same
   direction count as MEDIUM. Market state is unavailable (→ LOW) when the 15m candle is
   missing/incomplete or the 4h regime / 1h structure is UNAVAILABLE.
6. Forecaster: point forecast for the MAE gate is the mixture mean; display direction UP/DOWN/NEUTRAL
   from P(>0) vs 0.5; weighted quantile = lower inverse CDF; a training row needs an available risk
   scale and an exact terminal minute; the first engine year has no model (UNAVAILABLE).
7. Economics: P&L attributed to the UTC exit year; equity return from 10,000 at the phase start;
   positions still open at a phase end are closed at the last close as UNSCORABLE. Phase A's engine
   ends exactly at 2023-01-01T00:00Z, so no 2023 price enters selection. Phase B replays 2020-2022 for
   warm-up but only the selected configuration trades, in 2023-2024.
8. Funding stamps are floored to the minute; only 00/08/16 UTC settlements are booked.
9. Entry order expires 15 minutes after readiness + delay (the exact fill minute must exist).

Estimated batch cost: ~0.28 ms per minute → roughly 12 minutes per phase pass on this machine.

## Also changed

- Cycle-gate `--check` now verifies the preserved artifact hash and re-executes the gate, comparing
  everything except code identities / activation flag (ADR-0046 edited `cycle.py` text only).
- Checkpoint-1 scenario tests updated to the active cycle role; `CausalView` history is bounded and
  aggregation incremental (O(1) memory for multi-year runs); `Bar` carries quote and taker-buy volume.

## Correction — ADR-0047 (FIX-SYSTEM-G1-INCOMPLETE-BAR-RECURSIVE-STATE-V1)

Pre-outcome defect fixed before any execution: an INCOMPLETE aggregated bar used to publish
UNAVAILABLE while still updating the recursive indicator with its partial OHLC/close, which could
contaminate later READY values. Now, in `backend/app/g1/indicators.py`:

- 15m Wilder ATR: incomplete bar resets the ATR state, is not consumed, publishes UNAVAILABLE;
- 1h EMA20/EMA50 structure: both EMAs reset; re-seeded only from subsequent complete closes;
- 4h Wilder ADX/+DI/-DI: the entire state resets; re-warms from subsequent complete bars;
- daily context: EMA20 and its three-day lookback reset; boundary and direction UNAVAILABLE; the
  incomplete day's close/high/low are not consumed.

Unchanged: session VWAP, participation/RVOL, cycle, forecaster risk window, aggregation, every
threshold/timeframe/playbook/cost/risk rule, configurations and source bindings. Protocol hash and
configuration identity are unchanged; only the `indicators.py` code identity changed
(`reports/validation/SYSTEM-G1-DEVELOPMENT-IMPLEMENTATION-V1.json` regenerated).

Tests (`backend/tests/test_g1_incomplete_bar_fix.py`, 8): for ATR, EMA, ADX and daily context,
two histories identical before an incomplete bar with radically different partial OHLC publish
UNAVAILABLE at that bar, produce identical later state equal to a fresh indicator fed only the later
complete bars, and publish no READY value before the frozen re-warm (ATR 14, EMA 50, ADX 28 complete
4h bars, daily direction 23 days); whole-bar-gap resets retained. An integration run of the
development engine (S0 and S_FULL) with poisoned minutes inside incomplete 3m/15m/1h/4h/1d bars
yields identical decisions, market states, forecasts, fills and trades. All five contamination tests
fail against the pre-fix code.
