from datetime import datetime
from pathlib import Path

import pyarrow.dataset as ds

from .policy import require_allowed

ROOT = Path(__file__).resolve().parents[3]
FILES = {
    "1m": ROOT / "data/canonical/BTCUSDT-1m.parquet",
    "1h": ROOT / "data/derived/BTCUSDT-1h.parquet",
    "4h": ROOT / "data/derived/BTCUSDT-4h.parquet",
}


def candles(symbol: str, timeframe: str, start: datetime, end: datetime, limit: int):
    require_allowed(symbol, end)
    if timeframe not in FILES or not 1 <= limit <= 5000 or start > end:
        raise ValueError("invalid timeframe, range, or limit")
    table = ds.dataset(FILES[timeframe], format="parquet").to_table(
        filter=(ds.field("open_time") >= start) & (ds.field("open_time") <= end)
    )
    if timeframe in {"1h", "4h"}:
        table = table.filter(table["complete"])
    return table.slice(0, limit).to_pylist()


def available():
    return FILES["1m"].exists()
