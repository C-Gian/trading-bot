from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from app.backtest import EVENT_SEQUENCE
from app.backtest.asof import AsOfView
from app.backtest.engine import simulate
from app.backtest.models import Bar, ExitReason, Intent
from app.data.policy import require_allowed

T = datetime(2020, 1, 1, 1, tzinfo=UTC)


def intent(signal=T):
    return Intent(
        "SYNTHETIC",
        "SYNTHETIC",
        "SYNTHETIC",
        "a" * 64,
        signal,
        "LONG",
        "NEXT_1M_OPEN",
        D(90),
        D(110),
        "LIMIT_AT_TARGET",
        60,
    )


def bar(t, o=100, h=105, l=95, c=101, complete=True):
    return Bar(t, D(o), D(h), D(l), D(c), complete)


def test_same_boundary_has_explicit_causal_order():
    record = simulate(intent(), [bar(T, h=111)])
    assert record.signal_timestamp == record.entry_timestamp
    assert EVENT_SEQUENCE == ("BAR_CLOSE", "SIGNAL_DECISION", "NEXT_1M_OPEN_EXECUTION")


def test_target_available_at_open_precedes_later_intrabar_stop_golden():
    record = simulate(intent(), [bar(T), bar(T + timedelta(minutes=1), o=112, h=115, l=80, c=90)])
    assert record.exit_reason == ExitReason.TARGET and record.exit_raw_price == D(110)


def test_contiguous_suffix_rejects_hourly_and_four_hour_holes():
    one = (bar(T - timedelta(hours=3)), bar(T - timedelta(hours=1)))
    four = (bar(T - timedelta(hours=13)), bar(T - timedelta(hours=5)))
    view = AsOfView.build(T, one, four)
    with pytest.raises(ValueError):
        view.require_1h(2)
    with pytest.raises(ValueError):
        view.require_4h(2)


def test_incomplete_breaks_continuity_and_future_surface_absent():
    view = AsOfView.build(
        T, (bar(T - timedelta(hours=2)), bar(T - timedelta(hours=1), complete=False)), ()
    )
    with pytest.raises(ValueError):
        view.require_1h(1)
    assert not hasattr(view, "future_bars")


def test_offset_cutoff_bypass_naive_signal_and_postcutoff_path_rejected():
    with pytest.raises(ValueError):
        require_allowed("BTCUSDT", datetime.fromisoformat("2024-12-31T20:30:00-05:00"))
    with pytest.raises(ValueError):
        require_allowed("BTCUSDT", datetime.fromisoformat("2024-12-31T23:00:00"))
    with pytest.raises(ValueError):
        intent(T + timedelta(minutes=1))
    with pytest.raises(ValueError):
        simulate(intent(), [bar(datetime(2025, 1, 1, tzinfo=UTC))])


def test_real_data_known_gap_breaks_contiguous_lookback():
    path = Path(__file__).parents[2] / "data/derived/BTCUSDT-1h.parquet"
    if not path.exists():
        pytest.skip("local development dataset not installed")
    table = pq.read_table(path).to_pylist()
    rows = [
        r
        for r in table
        if datetime(2017, 9, 6, tzinfo=UTC)
        <= r["open_time"]
        <= datetime(2017, 9, 7, 12, tzinfo=UTC)
    ]
    bars = tuple(
        Bar(
            r["open_time"],
            D(str(r["open"])),
            D(str(r["high"])),
            D(str(r["low"])),
            D(str(r["close"])),
            r["complete"],
        )
        for r in rows
    )
    view = AsOfView.build(datetime(2017, 9, 7, 13, tzinfo=UTC), bars, ())
    with pytest.raises(ValueError):
        view.require_1h(18)
