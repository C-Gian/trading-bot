# Execution model V1

Version: `EXECUTION_MODEL_V1`

- Scope: BTCUSDT Spot, LONG or no entry, no leverage, one open simulated position.
- Entry: after a completed UTC-aligned 1h signal bar, at the next consecutive 1m open plus adverse entry friction. A missing next minute is `INVALID_MISSING_ENTRY_BAR`.
- Stop: an open below stop exits at that adverse open; otherwise a low touching stop exits at stop. Adverse exit friction then reduces proceeds.
- Target: a high touching target exits at target. An open above target still fills at the target, avoiding favorable price improvement.
- Ambiguity: a minute touching stop and target resolves `STOP_FIRST_V1`.
- Expiry: exit at the close of the minute whose close reaches the configured horizon, with adverse exit friction.
- Gaps: any non-consecutive minute while open is `UNRESOLVED_DATA_GAP`; no row is filled or path ordering inferred.
- End of data: `UNRESOLVED_END_OF_DATA`, without numeric return.
- Maximum hold: exactly 1,440 minutes. Longer requests and non-positive initial risk are rejected.

