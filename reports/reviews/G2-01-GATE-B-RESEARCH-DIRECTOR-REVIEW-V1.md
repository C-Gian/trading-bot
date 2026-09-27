# G2-01 Gate B — Research Director Review V1

Status: **CORRECTION REQUIRED BEFORE GATE B PASS**  
Date: 2026-09-27  
Reviewed commit: `c5cf3475ea49d063261bd7de1ec6c23f89573a93`

## Overall finding

The G2-01 implementation is substantially successful.

The frozen G2-V0 architecture is implemented as a distinct causal engine; the validation artifact
shows deterministic replay, continuous prediction/decision records, phase-bounded exposed-data
access, no protected-data access, no G2 economic market run, and all 13 cycle-method tests passing.

No evidence of G1 rescue, parameter tuning, protected-outcome inspection, paper orders or real-money
activation was found.

Gate B is **not rejected**. It remains pending while a small bounded engineering correction package
is completed.

## Findings that pass review

PASS:
- exact eight-column G2-V0 dictionary;
- completed-bar causal state and prefix invariance;
- train-only robust scaling and fixed-penalty ridge;
- monthly causal refits with mature-label exclusion;
- empirical fallback/prequential predictive distribution;
- separate LONG/SHORT utility heads;
- prudential-margin selection independent of terminal forecast direction;
- one-position/risk/execution architecture;
- adverse historical friction and funding accounting structure;
- immutable append-only event lineage;
- causal replay/API projection from the same authoritative core;
- phase-bounded loader refusing 2025+ observation access before I/O;
- seven-day 2024 engineering window used without fit, trade or economic output;
- historical G1 validation repairs preserve prior scientific artifacts through Git history.

## Cycle adjudication

All 13 required G2 cycle method tests pass, including exact G1/G2 tracker parity, white-noise,
coherent-cycle, noisy-cycle, trend, jump, prefix, reset, amplitude, stability, turn-confirmation
and replay-speed checks.

Research Director classification:

`CYCLE-CAUSALITY-01 = AVAILABLE_FOR_RESERVED_REVISION`

This means only that the method is technically eligible for the single reserved `G2-RCYCLE`
development slot.

It does **not** activate cycle terms in G2-V0 and does not establish predictive utility.

## Ratification of executor conventions

The 11 executor conventions are adjudicated as follows.

1. **RATIFIED** — shadow/utility labels becoming visible at T+4h+1m is a conservative historical
   availability convention consistent with minute-bar availability.
2. **RATIFIED** — utility heads reuse the forecast fit's training-only scaler at the same boundary.
3. **RATIFIED** — 180-day support span means last admitted decision time minus first admitted
   decision time >= 180 days.
4. **RATIFIED** — empirical quantiles use NumPy linear/type-7 interpolation.
5. **RATIFIED WITH QUALIFICATION** — funding applies for entry_time < F <= exit_time. The 8h
   expected-grid assumption must be verified over the complete exposed 2020-2024 funding artifact
   before G2-02. Any `FUNDING_DATA_INVALID` record is operationally preserved but cannot silently
   contribute as valid primary economic evidence.
6. **RATIFIED** — quantity floors to step and stop rounds toward entry, never increasing planned
   stop risk.
7. **RATIFIED** — path drawdown uses marked account equity at 1m closes; hypothetical future exit
   friction is not deducted until actually incurred. Open positions are not force-closed merely
   because the new-entry drawdown lock activates.
8. **RATIFIED WITH QUALIFICATION** — a live simulated position may be operationally closed at the
   first available open after a missing exact expiry bar, but the trade carries
   `EXECUTION_EXIT_DATA_MISSING` and must not be silently treated as a clean primary-economic
   observation in G2-02. Shadow labels remain unavailable.
9. **RATIFIED** — required 1h/4h state must end at the exact completed boundary; stale context fails
   closed.
10. **RATIFIED** — ATR14 becomes eligible after the first 14 valid true ranges under Wilder seeding.
11. **RATIFIED** — the additive-noise checkpoint requires finite/explicit quality behavior plus
   observed aggregate abstention, not abstention on every scale; the frozen 1w reference itself has
   approximately 100% usable occupancy.

These ratifications clarify previously silent implementation details before any G2 economic result
exists. They consume no scientific revision slot.

## Corrections required before Gate B pass

### B-01 — Risk-state event freshness

`RiskStateEvent` can be emitted immediately after ENTRY/FUNDING/EXIT while the governor's marked
equity/drawdown still reflects the preceding mark update.

Correct the event semantics so each risk event describes the post-event risk state at its own
availability instant.

Requirements:
- explicit marked equity must be inspectable in risk records;
- funding that crosses the 5% drawdown boundary must activate the lock at that same availability
  instant, not one minute later;
- ENTRY/EXIT/FUNDING risk events must be internally consistent with equity, peak, drawdown and
  actual position state;
- no scientific threshold or sizing rule changes.

### B-02 — Decision risk flag semantics

`RiskSnapshot.position_open` must mean an actual open trade. It must not mean "open or
entry-pending"; `Decision.position_state` already carries FLAT/ENTRY_PENDING/OPEN semantics.

### B-03 — Ledger timestamp provenance qualification

The executor-added records `G2-01-ENG-WINDOW-001` and `G2-01-CHECKPOINT-001` contain rounded
executor wall-clock timestamps that are not independently consistent with Git commit metadata.

Do not rewrite or delete them: the ledger is append-only.

Append a provenance-qualification record stating that:
- their append order is preserved;
- their exact wall-clock values are not used as proof of preregistration timing;
- the engineering window produced zero model fits, zero economic actions and no economic output, so
  this timestamp defect does not contaminate economic evidence;
- future records use actual timezone-aware UTC timestamps rather than invented rounded times.

## Mandatory pre-G2-02 data-integrity preflight

Before the first economic development run, perform a non-economic integrity audit on exposed
2020-2024 data only.

Measure and persist:
- missing, duplicate and out-of-order 1m observations by month/year;
- longest contiguous minute gap and gap distribution;
- incomplete 15m/1h/4h bars caused by gaps;
- expected G2 decision coverage lost under the frozen re-warm rules, including the 96 completed 4h
  context re-warm;
- funding timestamp coverage, duplicates and deviations from the assumed 8h settlement grid;
- exact months/files present versus the canonical manifest.

This audit may inspect exposed data but must not fit G2 models, create economic actions, calculate
strategy returns or rank variants.

Before G2-02 also pin a current primary-source Binance USD-M `exchangeInfo` snapshot for BTCUSDT
PERPETUAL/TRADING and persist the relevant filter values plus raw snapshot hash. If primary-source
retrieval is unavailable, report BLOCKED rather than fabricating values.

## Gate decision

Current decision:

`GATE_B = PENDING_CORRECTION`

No substantive G2 revision slot is consumed.

G2-02 economic development remains forbidden until the correction package is independently reviewed
and Gate B is explicitly changed to PASS.

Validated strategy remains NONE.
Champion remains NONE.
Operational action remains NO_TRADE.
Real money remains forbidden.
