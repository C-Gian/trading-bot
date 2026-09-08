# Backtest engine V2

At UTC hour boundary `t`, the completed 1h bar `[t-1h,t)` becomes visible, the strategy decision is frozen, and only then may the canonical minute opening at `t` execute it. The events share a timestamp but are ordered `BAR_CLOSE -> SIGNAL_DECISION -> NEXT_1M_OPEN_EXECUTION`.

The engine independently requires timezone-aware UTC hourly signal instants and rejects path bars after the development cutoff. Inputs are BTCUSDT Spot, long-only, unlevered, one position at a time. Missing execution/path data remains invalid or unresolved without invented fills. Every record carries engine/execution/cost versions and deterministic identity.

