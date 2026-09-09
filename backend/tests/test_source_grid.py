from dataclasses import replace

import numpy as np
import pytest
from app.research.continuation import FeatureBar, FeatureSource, IneligibleSignal
from app.research.continuation_lab import trade_at
from app.research.source_grid import HOUR_US, MINUTE_US, grid_audit, unsafe_buckets
from test_continuation import T, inputs


def test_late_minute_quarantines_both_sides_of_hour_and_four_hour_boundary():
    times = np.array([T - MINUTE_US + 20_799_000], dtype=np.int64)
    assert unsafe_buckets(times, HOUR_US) == {T - HOUR_US, T}
    assert unsafe_buckets(times, 4 * HOUR_US) == {T - 4 * HOUR_US, T}
    audit = grid_audit(times)
    assert audit["off_grid_rows"] == 1 and audit["quarantined_1h_buckets"] == 2
    assert audit["repairs_or_fills"] == 0
    assert grid_audit(times.copy()) == audit


def test_quarantine_preserves_bar_and_requires_full_contiguous_recovery():
    bars = [FeatureBar(T + index * HOUR_US, 100, 99, 1) for index in range(7)]
    bars[2] = replace(bars[2], complete=False)
    times = tuple(bar.open_us for bar in bars)
    with pytest.raises(IneligibleSignal):
        FeatureSource._window(tuple(bars), times, T + 5 * HOUR_US, HOUR_US, 3)
    assert len(FeatureSource._window(tuple(bars), times, T + 6 * HOUR_US, HOUR_US, 3)) == 3
    assert len(bars) == 7  # Quarantine never silently removes a source interval.


def test_off_grid_execution_path_is_unresolved_not_rounded_or_skipped():
    data = inputs()
    data.minute_times[10] += 20_799_000
    result, available = trade_at(data, T, 100, "ALIGNED", "DEFAULT", "SYNTHETIC")
    assert result["reason"] == "UNRESOLVED_DATA_GAP"
    assert "net_r" not in result and available == T + 24 * HOUR_US


def test_normal_source_grid_has_no_quarantine():
    times = T + np.arange(100) * MINUTE_US
    assert grid_audit(times)["off_grid_rows"] == 0
    assert not unsafe_buckets(times, HOUR_US)
