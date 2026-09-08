# Market data contract

BTCUSDT Binance Spot 1m bars use UTC open timestamps and OHLCV fields. Rows are ordered and unique, never filled, and capped at `2024-12-31T23:59:00Z`. OHLC must be internally consistent and volume non-negative. Derived 1h/4h bars use UTC-aligned closed windows; incomplete windows are explicitly flagged. Conflicts fail closed. Logical content identity is SHA-256 over canonical UTF-8 CSV rows with fixed column order.

