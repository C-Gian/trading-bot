"""G2-01 feature formulas: exact hand-calculated fixtures for the eight columns (contract s.3-4, 11)."""

from __future__ import annotations

import math
from datetime import timedelta

import pytest
from app.g2.contract import COLUMNS, EPS
from app.g2.features import AVAILABLE, MISSING, WARMUP, Atr, Ewm, FeatureEngine, ewm_lambda
from app.g2.records import Reason
from g2_support import T0, bar

H1, H4, M15 = timedelta(hours=1), timedelta(hours=4), timedelta(minutes=15)
T = T0 + timedelta(days=16)  # 96 x 4h, 384 x 1h, 1536 x 15m completed bars end exactly at T


def ewm(values: list[float], half_life: int) -> float:
    lam = 2.0 ** (-1.0 / half_life)
    state = values[0]
    for x in values[1:]:
        state = lam * state + (1 - lam) * x
    return state


def series():
    closes4 = [100.0 * math.exp(0.01 * math.sin(k / 5.0) + 0.0005 * k) for k in range(96)]
    closes1 = [100.0 * math.exp(0.004 * math.cos(k / 7.0) + 0.0002 * k) for k in range(384)]
    closes15 = [100.0 * math.exp(0.003 * math.sin(k / 11.0) + 0.00004 * k) for k in range(1536)]
    quotes = [1000.0 + 300.0 * math.sin(k / 13.0) for k in range(1536)]
    volumes = [20.0 + 5.0 * math.cos(k / 3.0) for k in range(1536)]
    takers = [v * (0.5 + 0.3 * math.sin(k / 17.0)) for k, v in enumerate(volumes)]
    bars = []
    for k, c in enumerate(closes4):
        bars.append(bar("4h", T - (96 - k) * H4, c, c * 1.01, c * 0.99, c))
    for k, c in enumerate(closes1):
        bars.append(bar("1h", T - (384 - k) * H1, c, c * 1.002, c * 0.998, c))
    for k, c in enumerate(closes15):
        bars.append(bar("15m", T - (1536 - k) * M15, c, c, c, c, volumes[k], quotes[k], takers[k]))
    bars.sort(key=lambda b: (b.close_time, b.timeframe))
    return bars, closes4, closes1, closes15, quotes, volumes, takers


def engine_with(bars) -> FeatureEngine:
    engine = FeatureEngine()
    for item in bars:
        engine.on_bar(item)
    return engine


def test_ewm_operator_is_the_contract_recursion():
    e = Ewm(4)
    for x in (1.0, 2.0, 3.0):
        e.update(x)
    lam = 2 ** (-1 / 4)
    expected = lam * (lam * 1.0 + (1 - lam) * 2.0) + (1 - lam) * 3.0
    assert e.value == pytest.approx(expected, rel=0, abs=1e-15)
    assert ewm_lambda(96) == 2 ** (-1 / 96) and e.count == 3


def test_exact_hand_calculated_eight_columns():
    bars, closes4, closes1, closes15, quotes, volumes, takers = series()
    snap = engine_with(bars).snapshot(T)
    assert snap.reason is None and snap.term_status == (AVAILABLE,) * 8
    log1 = [math.log(c) for c in closes1]
    log4 = [math.log(c) for c in closes4]
    local = ewm(log1, 4) - ewm(log1, 16)
    context = ewm(log4, 6) - ewm(log4, 24)
    extension = math.log(closes15[-1]) - ewm(log1, 4)
    lq = [math.log1p(q) for q in quotes]
    participation = lq[-1] - ewm(lq[:-1], 96)
    taker = (2 * takers[-1] - volumes[-1]) / volumes[-1]
    r = [math.log(closes15[k] / closes15[k - 1]) for k in range(1, 1536)]
    v_fast, v_slow = ewm([x * x for x in r], 16), ewm([x * x for x in r], 96)
    volatility = 0.5 * math.log(max(v_fast, EPS) / max(v_slow, EPS))
    response = r[-1] / math.sqrt(max(v_slow, EPS))
    expected = {
        "LOCAL_STRUCTURE": local,
        "CONTEXT_STRUCTURE": context,
        "PRICE_EXTENSION": extension,
        "RELATIVE_PARTICIPATION": participation,
        "TAKER_IMBALANCE": taker,
        "VOLATILITY_STATE": volatility,
        "LOCAL_STRUCTURE_X_PARTICIPATION": local * participation,
        "IMBALANCE_X_PRICE_RESPONSE": taker * response,
    }
    for name, value in zip(COLUMNS, snap.raw, strict=True):
        assert value == pytest.approx(expected[name], rel=1e-12, abs=1e-15), name
    assert snap.sigma_4h == pytest.approx(math.sqrt(16 * v_slow), rel=1e-12)
    assert snap.price_response == pytest.approx(response, rel=1e-12)
    assert snap.max_source_time == T and snap.price == closes15[-1]


def test_warmup_eligibility_is_four_times_the_longest_half_life():
    bars, *_ = series()
    # Drop the first 1h bar: 383 bars remain, still >= 64. Truncate instead to exactly 63/64.
    for count, expected in ((63, WARMUP), (64, AVAILABLE)):
        kept = [b for b in bars if b.timeframe != "1h" or b.open_time >= T - count * H1]
        snap = engine_with(kept).snapshot(T)
        assert snap.term_status[COLUMNS.index("LOCAL_STRUCTURE")] == expected
    for count, expected in ((95, WARMUP), (96, AVAILABLE)):
        kept = [b for b in bars if b.timeframe != "4h" or b.open_time >= T - count * H4]
        status = engine_with(kept).snapshot(T).term_status
        assert status[COLUMNS.index("CONTEXT_STRUCTURE")] == expected
    for count, expected in ((384, WARMUP), (385, AVAILABLE)):
        # participation needs 384 observations strictly before the decision candle
        kept = [b for b in bars if b.timeframe != "15m" or b.open_time >= T - count * M15]
        status = engine_with(kept).snapshot(T).term_status
        assert status[COLUMNS.index("RELATIVE_PARTICIPATION")] == expected


def test_gap_and_incomplete_bar_reset_the_recursion_and_force_rewarm():
    bars, *_ = series()
    gap = [b for b in bars if not (b.timeframe == "1h" and b.open_time == T - 10 * H1)]
    snap = engine_with(gap).snapshot(T)
    assert snap.term_status[COLUMNS.index("LOCAL_STRUCTURE")] == WARMUP
    assert snap.reason is Reason.FORECAST_UNAVAILABLE_WARMUP
    broken = [
        bar("1h", b.open_time, b.open, b.high, b.low, b.close, complete=False)
        if b.timeframe == "1h" and b.open_time == T - 3 * H1
        else b
        for b in bars
    ]
    engine = engine_with(broken)
    assert engine.local_fast.count == 2  # re-initialized by the first valid bar after the reset
    assert engine.snapshot(T).term_status[COLUMNS.index("LOCAL_STRUCTURE")] == WARMUP


def test_incomplete_decision_candle_is_never_read():
    bars, *_ = series()
    last = (
        bars[-1]
        if bars[-1].timeframe == "15m"
        else next(b for b in reversed(bars) if b.timeframe == "15m")
    )
    broken = [
        bar("15m", b.open_time, b.open, b.high, b.low, b.close, complete=False) if b is last else b
        for b in bars
    ]
    snap = engine_with(broken).snapshot(T)
    assert snap.price is None and snap.reason is Reason.FORECAST_UNAVAILABLE_MISSING_DATA
    assert snap.raw[COLUMNS.index("TAKER_IMBALANCE")] is None


@pytest.mark.parametrize(
    ("quote", "taker", "volume", "column"),
    [
        (None, 5.0, 10.0, "RELATIVE_PARTICIPATION"),
        (1000.0, None, 10.0, "TAKER_IMBALANCE"),
        (1000.0, 0.0, 0.0, "TAKER_IMBALANCE"),
    ],
)
def test_missing_critical_data_is_unavailable_never_zero(quote, taker, volume, column):
    bars, *_ = series()
    last15 = max((b for b in bars if b.timeframe == "15m"), key=lambda b: b.open_time)
    edited = [
        bar("15m", b.open_time, b.open, b.high, b.low, b.close, volume, quote, taker)
        if b is last15
        else b
        for b in bars
    ]
    snap = engine_with(edited).snapshot(T)
    index = COLUMNS.index(column)
    assert snap.raw[index] is None and snap.term_status[index] == MISSING
    assert snap.reason is Reason.FORECAST_UNAVAILABLE_MISSING_DATA


@pytest.mark.parametrize(("buy", "expected"), [(10.0, 1.0), (0.0, -1.0), (5.0, 0.0), (7.5, 0.5)])
def test_taker_imbalance_bounds(buy, expected):
    bars, *_ = series()
    last15 = max((b for b in bars if b.timeframe == "15m"), key=lambda b: b.open_time)
    edited = [
        bar("15m", b.open_time, b.open, b.high, b.low, b.close, 10.0, 1000.0, buy)
        if b is last15
        else b
        for b in bars
    ]
    value = engine_with(edited).snapshot(T).raw[COLUMNS.index("TAKER_IMBALANCE")]
    assert value == expected and -1.0 <= value <= 1.0


def test_constant_price_gives_invalid_sigma_and_eps_floors():
    bars, *_ = series()
    flat = [
        bar("15m", b.open_time, 100.0, 100.0, 100.0, 100.0, 10.0, 1000.0, 5.0)
        if b.timeframe == "15m"
        else b
        for b in bars
    ]
    snap = engine_with(flat).snapshot(T)
    assert snap.sigma_4h is None
    assert snap.reason is Reason.FORECAST_UNAVAILABLE_INVALID_SIGMA
    assert snap.raw[COLUMNS.index("VOLATILITY_STATE")] == 0.0  # 0.5*log(eps/eps)
    assert snap.price_response == 0.0


def test_atr14_exact_wilder_fixture():
    atr = Atr()
    atr.update(bar("1h", T0, 100, 101, 99, 100))  # no previous close: no TR
    for k in range(1, 15):
        atr.update(bar("1h", T0 + k * H1, 100, 101, 99, 100))  # TR = 2
    assert atr.value == 2.0
    atr.update(bar("1h", T0 + 15 * H1, 100, 110, 100, 105))  # TR = max(10, 10, 0) = 10
    assert atr.value == (13 * 2.0 + 10.0) / 14
    atr.update(bar("1h", T0 + 16 * H1, 95, 95, 90, 92))  # TR = max(5, |95-105|, |90-105|) = 15
    assert atr.value == pytest.approx((13 * ((13 * 2.0 + 10.0) / 14) + 15.0) / 14, abs=1e-15)
