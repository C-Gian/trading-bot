# G2-01 Causal Trader Vertical Slice V1 — Executor Checkpoint

Status: **EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_GATE_B_REVIEW**
Executor: Claude Code (overflow executor) · Date: 2026-09-27
Package: `tasks/G2_01_IMPLEMENTATION_PACKAGE_V1.md` · Evidence: `reports/validation/G2-01-ENGINEERING-VALIDATION-V1.{json,md,log}`

G2-01 is engineering/causal validation only. Nothing here says anything about G2 profitability.
Validated strategy NONE · Champion NONE · operational action NO_TRADE · real money false.

## Delivered

- `backend/app/g2/` — authoritative G2-V0 implementation: `contract` (frozen constants),
  `bars` (causal 1m tape, completed 3m/15m/1h/4h/D/W bars), `features` (exact eight columns,
  SIGMA_4H, PRICE_RESPONSE, ATR14, Daily/Weekly display), `models` (train-only median/MAD, clip ±8,
  fixed-penalty ridge, monthly fit, 730/180-day and 10,000-row support), `distribution`
  (version-keyed prequential archives, causal fallback, q10/q50/q90, p_positive), `execution`
  (shadow geometry, stops/gaps, expiry, adverse friction, settled funding), `risk` (0.25% stop-risk
  sizing, 1.0x cap, filters, one position, 5% path-drawdown lock), `cycle` (shadow adapter on the
  unchanged G1 ACP + amplitude/stability), `store`/`records` (immutable, append-only, canonical
  hashes), `core` (state machine), `sources` (phase-bounded loader), `runs`/`service`/`api`
  (`/api/v1/g2`), `cycle_checkpoint`, `validation`.
- Frontend: Replay page now opens G2-V0 (G1 kept as a tab); Dashboard has an explicit-load G2
  latest-state panel. All G2 surfaces are labelled NOT PERFORMANCE EVIDENCE; cycle marked SHADOW.
- Tests: `backend/tests/test_g2_*.py` (features, models/distribution, policy/execution,
  causality/records, cycle checkpoint, data boundary, API) and `frontend/src/G2Replay.test.tsx`.
- Validation: `scripts/build_g2_validation.py` (write / `--check`), wired into `scripts/check.py`.
- Ledger: `G2-01-ENG-WINDOW-001` (declared before any observation read), `G2-01-CHECKPOINT-001`.

## Gate B criteria — executor evidence

| # | Criterion | Evidence |
|---|---|---|
| 1 | deterministic causal/integrity tests pass | pytest G2 suite; `check.py` green |
| 2 | frozen contract parity | hand-calculated feature fixtures; ridge vs augmented least squares; exact geometry/friction/funding tests; `frozen_contract_identity` in artifact |
| 3 | no protected outcomes touched | loader rejects 2025+ before I/O; artifact `protected_objects_opened=false` |
| 4 | exposed window engineering-only | ledger declaration; artifact has no economic output; 0 fits, 0 actions |
| 5 | continuous predictions | 25,152 / 25,152 candles |
| 6 | NO_TRADE/reason semantics | all canonical codes exercised; unit tests per veto |
| 7 | reproducible/inspectable records | fingerprint identity, prefix invariance, lineage API |
| 8 | cycle method disposition | 13/13 checkpoint tests pass — classification is the Research Director's |
| 9 | replay/API from one core | API output equals core records (test); replay = causal projection of the core's immutable log |
| 10 | full validation green | `python scripts/check.py` |

## Implementation conventions for Research Director review

Where the frozen text is silent, the executor chose the conservative reading below. None was selected
by looking at outcomes; each is a candidate for explicit ratification or correction.

1. Shadow labels and utility residuals become available uniformly at T+4h+1m (close of the exact
   expiry bar), even when the stop was hit earlier; utility training uses that maturity instant.
2. The LONG/SHORT utility heads reuse the forecast fit's training-only scaler of the same boundary
   ("exactly the same eight standardized columns").
3. Training "calendar span" = last minus first admitted decision time ≥ 180 days.
4. Empirical quantiles use numpy's default linear interpolation (Hyndman-Fan type 7).
5. Funding applies to settlements F with entry_time < F ≤ exit_time; a missing price proxy is charged
   adversely at the last known price and flagged; an expected 8h settlement without a record is
   flagged `FUNDING_DATA_INVALID` (shadow label unavailable).
6. The live stop is rounded to the tick toward the entry (risk never above plan); quantity floors to
   the step. A decision-time filter pre-check uses P(T); the fill re-checks with the raw entry.
7. The 5% path drawdown is measured on 1m-close marks (no exit friction in the mark); an open
   position is kept to its stop/expiry after the lock.
8. A missing expiry bar closes a live trade at the next available open with
   `EXECUTION_EXIT_DATA_MISSING`; a shadow label with any missing path minute is unavailable.
9. A state term requires the latest completed 1h/4h bar to end at floor(T); otherwise MISSING_DATA.
10. ATR14 eligibility is its 14-TR seed (Wilder is not declared as an EWM half-life).
11. Additive-noise abstention is required in aggregate: 1w showed ~100% USABLE occupancy, matching the
    checkpoint's own reference (1.000); all other occupancies track the reference closely.

## Observations (no action taken)

- Any single missing 1m kline makes the containing 15m/1h/4h bars incomplete and resets the recursive
  state; CONTEXT_STRUCTURE then needs 96 completed 4h bars (16 days) to re-warm. Real 2020-2024
  minute gaps may therefore remove material coverage in G2-02; the gap census should be measured
  before economic development.
- The exposed window used placeholder filters (no economic action possible). G2-02 needs a pinned
  exchangeInfo snapshot per the data manifest §11.

## Repository validation repairs (engineering, no scientific change)

`scripts/check.py` and 7 tests were already failing at the G2-00 HEAD. Repairs: schema allows the
recorded `system_g1_development.selected_configuration: null`; validators read ADR-0053-compacted
documents at the preserved pre-cleanup Git revision (`app/historical_docs.py`); the top-level G1
pointers are validated as frozen historical fields under G2; the fail-closed live-state test and
successor-title lists recognize G2; `state/current_state.json` is serialized ASCII-escaped again (no
value change). G1 results, artifacts and gates are unchanged (their `--check` replays pass).

## Not done / out of scope

No G2-02, no economic development, no cycle activation, no change to `validated_strategy`, no paper
trading. Gate B and cycle classification (`AVAILABLE_FOR_RESERVED_REVISION` or not) are Research
Director decisions.
