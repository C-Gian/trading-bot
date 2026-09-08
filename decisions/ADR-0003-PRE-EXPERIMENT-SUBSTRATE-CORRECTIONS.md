# ADR-0003: Pre-experiment substrate corrections

Status: Accepted prospectively before market experiments

At UTC hour boundary `t`, event order is `BAR_CLOSE -> SIGNAL_DECISION -> NEXT_1M_OPEN_EXECUTION`; the decision and eligible 1m open share wall-clock `t` while remaining causally ordered. V2 resolves an open below stop first, then an open at/above target at the conservative target price, then intrabar ambiguity with stop first. Strategy inputs require contiguous, complete, aligned suffixes. All cutoffs compare parsed timezone-aware UTC instants. The engine validates signal clocks and every path bar independently. Splitter train, validation, and horizon durations are positive. The production runner owns iteration over preregistered trial plans, verifies code/config content, preserves every trial, and atomically finalizes immutable records.

Versions are `BACKTEST_ENGINE_V2` and `EXECUTION_MODEL_V2`; costs remain `BTCUSDT_SPOT_COST_V1`.
