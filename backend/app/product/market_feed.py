"""Credential-free current BTCUSDT klines for the paper-research analysis path only.

Read-only public market data. No key, account, balance, order-placement or
fund-transfer surface exists here, and nothing fetched is written to the development
store.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

ENDPOINT = "https://api.binance.com/api/v3/klines"
SYMBOL = "BTCUSDT"
INTERVAL_MINUTES = {"1h": 60, "4h": 240}
HTTP_TIMEOUT_SECONDS = 15
USER_AGENT = "trading-bot-wp010a/1.0"


class MarketFeedError(RuntimeError):
    """Current market data could not be obtained completely enough to analyse."""


@dataclass(frozen=True)
class Kline:
    open_ms: int
    high: float
    low: float
    close: float
    volume: float


def _parse(rows: Any, interval: str, now_ms: int) -> tuple[Kline, ...]:
    """Keep only bars whose interval has fully closed before ``now_ms``."""
    if not isinstance(rows, list):
        raise MarketFeedError("market feed returned an unexpected payload")
    width_ms = INTERVAL_MINUTES[interval] * 60_000
    klines = []
    for row in rows:
        try:
            open_ms = int(row[0])
            high, low, close, volume = (float(row[index]) for index in (2, 3, 4, 5))
        except (TypeError, ValueError, IndexError) as exc:
            raise MarketFeedError("market feed returned a malformed kline") from exc
        if open_ms % width_ms:
            raise MarketFeedError("market feed returned an unaligned kline")
        if open_ms + width_ms > now_ms:
            continue
        klines.append(Kline(open_ms, high, low, close, volume))
    klines.sort(key=lambda kline: kline.open_ms)
    if len({kline.open_ms for kline in klines}) != len(klines):
        raise MarketFeedError("market feed returned duplicate klines")
    return tuple(klines)


def fetch_klines(
    interval: str, limit: int, *, now: datetime, client: Any = httpx
) -> tuple[Kline, ...]:
    """Fetch completed public klines. Any transport or shape problem fails closed."""
    if interval not in INTERVAL_MINUTES or not 1 <= limit <= 1000:
        raise MarketFeedError("unsupported market feed request")
    try:
        response = client.get(
            ENDPOINT,
            params={"symbol": SYMBOL, "interval": interval, "limit": str(limit)},
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise MarketFeedError(f"market feed transport failure: {exc}") from exc
    if response.status_code != 200:
        raise MarketFeedError(f"market feed returned status {response.status_code}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise MarketFeedError("market feed returned non-JSON content") from exc
    return _parse(payload, interval, int(now.astimezone(UTC).timestamp() * 1000))
