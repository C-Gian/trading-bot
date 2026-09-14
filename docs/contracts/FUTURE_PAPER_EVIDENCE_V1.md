# FUTURE_PAPER_EVIDENCE_V1

Version: `FUTURE_PAPER_EVIDENCE_V1`.

Status: accepted prospectively before any paper trade exists.

Current safety gate: `BLOCKED_CAUSAL_ENTRY_TIMING_V1`. PROJECT-RETROSPECTIVE-V1 found
that the manual analysis request occurs after the boundary minute whose open this V1
would record as its prospective entry. Production creation is therefore disabled. No
paper trade exists and no evidence was contaminated. Restoring creation requires a new,
versioned causal entry contract; this V1's historical definition is not silently changed.

## Scope

This contract governs prospective BTCUSDT spot paper-research trades produced by the
local product analysis surface. It creates forward records only. It authorizes no real
capital, no exchange order, no credential, no leverage and no SHORT.

## Separation from development research

Paper records under this contract are a **different evidence class** from development
backtests and must never be merged with them.

- Development experiments use the frozen historical dataset through
  `2024-12-31T23:59:00Z` and are recorded under `research/experiments/`.
- Paper records use current public market data after that cutoff and are recorded under
  `data/paper/PAPER_TRADES_V1.json`.
- A paper record is never an input to a development experiment, a model fit, a
  parameter choice, a threshold, a feature, a historical report, or sealed evaluation.
- A development result never retroactively edits a paper record.

The strategy under observation is `ALIGNED_PARTICIPATION_CONTINUATION_V1:ALIGNED`. It is
a `PAPER_RESEARCH_CANDIDATE`. It is **not** a Champion, and recording paper trades does
not promote it.

## Counter discipline

`paper_trades_completed` in `state/current_state.json` counts **Owner-reviewed genuine
forward evidence only**.

It is not incremented by implementing this feature, by running tests, by fixtures, or
by any record created in a test store. A locally recorded trade becomes a counted paper
trade only through an explicit later review checkpoint.

## Lifecycle

One analysis produces at most one paper trade, identified by the deterministic
`analysis_id` of the evaluated signal. At most one trade may be `PENDING_ENTRY` or
`OPEN` at any time.

Statuses:

- `PENDING_ENTRY` — created from a LONG analysis; the entry minute has not resolved.
- `OPEN` — entered; no exit condition has resolved on complete data.
- `CLOSED_TARGET` — the frozen execution model resolved the target.
- `CLOSED_STOP` — the frozen execution model resolved the stop, including a gap open
  below the stop.
- `CLOSED_EXPIRY` — the 1,440 minute maximum hold elapsed.
- `INVALIDATED` — the entry minute is absent from public data, or the intent is
  non-tradable.

Terminal statuses are immutable. A later update never reopens or rewrites them.

## Execution semantics

Entry and exit are resolved by `PROSPECTIVE_PAPER_EXECUTION_V1` under
`BTCUSDT_SPOT_COST_V1`, on real current timestamps.

The frozen historical simulator `BACKTEST_ENGINE_V2` correctly refuses clocks after the
development cutoff, and it stays unmodified and cutoff-protected. Forward paper evidence
therefore uses a separate prospective adapter rather than translating post-cutoff
instants onto a historical anchor. The adapter reproduces `EXECUTION_MODEL_V2` exactly;
`backend/tests/test_prospective_execution.py` runs both implementations over identical
pre-cutoff fixtures covering entry, target, stop, adverse gap open, open above target,
ambiguous fill, expiry, data gap, end of data and missing entry bar, under the DEFAULT
and DOUBLE cost profiles, and requires every trade-record field to agree apart from the
two version labels.

The prospective adapter is never used to produce development evidence, and no research
or backtest module may import it.

Rules held identical:

- Entry at `NEXT_1M_OPEN_EXECUTION` — the first 1m open at or after the signal hour,
  plus adverse entry friction.
- An open below the stop exits at that adverse open; a low touching the stop exits at
  the stop.
- A high touching the target exits at the target; an open above the target still fills
  at the target, never at a better price.
- A minute touching both the stop and the target resolves `STOP_FIRST_V1`.
- Expiry exits at the close of the minute reaching the horizon.

## Data integrity

Lifecycle updates read public credential-free BTCUSDT market data only.

Missing or non-consecutive minutes never manufacture an outcome. An incomplete path
leaves the trade `OPEN` with an explicit unresolved reason recorded. No price, fill or
return is interpolated, inferred or filled forward.

Updates run only on an explicit API call. Nothing advances in the background or on
application startup.

An update is deterministic and idempotent: the same stored trade and the same observed
minutes always produce the same record, and re-running it changes nothing.

## Prohibited

Real capital, exchange orders, API keys, account or balance endpoints, withdrawals,
leverage, SHORT, asset universe expansion, and any automatic promotion to Champion.

Paper success is not permission for live capital. Any real-capital transition requires
a separate explicit Owner gate.
