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
INTERVAL_MINUTES = {"1m": 1, "1h": 60, "4h": 240}
HTTP_TIMEOUT_SECONDS = 15
MAX_LIMIT = 1000
MAX_RANGE_REQUESTS = 4
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
    open: float = 0.0


def _parse(rows: Any, interval: str, now_ms: int) -> tuple[Kline, ...]:
    """Keep only bars whose interval has fully closed before ``now_ms``."""
    if not isinstance(rows, list):
        raise MarketFeedError("market feed returned an unexpected payload")
    width_ms = INTERVAL_MINUTES[interval] * 60_000
    klines = []
    for row in rows:
        try:
            open_ms = int(row[0])
            opened, high, low, close, volume = (float(row[index]) for index in (1, 2, 3, 4, 5))
        except (TypeError, ValueError, IndexError) as exc:
            raise MarketFeedError("market feed returned a malformed kline") from exc
        if open_ms % width_ms:
            raise MarketFeedError("market feed returned an unaligned kline")
        if open_ms + width_ms > now_ms:
            continue
        klines.append(Kline(open_ms, high, low, close, volume, opened))
    klines.sort(key=lambda kline: kline.open_ms)
    if len({kline.open_ms for kline in klines}) != len(klines):
        raise MarketFeedError("market feed returned duplicate klines")
    return tuple(klines)


def fetch_klines(
    interval: str,
    limit: int,
    *,
    now: datetime,
    client: Any = httpx,
    start_ms: int | None = None,
) -> tuple[Kline, ...]:
    """Fetch completed public klines. Any transport or shape problem fails closed."""
    if interval not in INTERVAL_MINUTES or not 1 <= limit <= MAX_LIMIT:
        raise MarketFeedError("unsupported market feed request")
    params = {"symbol": SYMBOL, "interval": interval, "limit": str(limit)}
    if start_ms is not None:
        params["startTime"] = str(start_ms)
    try:
        response = client.get(
            ENDPOINT,
            params=params,
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


def fetch_minutes(
    start_ms: int, count: int, *, now: datetime, client: Any = httpx, feed: Any = None
) -> tuple[Kline, ...]:
    """Completed 1m klines from ``start_ms``, over a bounded number of paged requests."""
    if count < 1 or count > MAX_LIMIT * MAX_RANGE_REQUESTS:
        raise MarketFeedError("unsupported minute range request")
    fetch = feed or fetch_klines
    collected: dict[int, Kline] = {}
    cursor = start_ms
    for _ in range(MAX_RANGE_REQUESTS):
        remaining = count - len(collected)
        if remaining <= 0:
            break
        page = fetch("1m", min(MAX_LIMIT, remaining), now=now, client=client, start_ms=cursor)
        fresh = [kline for kline in page if kline.open_ms >= start_ms]
        if not fresh:
            break
        for kline in fresh:
            collected[kline.open_ms] = kline
        cursor = max(kline.open_ms for kline in fresh) + 60_000
    return tuple(sorted(collected.values(), key=lambda kline: kline.open_ms))


CURRENT_MARKET_CLASSIFICATION = "CURRENT PUBLIC MARKET DATA — READ ONLY"


def recent_candles(
    limit: int = 200,
    *,
    interval: str = "1h",
    now: datetime | None = None,
    client: Any = httpx,
    feed: Any = None,
) -> dict[str, Any]:
    """Completed current candles for the local chart. Read-only, never persisted."""
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    fetch = feed or fetch_klines
    try:
        klines = fetch(interval, max(1, min(limit, MAX_LIMIT)), now=moment, client=client)
    except MarketFeedError as exc:
        return {
            "classification": CURRENT_MARKET_CLASSIFICATION,
            "symbol": SYMBOL,
            "interval": interval,
            "status": "MARKET_DATA_UNAVAILABLE",
            "detail": str(exc),
            "candles": [],
        }
    return {
        "classification": CURRENT_MARKET_CLASSIFICATION,
        "symbol": SYMBOL,
        "interval": interval,
        "status": "OK",
        "detail": f"{len(klines)} completed {interval} candles",
        "candles": [
            {
                "open_time": datetime.fromtimestamp(kline.open_ms / 1000, UTC)
                .isoformat()
                .replace("+00:00", "Z"),
                "open": kline.open,
                "high": kline.high,
                "low": kline.low,
                "close": kline.close,
            }
            for kline in klines
        ],
    }
