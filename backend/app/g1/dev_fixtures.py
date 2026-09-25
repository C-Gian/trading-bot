"""Deterministic synthetic 1m paths for the System G1 development engine (not market data).

Timestamps are placed in 2000-2001, before BTC existed. The path is a seeded log random walk with
alternating trending and mean-reverting regimes, plus synthetic base/quote/taker-buy volumes, so
the frozen indicators, P1/P2 recognition, the forecaster's annual training boundary and the ledger
can all be exercised end to end. Nothing about its P&L or forecast quality is evidence.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np

from .bars import MINUTE, Bar, minute_bar
from .canonical import digest

FIXTURE_ID = "G1-DEVELOPMENT-SYNTHETIC-PATH-V1"
START = datetime(2000, 11, 20, tzinfo=UTC)
END = datetime(2001, 1, 8, tzinfo=UTC)
SEED = 20260927
CENT = Decimal("0.01")
# Regime schedule (days): trend up, bounded range, trend down, bounded range — repeating. Range
# regimes are long enough for the doubly-smoothed 4h ADX to fall below 20.
REGIME_DAYS = (6, 12, 6, 12)
RANGE_AMPLITUDE = 0.015
RANGE_PERIOD = 960


def regime_at(index: int) -> int:
    cycle = sum(REGIME_DAYS) * 1440
    offset = index % cycle
    for regime, days in enumerate(REGIME_DAYS):
        if offset < days * 1440:
            return regime
        offset -= days * 1440
    return 0  # pragma: no cover


def synthetic_path(
    start: datetime = START,
    end: datetime = END,
    seed: int = SEED,
    missing: frozenset[int] = frozenset(),
) -> tuple[Bar, ...]:
    minutes = int((end - start) / MINUTE)
    rng = np.random.default_rng(seed)
    shocks = rng.normal(0.0, 0.0007, minutes)
    wick = np.abs(rng.normal(0.0, 0.0002, minutes))
    volume = np.exp(rng.normal(2.0, 0.5, minutes))
    taker_noise = rng.uniform(-0.15, 0.15, minutes)
    bars = []
    log_price = math.log(30000.0)
    anchor = log_price
    for index in range(minutes):
        regime = regime_at(index)
        if regime == 0:
            drift = 0.00006
        elif regime == 2:
            drift = -0.00006
        else:
            # Bounded auction: revert towards an oscillating value area (period ~1.5 days).
            target = anchor + RANGE_AMPLITUDE * math.sin(2 * math.pi * index / RANGE_PERIOD)
            drift = -0.02 * (log_price - target)
        if regime in (0, 2):
            anchor = log_price
        noise = float(shocks[index]) * (0.4 if regime in (1, 3) else 1.0)
        change = drift + noise
        opened = math.exp(log_price)
        log_price += change
        closed = math.exp(log_price)
        if index in missing:
            continue
        open_ = Decimal(repr(opened)).quantize(CENT)
        close = Decimal(repr(closed)).quantize(CENT)
        high = (max(open_, close) * Decimal(repr(1 + float(wick[index])))).quantize(CENT)
        low = (min(open_, close) * Decimal(repr(1 - float(wick[index])))).quantize(CENT)
        base = Decimal(
            repr(round(float(volume[index]) * (1.8 if abs(change) > 0.0015 else 1.0), 6))
        )
        taker_share = min(0.95, max(0.05, 0.5 + 60 * float(change) + float(taker_noise[index])))
        taker = (base * Decimal(repr(round(taker_share, 6)))).quantize(Decimal("0.000001"))
        typical = (high + low + close) / 3
        bars.append(
            minute_bar(
                start + index * MINUTE,
                open_,
                high,
                low,
                close,
                base,
                (base * typical).quantize(Decimal("0.000001")),
                taker,
            )
        )
    return tuple(bars)


def synthetic_funding(start: datetime = START, end: datetime = END) -> dict[datetime, Decimal]:
    rates = {}
    moment = start.replace(hour=0, minute=0)
    index = 0
    while moment <= end:
        for hour in (0, 8, 16):
            settle = moment.replace(hour=hour)
            if start < settle <= end:
                rates[settle] = Decimal("0.0001") if index % 5 else Decimal("-0.00005")
                index += 1
        moment += timedelta(days=1)
    return rates


def path_hash(bars: tuple[Bar, ...]) -> str:
    return digest(
        [
            (
                b.open_time,
                b.open,
                b.high,
                b.low,
                b.close,
                b.volume,
                b.quote_volume,
                b.taker_buy_base_volume,
            )
            for b in bars
        ]
    )
