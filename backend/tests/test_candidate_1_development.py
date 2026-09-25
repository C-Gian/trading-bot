"""Synthetic proofs for the Candidate #1 Development Lab implementation.

Every price and outcome here is synthetic. The only real artifact read is the committed,
outcome-free frozen admission record (event identity); no execution bar is ever loaded.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest
from app.backtest.engine import simulate
from app.backtest.models import Bar, Intent
from app.research import candidate_1_development as dev

ROOT = Path(__file__).resolve().parents[2]
HOUR = 3600


def _epoch(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp())


def _episode(t: int, z: float, sigma: float, candidate: bool) -> dev.Episode:
    return dev.Episode(t, datetime.fromtimestamp(t, UTC).year, z, sigma, candidate)


# --- 1. frozen population ingestion ------------------------------------------------------


def test_the_frozen_admission_population_is_consumed_not_rederived() -> None:
    episodes, meta = dev.load_admission(ROOT)
    assert all(dev.identity_checks(ROOT).values())
    assert meta["valid"] == len(episodes) == 335
    assert meta["candidate"] == sum(e.candidate for e in episodes) == 116
    assert meta["admission_exclusions"] == {"OI_NON_POSITIVE": 1}
    record = json.loads((ROOT / dev.ADMISSION_RECORD_PATH).read_text(encoding="utf-8"))
    first = next(item for item in record["episodes"] if "excluded" not in item)
    assert episodes[0].shock_z == first["shock_z"]
    assert episodes[0].sigma_prior_1h == first["sigma_prior_1h"]
    assert dev.non_overlapping([e.t for e in episodes if e.candidate])


def test_ingestion_fails_closed_on_a_drifted_record() -> None:
    record = json.loads((ROOT / dev.ADMISSION_RECORD_PATH).read_text(encoding="utf-8"))
    with pytest.raises(dev.DevelopmentError, match="does not admit"):
        dev.episodes_from_admission({**record, "disposition": "OTHER"})
    with pytest.raises(dev.DevelopmentError, match="counts drifted"):
        dev.episodes_from_admission({**record, "counts": {**record["counts"], "candidate": 1}})


# --- 2. outcome-blind matching -----------------------------------------------------------


def _year_pool(cands: list[tuple[float, float]], ctrls: list[tuple[float, float]]) -> tuple:
    base = _epoch(2023, 2, 1)
    c = [_episode(base + i * 6 * HOUR, z, s, True) for i, (z, s) in enumerate(cands)]
    k = [_episode(base + (100 + i) * 6 * HOUR, z, s, False) for i, (z, s) in enumerate(ctrls)]
    return c, k


def test_caliper_excludes_edges_beyond_half_a_standardized_unit() -> None:
    cands, ctrls = _year_pool([(-2.1, 0.0040), (-6.0, 0.0041)], [(-2.1, 0.0040), (-2.2, 0.0042)])
    result = dev.match_year(cands, ctrls)
    assert result["blocked"] is None
    assert [p["candidate"] for p in result["pairs"]] == [cands[0].t]


def test_maximum_cardinality_precedes_distance() -> None:
    # z sd ~1.156, so the caliper is ~0.578 in raw z: feasible edges are A-X (0.15), A-Y (0.20)
    # and B-X (0.25); B-Y (0.60) is not. Nearest-first greedy (A-X) would strand B.
    cands, ctrls = _year_pool(
        [(-2.50, 0.0040), (-2.10, 0.0040)],
        [(-2.35, 0.0040), (-2.70, 0.0040), (-4.0, 0.0041), (-4.3, 0.0039), (-0.9, 0.0040)],
    )
    result = dev.match_year(cands, ctrls)
    assert result["blocked"] is None
    pairs = {p["candidate"]: p["control"] for p in result["pairs"]}
    assert pairs == {cands[0].t: ctrls[1].t, cands[1].t: ctrls[0].t}


def test_minimum_total_squared_distance_among_maximum_matchings() -> None:
    cands, ctrls = _year_pool(
        [(-2.40, 0.0040), (-2.60, 0.0041)],
        [(-2.41, 0.0040), (-2.61, 0.0041), (-3.9, 0.0045), (-4.1, 0.0046)],
    )
    pairs = {p["candidate"]: p["control"] for p in dev.match_year(cands, ctrls)["pairs"]}
    assert pairs == {cands[0].t: ctrls[0].t, cands[1].t: ctrls[1].t}


def test_exact_ties_break_by_candidate_then_control_timestamp() -> None:
    cands, ctrls = _year_pool(
        [(-2.5, 0.004), (-2.5, 0.004)],
        [(-2.5, 0.004), (-2.5, 0.004), (-2.5, 0.004), (-4.0, 0.006), (-2.0, 0.003)],
    )
    pairs = sorted((p["candidate"], p["control"]) for p in dev.match_year(cands, ctrls)["pairs"])
    assert pairs == [(cands[0].t, ctrls[0].t), (cands[1].t, ctrls[1].t)]
    # Input order never changes the result.
    shuffled = dev.match_year(list(reversed(cands)), list(reversed(ctrls)))["pairs"]
    assert sorted((p["candidate"], p["control"]) for p in shuffled) == pairs


def test_zero_standard_deviation_blocks_the_year() -> None:
    cands, ctrls = _year_pool([(-2.5, 0.004)], [(-2.5, 0.004)])
    assert dev.match_year(cands, ctrls)["blocked"] == "ZERO_OR_INVALID_SD_SHOCK_Z"


def test_standardized_mean_difference_and_gates() -> None:
    assert dev.smd([1.0, 3.0], [1.0, 3.0]) == 0.0
    assert dev.smd([2.0, 4.0], [1.0, 3.0]) == pytest.approx(1 / math.sqrt(2))
    assert dev.smd([1.0], [2.0]) == math.inf
    episodes = _synthetic_population()
    matched = dev.matching(episodes)
    assert all(matched["gates"].values())
    assert matched["coverage"] == 1.0


def test_matching_is_outcome_blind() -> None:
    episodes = _synthetic_population()
    one = dev.evaluate(episodes, _prices(episodes, 100.0, 30.0), {"OK": True})["matching"]
    two = dev.evaluate(episodes, _prices(episodes, -500.0, 900.0), {"OK": True})["matching"]
    assert one == two


# --- 3. execution semantics --------------------------------------------------------------


def test_accounting_matches_the_backtest_engine() -> None:
    start = datetime(2023, 3, 1, tzinfo=UTC)
    opens = [Decimal(100), Decimal(101), Decimal("102.5"), Decimal(103)]
    bars = [
        Bar(start + timedelta(minutes=i), o, o + 1, o - 1, opens[i + 1] if i + 1 < 4 else o)
        for i, o in enumerate(opens)
    ]
    intent = Intent("r", "s", "m", "h", start, "LONG", "NEXT_1M_OPEN", Decimal(50), None, None, 3)
    engine = simulate(intent, bars)
    ours = dev.trade_accounting(100.0, 103.0, dev.PRIMARY_COSTS)
    assert engine.exit_raw_price == Decimal(103)
    assert engine.net_pnl is not None
    assert ours["net_bp"] == pytest.approx(float(engine.net_pnl / Decimal(100) * 10_000))
    assert ours["gross_bp"] - ours["fees_bp"] - ours["friction_bp"] == pytest.approx(ours["net_bp"])


def test_cost_profiles_are_24_and_36_bp_round_trip_on_a_flat_price() -> None:
    assert dev.trade_accounting(100.0, 100.0, dev.PRIMARY_COSTS)["net_bp"] == pytest.approx(-24.0)
    assert dev.trade_accounting(100.0, 100.0, dev.STRESS_COSTS)["net_bp"] == pytest.approx(-36.0)


def _bar(price: float) -> dev.MinuteBar:
    return dev.MinuteBar(price, price, price, price)


def test_primary_and_delay_timestamps() -> None:
    t = _epoch(2023, 6, 1, 10)
    queried: list[int] = []

    def prices(minute: int) -> dev.MinuteBar | None:
        queried.append(minute)
        return _bar(100.0)

    primary = dev.execute(t, prices, dev.PRIMARY_COSTS)
    assert primary["entry_time"] == t + 16 * 60 and primary["exit_time"] == t + 4 * HOUR + 15 * 60
    assert primary["holding_minutes"] == 239
    assert max(queried) == t + 4 * HOUR + 15 * 60  # nothing after the exit minute
    delay = dev.execute(t, prices, dev.PRIMARY_COSTS, dev.DELAY_ENTRY_OFFSET)
    assert delay["entry_time"] == t + 46 * 60 and delay["exit_time"] == primary["exit_time"]
    assert delay["holding_minutes"] == 209


def test_missing_exact_minutes_are_unscorable_without_replacement_fill() -> None:
    t = _epoch(2023, 6, 1, 10)
    entry, exit_ = t + 16 * 60, t + 4 * HOUR + 15 * 60
    no_entry = dev.execute(t, lambda m: None if m == entry else _bar(100.0), dev.PRIMARY_COSTS)
    no_exit = dev.execute(t, lambda m: None if m == exit_ else _bar(100.0), dev.PRIMARY_COSTS)
    assert (no_entry["scorable"], no_entry["reason"]) == (False, dev.ENTRY_MINUTE_UNAVAILABLE)
    assert (no_exit["scorable"], no_exit["reason"]) == (False, dev.EXIT_MINUTE_UNAVAILABLE)


def test_exit_after_the_development_cutoff_is_never_read() -> None:
    t = _epoch(2024, 12, 31, 21)

    def prices(minute: int) -> dev.MinuteBar | None:
        raise AssertionError("a post-cutoff bar was requested")

    record = dev.execute(t, prices, dev.PRIMARY_COSTS)
    assert record["reason"] == dev.EXIT_AFTER_DEVELOPMENT_CUTOFF


def test_overlapping_primary_positions_are_detected() -> None:
    t = _epoch(2023, 1, 1, 4)
    assert dev.non_overlapping([t, t + 4 * HOUR])
    assert not dev.non_overlapping([t, t + 3 * HOUR])


# --- 4. metrics ------------------------------------------------------------------------------


def test_expected_shortfall_and_drawdown() -> None:
    values = [float(v) for v in range(-50, 50)]  # 100 values
    assert dev.expected_shortfall(values) == pytest.approx(np.mean(range(-50, -40)))
    assert dev.expected_shortfall([5.0, -5.0, 1.0]) == -5.0  # ceil(0.3) = 1
    assert dev.max_drawdown([10.0, -30.0, 5.0, -10.0, 50.0]) == 35.0
    assert dev.max_drawdown([-10.0, 5.0]) == 10.0  # measured from the zero start


# --- 5. dependence-aware uncertainty ---------------------------------------------------------


def test_one_way_cluster_se_with_repeated_months() -> None:
    x = [1.0, 3.0, 2.0, 6.0, 4.0]
    months = ["a", "a", "b", "b", "c"]
    e = np.array(x) - np.mean(x)
    sums = [e[0] + e[1], e[2] + e[3], e[4]]
    expected = math.sqrt(3 / 2 * sum(s * s for s in sums) / 25)
    result = dev.cluster_se(x, months)
    assert result["valid"] and result["se"] == pytest.approx(expected)
    assert result["clusters"] == [3] and result["df"] == 2
    assert result["ci95"][0] < np.mean(x) < result["ci95"][1]


def test_two_way_cluster_se_with_overlapping_clusters() -> None:
    x = [1.0, 4.0, 2.0, 7.0, 3.0, 5.0]
    a = ["m1", "m1", "m2", "m2", "m3", "m3"]
    b = ["m1", "m2", "m2", "m3", "m3", "m1"]
    e = np.array(x) - np.mean(x)

    def part(labels: list) -> float:
        sums: dict = {}
        for v, g in zip(e, labels, strict=True):
            sums[g] = sums.get(g, 0.0) + v
        g = len(sums)
        return g / (g - 1) * sum(s * s for s in sums.values()) / 36

    expected = part(a) + part(b) - part(list(zip(a, b, strict=True)))
    result = dev.cluster_se(x, a, b)
    assert result["valid"] and result["se"] == pytest.approx(math.sqrt(expected))
    assert result["clusters"] == [3, 3, 6]
    # Identical dimensions reduce two-way to one-way.
    assert dev.cluster_se(x, a, a)["se"] == pytest.approx(dev.cluster_se(x, a)["se"])


def test_degenerate_and_non_finite_variance_is_invalid() -> None:
    assert dev.cluster_se([1.0, 2.0], ["a", "a"])["reason"] == "FEWER_THAN_TWO_CLUSTERS"
    assert not dev.cluster_se([1.0], ["a"])["valid"]
    assert not dev.cluster_se([1.0, math.nan, 2.0], ["a", "b", "c"])["valid"]
    assert dev.cluster_se([2.0, 2.0, 2.0], ["a", "b", "c"])["reason"] == "NON_POSITIVE_VARIANCE"
    # Two-way subtraction can go non-positive: invalid, never promoted.
    negative = dev.cluster_se([1.0, -1.0, -1.0, 1.0], ["a", "a", "b", "b"], ["c", "d", "c", "d"])
    assert negative["valid"] is False
    assert math.isnan(dev.planning_sd(5.0, negative, 4, {}))
    assert dev.required_n(math.nan, 25.0) == math.inf


# --- 6. prospective detectability ------------------------------------------------------------


def test_planning_sd_and_required_n() -> None:
    se = {"valid": True, "se": 10.0}
    assert dev.planning_sd(40.0, se, 25, {"2022": 45.0, "2023": math.nan}) == 50.0
    assert dev.planning_sd(60.0, se, 25, {"2022": 45.0}) == 60.0
    z = 1.959963984540054 + 0.8416212335729143
    assert dev.required_n(50.0, 25.0) == math.ceil((z * 50 / 25) ** 2) == 32


# --- 7. adjudication -------------------------------------------------------------------------


def _stages(**failed: str) -> dict:
    stages = {
        name: {"G": True}
        for name in ("integrity", "support", "development", "promotion_feasibility")
    }
    for stage in failed.values():
        stages[stage] = {"G": False}
    return stages


def test_disposition_order_cannot_be_overridden_by_later_stages() -> None:
    assert dev.adjudicate(_stages()) == dev.PROMOTION_ELIGIBLE
    assert dev.adjudicate(_stages(a="promotion_feasibility")) == dev.INCONCLUSIVE
    assert dev.adjudicate(_stages(a="development")) == dev.REJECTED
    assert dev.adjudicate(_stages(a="support")) == dev.BLOCKED
    assert dev.adjudicate(_stages(a="integrity")) == dev.INVALID_EXECUTION
    assert dev.adjudicate(_stages(a="support", b="development")) == dev.BLOCKED


# --- end-to-end on a synthetic market --------------------------------------------------------


def _synthetic_population() -> list[dev.Episode]:
    episodes = []
    for year in dev.YEARS:
        for i in range(30):
            day = _epoch(year, 1, 2) + i * 7 * 24 * HOUR
            z, sigma = -2.2 - 0.05 * (i % 10), 0.003 + 0.0001 * (i % 7)
            episodes.append(_episode(day + 4 * HOUR, z, sigma, True))
            episodes.append(_episode(day + 12 * HOUR, z - 0.001, sigma * 1.0005, False))
            episodes.append(_episode(day + 20 * HOUR, z + 0.8, sigma * 1.3, False))
    return sorted(episodes, key=lambda e: e.t)


def _prices(
    episodes: list[dev.Episode], candidate_gross_bp: float, control_gross_bp: float
) -> dev.PriceSource:
    bars: dict[int, dev.MinuteBar] = {}
    for n, e in enumerate(episodes):
        gross = (candidate_gross_bp if e.candidate else control_gross_bp) + (5 if n % 2 else -5)
        for offset in (dev.PRIMARY_ENTRY_OFFSET, dev.DELAY_ENTRY_OFFSET):
            bars[e.t + offset] = _bar(100.0)
        bars[e.t + dev.EXIT_OFFSET] = _bar(100.0 * (1 + gross / 1e4))
    return bars.get


def test_attractive_synthetic_market_is_promotion_eligible() -> None:
    episodes = _synthetic_population()
    result = dev.evaluate(episodes, _prices(episodes, 100.0, 30.0), {"PROTOCOL": True})
    assert result["disposition"] == dev.PROMOTION_ELIGIBLE, result["stages"]
    assert result["counts"]["scorable_candidates"] == 90
    assert result["primary"]["ABS_NET_BP"] == pytest.approx(76.0, abs=0.5)


def test_losing_synthetic_market_is_rejected() -> None:
    episodes = _synthetic_population()
    result = dev.evaluate(episodes, _prices(episodes, 10.0, 30.0), {"PROTOCOL": True})
    assert result["disposition"] == dev.REJECTED


def test_support_failure_beats_attractive_economics() -> None:
    episodes = _synthetic_population()
    prices = _prices(episodes, 400.0, 0.0)

    def gappy(minute: int) -> dev.MinuteBar | None:
        return None if datetime.fromtimestamp(minute, UTC).year == 2023 else prices(minute)

    result = dev.evaluate(episodes, gappy, {"PROTOCOL": True})
    assert result["disposition"] == dev.BLOCKED
    assert result["stages"]["development"]["ABS_NET_BP_AT_LEAST_25"] is True


def test_integrity_failure_beats_everything() -> None:
    episodes = _synthetic_population()
    result = dev.evaluate(episodes, _prices(episodes, 100.0, 30.0), {"PROTOCOL": False})
    assert result["disposition"] == dev.INVALID_EXECUTION


def test_noisy_market_is_inconclusive_not_promoted() -> None:
    episodes = _synthetic_population()
    base = _prices(episodes, 0.0, 0.0)
    noise = {e.t: (1 if i % 2 else -1) * 400.0 + 120.0 for i, e in enumerate(episodes)}
    exit_times = {e.t + dev.EXIT_OFFSET: e.t for e in episodes}

    def noisy(minute: int) -> dev.MinuteBar | None:
        if minute in exit_times:
            t = exit_times[minute]
            candidate = next(e.candidate for e in episodes if e.t == t)
            bump = noise[t] if candidate else noise[t] - 60.0
            return _bar(100.0 * (1 + bump / 1e4))
        return base(minute)

    result = dev.evaluate(episodes, noisy, {"PROTOCOL": True})
    assert all(result["stages"]["development"].values()), result["stages"]["development"]
    assert result["disposition"] == dev.INCONCLUSIVE


def test_hungarian_assignment_is_exact() -> None:
    from itertools import permutations

    from scipy.optimize import linear_sum_assignment

    rng = np.random.default_rng(20260925)
    for rows, cols in ((1, 1), (2, 3), (3, 3), (4, 6), (5, 2)):
        weights = rng.integers(0, 5, size=(rows, cols)).astype(float)  # many exact ties
        pairs = dev.assignment(weights)
        assert len(pairs) == min(rows, cols)
        assert len({r for r, _ in pairs}) == len({c for _, c in pairs}) == len(pairs)
        total = sum(weights[r, c] for r, c in pairs)
        if rows <= cols:
            best = min(
                sum(weights[r, c] for r, c in enumerate(perm))
                for perm in permutations(range(cols), rows)
            )
        else:
            best = min(
                sum(weights[r, c] for c, r in enumerate(perm))
                for perm in permutations(range(rows), cols)
            )
        assert total == best
    for _ in range(20):
        weights = rng.random((12, 25))
        r, c = linear_sum_assignment(weights)
        pairs = dev.assignment(weights)
        assert sum(weights[i, j] for i, j in pairs) == pytest.approx(weights[r, c].sum())
