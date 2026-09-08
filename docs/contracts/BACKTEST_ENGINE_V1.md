# Backtest engine V1

`BACKTEST_ENGINE_V1` is a deterministic, event-driven research simulator for BTCUSDT Spot long intents. It consumes a frozen intent and then a continuous canonical 1m path. It supports one position; later signals are recorded as suppressed under `IGNORE_WHILE_POSITION_OPEN_V1`. No strategy logic, leverage, shorting, exchange connectivity, or order management exists.

Only completed 1h bars may trigger an intent. The decision timestamp equals the signal bar close. Context is the most recent completed 4h bar whose close is no later than that timestamp. The entry is the immediately following canonical minute open. Signal time must precede execution time. Missing required path produces an explicit invalid or unresolved outcome.

Every run identity hashes its code commit, dataset content hash, preregistration identity, versioned models, configuration, and seeds. Audit timestamps are excluded from the deterministic hash.

