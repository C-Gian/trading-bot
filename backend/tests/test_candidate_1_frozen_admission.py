"""Synthetic proofs for the frozen Candidate #1 admission calculation.

No market data is read here; these fixtures prove the frozen event, state, timing and gate
semantics before the single real calculation runs.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np
import pytest
from app.research import candidate_1_admission as frozen

HOUR = 3600


def _epoch(year: int, month: int, day: int, hour: int = 0) -> int:
    return int(datetime(year, month, day, hour, tzinfo=UTC).timestamp())


def test_shock_z_uses_the_168_returns_ending_at_t_minus_4h() -> None:
    returns = np.array([0.01 if i % 2 else -0.01 for i in range(200)])
    log_close = np.concatenate(([0.0], np.cumsum(returns)))
    log_close[-4:] = log_close[-5] - np.array([0.01, 0.02, 0.03, 0.04])
    z, sigma = frozen.shock_z(np.exp(log_close))
    last = log_close.shape[0] - 1
    assert sigma[last] == pytest.approx(0.01)
    assert z[last] == pytest.approx(-0.04 / (0.01 * 2))
    # The shock interval does not enter the risk estimator.
    _, calm_sigma = frozen.shock_z(np.exp(np.concatenate(([0.0], np.cumsum(returns)))))
    assert calm_sigma[last] == pytest.approx(sigma[last])
    # Fewer than 169 prior closes: undefined.
    assert math.isnan(sigma[171]) and not math.isnan(sigma[172])


def test_a_missing_close_in_the_volatility_window_makes_shock_undefined() -> None:
    close = np.exp(np.cumsum(np.tile([0.01, -0.01], 300)))
    close[300] = np.nan  # removes the returns ending at hours 300 and 301
    z, _ = frozen.shock_z(close)
    assert math.isnan(z[300]) and math.isnan(z[304])  # R4 endpoints
    assert math.isnan(z[305]) and math.isnan(z[301 + 171])  # volatility window
    assert not math.isnan(z[299]) and not math.isnan(z[301 + 172])


def test_first_crossing_and_four_hour_suppression() -> None:
    z = np.array([0.0, -3.0, -3.0, 0.0, -3.0, 0.0, 0.0, -3.0, np.nan, -2.5, 0.0, -2.0])
    events, undetermined = frozen.triggers(z)
    # 1 triggers; 2 continues; 4 is suppressed (< 1 + 4); 5 is eligible again -> 7 triggers;
    # 9 has an undefined predecessor; -2.0 exactly is a sell-off (11 triggers).
    assert events == [1, 7, 11]
    assert undetermined == 1


def test_a_suppressed_crossing_does_not_extend_the_cooldown() -> None:
    z = np.array([0.0, -3.0, 0.0, -3.0, 0.0, -3.0])
    assert frozen.triggers(z)[0] == [1, 5]


def _inputs(oi_times: list[int], oi_quantity: list[float]) -> frozen.HourlyInputs:
    return frozen.HourlyInputs(
        instants=np.array([0], dtype=np.int64),
        spot_close=np.array([1.0]),
        perp_close=np.array([1.0]),
        oi_times=np.array(oi_times, dtype=np.int64),
        oi_quantity=np.array(oi_quantity),
    )


def test_oi_state_timing_and_quality_rules() -> None:
    t = _epoch(2023, 5, 1, 12)
    inputs = _inputs([t - 900, t - 600, t, t + 300], [1.0, 2.0, 3.0, 4.0])
    assert frozen.oi_state(inputs, t)[0] == 3.0  # stamped exactly T is admissible
    assert frozen.oi_state(inputs, t - 1)[0] == 2.0  # never a later record
    assert frozen.oi_state(_inputs([t - 600], [1.0]), t)[0] == 1.0
    assert frozen.oi_state(_inputs([t - 601], [1.0]), t)[1] == frozen.OI_STALE
    assert frozen.oi_state(_inputs([t - 300], [0.0]), t)[1] == frozen.OI_NON_POSITIVE
    assert frozen.oi_state(_inputs([t + 1], [1.0]), t)[1] == frozen.OI_NO_RECORD
    start = frozen.OI_ADMITTED_START
    outside = frozen.oi_state(_inputs([start - 300], [1.0]), start)
    assert outside[1] == frozen.OI_OUTSIDE_ADMITTED_INTERVAL


def test_required_effect_screen() -> None:
    assert frozen.required_standardized_effect(25) <= 0.50
    assert frozen.required_standardized_effect(24) > 0.50
    assert frozen.required_standardized_effect(0) == math.inf
    assert frozen.required_standardized_effect(100) == pytest.approx(0.24864748, abs=1e-6)


def _market(drop_hours: dict[int, str]) -> frozen.HourlyInputs:
    """Hourly grid from 2021-12-01; each drop hour gets a -8 z shock and a chosen state."""
    start = _epoch(2021, 12, 1)
    hours = 24 * 60
    instants = start + np.arange(hours, dtype=np.int64) * HOUR
    returns = np.tile([0.001, -0.001], hours // 2)
    rel = np.zeros(hours)
    oi_level = np.full(hours, 1000.0)
    for index, state in drop_hours.items():
        returns[index] = -0.016
        if state in {"CANDIDATE", "OI_ONLY"}:
            oi_level[index] = 990.0
        if state in {"CANDIDATE", "REL_ONLY"}:
            rel[index] = -0.001
    log_spot = np.cumsum(returns)
    spot = np.exp(log_spot)
    perp = np.exp(log_spot + rel)
    oi_times = np.arange(instants[0], instants[-1] + 1, 300, dtype=np.int64)
    oi_quantity = oi_level[np.clip((oi_times - start) // HOUR, 0, hours - 1)]
    return frozen.HourlyInputs(instants, spot, perp, oi_times, oi_quantity.astype(float))


def test_end_to_end_classification_and_gates() -> None:
    first = (_epoch(2022, 1, 5, 10) - _epoch(2021, 12, 1)) // HOUR
    drops = {
        first: "CANDIDATE",
        first + 48: "OI_ONLY",
        first + 96: "REL_ONLY",
        first + 144: "CANDIDATE",
    }
    record = frozen.admission(_market(drops))
    assert record["counts"] == {"intended": 4, "valid": 4, "candidate": 2, "control": 2}
    assert [e["candidate"] for e in record["episodes"]] == [True, False, False, True]
    assert all(e["shock_z"] <= -2.0 for e in record["episodes"])
    assert record["source_coverage"]["coverage"] == 1.0
    # All events fall in 2022: one year only -> common support fails; tiny n -> screen fails.
    assert record["common_support"]["years_used"] == [2022]
    assert record["gates"]["COMMON_SUPPORT"] is False
    assert record["gates"]["DETECTABILITY_12M"] is False
    assert record["disposition"] == frozen.CLOSED
    assert record["project_state"] == "STRONG_STOP_PENDING_ASTRA"
    assert record["forward_returns_computed"] is False


def test_missing_perp_is_an_exclusion_not_a_control() -> None:
    first = (_epoch(2022, 1, 5, 10) - _epoch(2021, 12, 1)) // HOUR
    market = _market({first: "CANDIDATE"})
    market.perp_close[first - 4] = np.nan
    record = frozen.admission(market)
    assert record["counts"]["valid"] == 0
    assert record["source_coverage"]["exclusion_reasons"][frozen.PERP_CLOSE_MISSING] == 1
    assert record["gates"]["SOURCE_RELIABILITY"] is False


def test_nothing_after_t_can_change_an_episode() -> None:
    first = (_epoch(2022, 1, 5, 10) - _epoch(2021, 12, 1)) // HOUR
    base = frozen.admission(_market({first: "CANDIDATE"}))["episodes"][0]
    market = _market({first: "CANDIDATE"})
    market.spot_close[first + 1 :] *= 0.5
    market.perp_close[first + 1 :] *= 2.0
    cutoff = market.instants[first]
    market.oi_quantity[market.oi_times > cutoff] = 1.0
    assert frozen.admission(market)["episodes"][0] == base
