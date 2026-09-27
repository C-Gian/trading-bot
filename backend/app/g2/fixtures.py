"""Deterministic synthetic G2 engineering fixtures (NOT market data, NOT performance evidence).

The synthetic 1m path uses a clearly non-market epoch (2001) and a seeded generator: bounded
sinusoidal drift regimes plus Gaussian minute noise, synthetic quote/taker volumes and 8-hourly synthetic
funding. Its only purpose is to exercise every G2-V0 contract path with the frozen constants:
warm-up, model support, fallback then prequential distributions, utility evidence, trades, stops,
expiry, funding, contract filters, missing data and zero-volume abstention.

Scripted engineering injections near the end of the path:
- a zero-volume 15m candle (taker imbalance V <= 0 -> unavailable, never zero);
- one missing 1m kline (incomplete higher-timeframe bars -> recursive reset and re-warm).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np

from .bars import Minute
from .risk import ExchangeFilters

FIXTURE_ID = "G2-SYNTHETIC-ENGINEERING-PATH-V1"
SEED = 20260927
START = datetime(2001, 1, 1, tzinfo=UTC)
DAYS = 262
END = START + timedelta(days=DAYS)
BASE_PRICE = 30_000.0
MINUTE_SD = 0.0006
DRIFT_REGIMES = ((5e-5, 3.1), (3e-5, 7.3))  # (per-minute amplitude, period in days)
ZERO_VOLUME_CANDLE = END - timedelta(days=4, hours=6)
MISSING_MINUTE = END - timedelta(days=2, hours=11, minutes=53)

SYNTHETIC_FILTERS = ExchangeFilters(
    source="SYNTHETIC_FAKE_FILTERS_NOT_EXCHANGEINFO",
    tick_size="0.1",
    step_size="0.001",
    min_qty="0.001",
    max_qty="1000",
    min_notional="5",
)


def drift_path(minutes: int, rng: np.random.Generator) -> np.ndarray:
    """Bounded drift regimes: two seeded-phase sinusoids (zero long-run integral)."""
    t = np.arange(minutes, dtype=float)
    phases = rng.uniform(0.0, 2 * np.pi, len(DRIFT_REGIMES))
    drift = np.zeros(minutes)
    for (amplitude, period_days), phase in zip(DRIFT_REGIMES, phases, strict=True):
        drift += amplitude * np.sin(2 * np.pi * t / (period_days * 1440.0) + phase)
    return drift


def synthetic_minutes(start: datetime = START, days: int = DAYS, seed: int = SEED) -> list[Minute]:
    rng = np.random.default_rng(seed)
    n = days * 1440
    drift = drift_path(n, rng)
    returns = drift + rng.normal(0.0, MINUTE_SD, n)
    closes = BASE_PRICE * np.exp(np.cumsum(returns))
    opens = np.concatenate([[BASE_PRICE], closes[:-1]])
    wick = np.abs(rng.normal(0.0, MINUTE_SD / 2, (2, n)))
    highs = np.maximum(opens, closes) * np.exp(wick[0])
    lows = np.minimum(opens, closes) * np.exp(-wick[1])
    volume = np.exp(rng.normal(np.log(40.0), 0.5, n))
    buy_fraction = np.clip(0.5 + 1500.0 * drift + rng.normal(0.0, 0.05, n), 0.05, 0.95)
    zero_start = int((ZERO_VOLUME_CANDLE - start) // timedelta(minutes=1))
    missing = int((MISSING_MINUTE - start) // timedelta(minutes=1))
    minutes: list[Minute] = []
    for i in range(n):
        o, h, low, c, v = opens[i], highs[i], lows[i], closes[i], volume[i]
        if zero_start <= i < zero_start + 15:
            h = low = c = o
            v = 0.0
        if i == missing:
            continue
        minutes.append(
            Minute(
                start + timedelta(minutes=i),
                float(o),
                float(h),
                float(low),
                float(c),
                float(v),
                float(v * c),
                float(v * buy_fraction[i]),
            )
        )
    return minutes


def synthetic_funding(start: datetime = START, days: int = DAYS) -> list[tuple[datetime, float]]:
    rates = []
    moment = start
    k = 0
    while moment < start + timedelta(days=days):
        rates.append((moment, 0.0001 + 0.00005 * float(np.sin(k / 9.0))))
        moment += timedelta(hours=8)
        k += 1
    return rates
