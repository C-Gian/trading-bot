# FUTURE_SHADOW_PAPER_EVIDENCE_V1

Version: `FUTURE_SHADOW_PAPER_EVIDENCE_V1`.

Evidence stage: `AUTOMATED_PROSPECTIVE_SHADOW_PAPER`.

Initiation mode: `AUTOMATED_RESEARCH_OBSERVER`.

Status: accepted prospectively before any automated observation or shadow trade exists.
The manual `FUTURE_PAPER_EVIDENCE_V2` contract and its durable store remain separate and
unchanged.

## Prospective decision clock

One local observer evaluates `ALIGNED_PARTICIPATION_CONTINUATION_V1` once for each new
completed UTC hourly boundary that occurs while the observer is active. Its first
eligible boundary is strictly after durable activation. It never catches up a signal
boundary that passed while the backend was stopped.

A decision must be evaluated and durably committed no later than five minutes after its
boundary. A boundary that was missed, or that cannot be recorded inside that window, is
permanently recorded as `MISSED_PROSPECTIVE_DECISION`; it can never create a later trade.
Every sound `NO_TRADE` and `LONG` decision is evidence and remains in the ledger.

## Durable LONG intent and entry

A LONG decision first commits an unarmed automated shadow intent. Only after that commit
is durable is the intent armed. Entry is the first available completed BTCUSDT one-minute
open whose timestamp is strictly later than durable intent persistence. The already
observed hourly boundary-minute open is forbidden.

Only one automated shadow intent or position may be active. A further LONG observation
is retained with status `LONG_SIGNAL_SUPPRESSED_ACTIVE_SHADOW_POSITION` but creates no
trade.

The frozen execution geometry is LONG-only spot with no leverage: 2% stop, 4% target,
1,440-minute maximum hold, `STOP_FIRST_V1` ambiguity handling, and
`BTCUSDT_SPOT_COST_V1`. Entry and exit observations are public read-only market data;
there is no credential, account, balance, or order endpoint.

## Restart and data quality

Missed decisions are never reconstructed. A pending entry interrupted by backend
downtime is closed without a fill. An already-entered prospective position may be
reconciled after restart using immutable public bars because its intent, entry, and full
execution rule were durable before those bars existed. Reconciliation preserves the
original timestamps and records restart metadata. Missing or inconsistent required bars
fail closed as a data-quality terminal state.

Observer health is stored separately from evidence. It records backend starts,
activations, heartbeats, successful market fetches, evaluated and missed boundaries,
the next expected boundary, and current errors. It never implies availability while the
app was closed.

## Scientific freeze and accounting

ALIGNED parameters, execution geometry, costs, and this observer contract are frozen
through at least 20 completed automated shadow trades. This is a minimum adaptation
boundary, not a sufficiency claim. Integrity fixes are versioned and never rewrite prior
evidence.

Automated observations are prospective evidence, not historical experiments, manual
paper evidence, Champion evidence, owner-authorized trades, or permission for real
capital. Historical accounting remains 26 completed experiments, 12 observed material
historical hypotheses, zero sealed queries, Champion `NONE`, and real money false.

The durable evidence store is `data/paper/FUTURE_SHADOW_PAPER_EVIDENCE_V1.json`. Health
is stored separately at `data/paper/PROSPECTIVE_SHADOW_OBSERVER_HEALTH_V1.json`.
