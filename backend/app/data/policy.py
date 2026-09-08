from datetime import UTC, datetime

CUTOFF = datetime(2024, 12, 31, 23, 59, tzinfo=UTC)
SYMBOL = "BTCUSDT"


def require_allowed(symbol: str, end: datetime) -> None:
    if symbol != SYMBOL:
        raise ValueError("only BTCUSDT spot is permitted")
    if end.tzinfo is None or end.astimezone(UTC) > CUTOFF:
        raise ValueError("request exceeds historical development cutoff")
