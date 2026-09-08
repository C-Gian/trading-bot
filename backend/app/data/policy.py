from datetime import UTC, datetime

CUTOFF = datetime(2024, 12, 31, 23, 59, tzinfo=UTC)
SYMBOL = "BTCUSDT"


def parse_utc_instant(value: str | datetime) -> datetime:
    try:
        instant = datetime.fromisoformat(value) if isinstance(value, str) else value
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if instant.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return instant.astimezone(UTC)


def require_allowed(symbol: str, end: datetime) -> None:
    if symbol != SYMBOL:
        raise ValueError("only BTCUSDT spot is permitted")
    if parse_utc_instant(end) > CUTOFF:
        raise ValueError("request exceeds historical development cutoff")
