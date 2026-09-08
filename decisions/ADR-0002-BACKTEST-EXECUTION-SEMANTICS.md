# ADR-0002: Backtest execution semantics V1

Status: Accepted prospectively before strategy experimentation

The V1 research simulator is BTCUSDT Spot, long-only, without leverage, and permits one active simulated position. It uses completed 1h signals, most recently completed 4h context, next eligible 1m open entry, a 24-hour maximum hold, `STOP_FIRST_V1` for ambiguous bars, and `IGNORE_WHILE_POSITION_OPEN_V1` for overlapping signals. Gaps never receive invented fills. Costs use `BTCUSDT_SPOT_COST_V1`. These assumptions precede all market strategy experiments and may only change prospectively by version.
