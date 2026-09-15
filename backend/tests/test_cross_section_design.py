"""CROSS_SECTION_COMMON_EFFECT_V1 design invariants and leakage barriers."""

import json
from pathlib import Path

import numpy as np
import pytest
from app.research.cross_section import (
    CROSS_SECTION_MESI_BPS,
    DEVELOPMENT_END_US,
    DEVELOPMENT_START_US,
    EFFECTIVE_ALPHA,
    LEVERAGED_TOKEN_SUFFIXES,
    LIQUIDITY_LOOKBACK_DAYS,
    MINIMUM_ASSET_CLUSTERS,
    MINIMUM_HISTORY_DAYS,
    MINIMUM_MEDIAN_DAILY_QUOTE_VOLUME_USDT,
    MINIMUM_WEEK_CLUSTERS,
    OUTCOME_HORIZON_HOURS,
    PROSPECTIVE_FAMILY_SIZE,
    QUOTE_ASSET,
    TARGET_POWER,
    UniversePolicyViolation,
    assert_no_real_effect_leakage,
    is_candidate_symbol,
    is_leveraged_token,
    mesi_bps,
    month_in_development,
)
from app.research.cross_section_lab import (
    SymbolBars,
    aligned_grid,
    daily_quote_volume,
    eligible_hours,
    feature_source,
    forward_outcome,
)
from app.research.cross_section_power import (
    PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS,
    Panel,
    TwoWayAbsorber,
    ZeroAlignmentForbidden,
    cluster_support,
    placebo_shift_grid,
    shift_signal,
    student_t_cdf,
    student_t_quantile,
    two_way_cluster_variance,
)
from app.research.evaluation_protocol import HOUR_US

ROOT = Path(__file__).resolve().parents[2]
DAY_US = 24 * HOUR_US


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _bars(
    symbol: str, start_us: int, hours: int, *, quote: float = 20_000_000.0 / 24
) -> SymbolBars:
    times = start_us + np.arange(hours, dtype=np.int64) * HOUR_US
    price = np.full(hours, 100.0)
    return SymbolBars(
        symbol,
        times,
        price.copy(),
        price + 1.0,
        price - 1.0,
        price.copy(),
        np.full(hours, 10.0),
        np.full(hours, quote),
        0,
        0,
        0,
        0,
    )


# --- universe policy ----------------------------------------------------------------
def test_quote_asset_must_be_usdt() -> None:
    assert QUOTE_ASSET == "USDT"
    assert is_candidate_symbol("ETHUSDT")
    assert not is_candidate_symbol("ETHBTC")
    assert not is_candidate_symbol("ETHBUSD")
    assert not is_candidate_symbol("USDT")


def test_leveraged_token_exclusion_rule_is_frozen_and_mechanical() -> None:
    assert LEVERAGED_TOKEN_SUFFIXES == ("UP", "DOWN", "BULL", "BEAR")
    for symbol in ("BTCUPUSDT", "BTCDOWNUSDT", "ETHBULLUSDT", "XRPBEARUSDT"):
        assert is_leveraged_token(symbol) and not is_candidate_symbol(symbol)
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        assert not is_leveraged_token(symbol)
    # The rule is applied to the symbol string alone, with no discretionary carve-outs.
    assert is_leveraged_token("JUPUSDT")


def test_universe_is_archive_derived_not_current_survivor_derived() -> None:
    protocol = read_json("research/protocols/CROSS-SECTION-FEASIBILITY-AND-POWER-V1.json")
    assert protocol["universe_policy"]["derivation"] == (
        "HISTORICAL_ARCHIVE_EVIDENCE_NOT_CURRENT_EXCHANGE_INFO"
    )
    assert protocol["data_source"]["current_exchange_info_used_as_listing_truth"] is False
    audit = read_json("reports/cross_section/CROSS-SECTION-SURVIVORSHIP-AUDIT-V1.json")
    assert audit["universe_is_current_survivor_list"] is False
    assert audit["delisted_or_archive_end_assets_retained"] is True
    assert audit["eligible_assets_whose_archive_ends_before_2024_12"] > 0
    assert audit["post_2024_information_used_for_inclusion"] is False


def test_no_future_survival_criterion_and_months_stay_in_window() -> None:
    assert month_in_development("2019-01") and month_in_development("2024-12")
    assert not month_in_development("2018-12") and not month_in_development("2025-01")
    protocol = read_json("research/protocols/CROSS-SECTION-FEASIBILITY-AND-POWER-V1.json")
    assert protocol["universe_policy"]["survival_to_2024_required"] is False
    assert protocol["causal_eligibility"]["future_longevity_is_eligibility_condition"] is False


# --- causal eligibility -------------------------------------------------------------
def test_thirty_day_history_rule_is_causal() -> None:
    assert MINIMUM_HISTORY_DAYS == 30
    bars = _bars("AAAUSDT", DEVELOPMENT_START_US, 29 * 24)
    assert len(eligible_hours(bars)) == 0


def test_liquidity_threshold_uses_trailing_completed_days_only() -> None:
    assert LIQUIDITY_LOOKBACK_DAYS == 30
    assert MINIMUM_MEDIAN_DAILY_QUOTE_VOLUME_USDT == 10_000_000.0
    thin = _bars("BBBUSDT", DEVELOPMENT_START_US, 90 * 24, quote=1_000.0)
    assert len(eligible_hours(thin)) == 0
    liquid = _bars("CCCUSDT", DEVELOPMENT_START_US, 90 * 24)
    hours = eligible_hours(liquid)
    assert len(hours) > 0
    # Eligibility starts only after 30 completed days, never on the first day.
    assert hours.min() >= DEVELOPMENT_START_US + MINIMUM_HISTORY_DAYS * DAY_US


def test_canonical_gaps_are_never_interpolated_and_block_eligibility() -> None:
    liquid = _bars("DDDUSDT", DEVELOPMENT_START_US, 90 * 24)
    keep = np.ones(len(liquid), dtype=bool)
    keep[40 * 24 : 40 * 24 + 5] = False  # a partial day can never be a complete day
    gapped = SymbolBars(
        "DDDUSDT",
        liquid.open_time[keep],
        liquid.open[keep],
        liquid.high[keep],
        liquid.low[keep],
        liquid.close[keep],
        liquid.volume[keep],
        liquid.quote_volume[keep],
        0,
        0,
        0,
        0,
    )
    days, totals = daily_quote_volume(gapped)
    assert np.isnan(totals).any()
    assert len(days) == 90  # the calendar axis stays contiguous across the gap
    assert len(eligible_hours(gapped)) < len(eligible_hours(liquid))


# --- frozen ALIGNED transfer --------------------------------------------------------
def test_aligned_gate_constants_are_unchanged() -> None:
    from app.research.continuation_lab import validate_config

    validate_config(
        {
            "strategy_version": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
            "variant": "ALIGNED",
            "feature_version": "CONTINUATION_FEATURES_V2",
            "breakout_hours": 24,
            "volume_baseline_hours": 24,
            "volume_multiplier": 2,
            "context_increments": 42,
            "up_to_down_ratio": 2,
            "stop_fraction": 0.02,
            "target_fraction": 0.04,
            "max_hold_minutes": 1440,
            "profiles": ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"],
        }
    )


def test_vectorized_aligned_matches_the_frozen_engine() -> None:
    rng = np.random.default_rng(20260916)
    hours = 4000
    times = DEVELOPMENT_START_US + np.arange(hours, dtype=np.int64) * HOUR_US
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, hours)))
    high = close * (1.0 + np.abs(rng.normal(0.0, 0.004, hours)))
    volume = np.abs(rng.lognormal(0.0, 0.8, hours))
    bars = SymbolBars(
        "EEEUSDT",
        times,
        close.copy(),
        high,
        close * 0.99,
        close,
        volume,
        np.full(hours, 1.0),
        0,
        0,
        0,
        0,
    )
    source = feature_source(bars)
    grid_hours, grid_emits = aligned_grid(bars)
    lookup = dict(zip(grid_hours.tolist(), grid_emits.tolist(), strict=True))
    compared = 0
    for hour in times.tolist():
        try:
            emits, _, _ = source.decision(int(hour), "ALIGNED")
        except Exception:
            assert hour not in lookup
            continue
        compared += 1
        assert hour in lookup and lookup[hour] == emits
    assert compared > 3000


def test_signal_support_reports_raw_unsuppressed_events() -> None:
    report = read_json("reports/cross_section/CROSS-SECTION-SIGNAL-SUPPORT-V1.json")
    assert report["events"] == "RAW_SIGNAL_EVENTS"
    assert report["occupancy_suppression_applied"] is False
    assert report["aligned_modified"] is False
    assert report["raw_signals"] > 0
    assert report["zero_alignment_outcome_inspected"] is False
    assert all(item["equivalent"] for item in report["vectorized_engine_equivalence"])


def test_direct_1h_reproduces_canonical_btc_aligned_semantics() -> None:
    report = read_json("reports/cross_section/CROSS-SECTION-BTC-1H-EQUIVALENCE-V1.json")
    assert report["DATA_SOURCE_STATUS"] == "PASS"
    assert report["identical_hour_key_set"] is True
    assert report["identical_decisions"] == report["both_decidable"] > 40_000
    assert report["canonical_aligned_signals"] == report["archive_aligned_signals"]
    assert report["canonical_only_decidable"] == 0
    assert report["archive_off_grid_rows_in_window"] == 0


# --- frozen outcome -----------------------------------------------------------------
def test_outcome_horizon_is_exactly_twenty_four_hours() -> None:
    assert OUTCOME_HORIZON_HOURS == 24
    bars = _bars("FFFUSDT", DEVELOPMENT_START_US, 48)
    bars.close[24] = 110.0
    outcome = forward_outcome(bars, int(bars.open_time[0]))
    assert outcome is not None
    assert outcome["terminal_us"] == int(bars.open_time[23])
    assert outcome["truncated"] is False


def test_terminal_price_is_never_interpolated_when_trading_stops() -> None:
    bars = _bars("GGGUSDT", DEVELOPMENT_START_US, 10)
    outcome = forward_outcome(bars, int(bars.open_time[0]))
    assert outcome is not None
    assert outcome["truncated"] is True
    assert outcome["terminal_us"] == int(bars.open_time[-1])


# --- pooled primary and inference ---------------------------------------------------
def test_exactly_one_pooled_primary_and_no_per_asset_selection() -> None:
    protocol = read_json("research/protocols/CROSS-SECTION-FEASIBILITY-AND-POWER-V1.json")
    assert protocol["primary_estimand"]["count"] == 1
    assert protocol["primary_estimand"]["fixed_effects"] == ["ASSET", "DECISION_TIME"]
    assert protocol["primary_estimand"]["per_asset_beta_is_primary"] is False
    assert protocol["primary_estimand"]["per_asset_beta_may_rescue"] is False
    assert protocol["primary_estimand"]["evaluated_at_true_alignment"] is False
    assert protocol["material_economic_hypotheses"] == 1
    assert protocol["one_hypothesis_per_asset"] is False


def test_two_way_cluster_dimensions_are_asset_and_utc_week() -> None:
    gate = read_json("reports/power/CROSS-SECTION-POWER-GATE-V1.json")
    assert gate["dependence"]["cluster_dimensions"] == [
        "ASSET_INSTRUMENT_EPOCH",
        "UTC_CALENDAR_WEEK",
    ]
    assert gate["dependence"]["covariance_identity"] == "V = V_asset + V_week - V_intersection"
    assert MINIMUM_ASSET_CLUSTERS == 30 and MINIMUM_WEEK_CLUSTERS == 100
    assert cluster_support(29, 500)["CLUSTER_SUPPORT_STATUS"] == "REDESIGN_REQUIRED"
    assert cluster_support(500, 99)["CLUSTER_SUPPORT_STATUS"] == "REDESIGN_REQUIRED"
    assert cluster_support(30, 100)["CLUSTER_SUPPORT_STATUS"] == "PASS"


def test_two_way_absorber_annihilates_both_factors() -> None:
    rng = np.random.default_rng(7)
    rows = 5000
    asset = rng.integers(0, 12, rows)
    time = rng.integers(0, 400, rows)
    values = rng.normal(size=rows) + asset * 3.0 + time * 0.25
    absorber = TwoWayAbsorber(asset, time, 12, 400)
    diagnostics = absorber.diagnostics(values)
    assert diagnostics["max_absolute_asset_mean"] < 1e-10
    assert diagnostics["max_absolute_time_mean"] < 1e-10


def test_two_way_cluster_variance_uses_inclusion_exclusion() -> None:
    rng = np.random.default_rng(11)
    rows = 400
    regressor = rng.normal(size=rows)
    residual = rng.normal(size=rows)
    asset = rng.integers(0, 8, rows)
    week = rng.integers(0, 20, rows)
    intersection = np.unique(asset * 20 + week, return_inverse=True)[1]
    result = two_way_cluster_variance(regressor, residual, asset, week, intersection)
    expected = result["meat_asset"] + result["meat_week"] - result["meat_intersection"]
    assert result["meat"] == pytest.approx(expected)
    assert result["variance"] == pytest.approx(expected / result["bread"] ** 2)


# --- multiplicity, threshold, power -------------------------------------------------
def test_prospective_family_size_alpha_mesi_and_power_target() -> None:
    assert PROSPECTIVE_FAMILY_SIZE == 13
    assert EFFECTIVE_ALPHA == pytest.approx(0.05 / 13)
    assert mesi_bps() == CROSS_SECTION_MESI_BPS == 24.0
    assert TARGET_POWER == 0.8
    gate = read_json("reports/power/CROSS-SECTION-POWER-GATE-V1.json")
    assert gate["multiplicity"]["prospective_family_size"] == 13
    assert gate["multiplicity"]["effective_alpha"] == pytest.approx(0.05 / 13)
    assert gate["multiplicity"]["UNQUANTIFIED_PRE_REPO_EXPOSURE"] is True
    assert gate["power"]["target_power"] == 0.8
    assert gate["economic_threshold"]["lowered_after_power"] is False


def test_student_t_helpers_match_reference_values() -> None:
    # Reference quantiles from the Student-t distribution, to six decimals.
    assert student_t_quantile(0.95, 10) == pytest.approx(1.812461, abs=1e-5)
    assert student_t_quantile(0.99, 30) == pytest.approx(2.457262, abs=1e-5)
    assert student_t_quantile(1 - 0.05 / 13, 183) == pytest.approx(2.695100, abs=1e-5)
    assert student_t_cdf(0.0, 50) == pytest.approx(0.5)
    assert student_t_cdf(2.0, 183) == pytest.approx(0.976510, abs=1e-5)
    assert 0.0 <= student_t_cdf(-5.0, 183) <= 1.0


# --- leakage barriers ---------------------------------------------------------------
def _panel(assets: int, length: int) -> Panel:
    rows = assets * length
    asset_index = np.repeat(np.arange(assets), length)
    time_index = np.tile(np.arange(length), assets)
    signal = np.zeros(rows)
    signal[::97] = 1.0
    return Panel(
        asset_index=asset_index,
        time_index=time_index,
        week_index=time_index // 168,
        outcome_bps=np.zeros(rows),
        signal=signal,
        asset_labels=[f"A{i}" for i in range(assets)],
        asset_offsets=np.arange(assets + 1) * length,
        time_count=length,
    )


def test_placebo_rejects_zero_shift_and_the_near_zero_band() -> None:
    panel = _panel(3, 2000)
    with pytest.raises(ZeroAlignmentForbidden):
        shift_signal(panel, 0)
    for shift in (1, 167, -167):
        with pytest.raises(ZeroAlignmentForbidden):
            shift_signal(panel, shift)
    assert PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS == 168
    shifted = shift_signal(panel, 500)
    assert shifted.sum() == panel.signal.sum()  # event count is preserved exactly


def test_placebo_shift_grid_never_admits_a_near_zero_displacement() -> None:
    lengths = np.array([700, 5000, 40000])
    grid = placebo_shift_grid(lengths, 400)
    assert grid["shifts"]
    for shift in grid["shifts"]:
        assert abs(shift) >= PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS
        for length in lengths:
            effective = shift % int(length)
            assert min(effective, int(length) - effective) >= PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS


def test_artifacts_carry_no_real_pooled_effect() -> None:
    for relative in (
        "reports/power/CROSS-SECTION-POWER-GATE-V1.json",
        "reports/cross_section/CROSS-SECTION-PLACEBO-CALIBRATION-V1.json",
        "reports/cross_section/CROSS-SECTION-SIGNAL-SUPPORT-V1.json",
        "reports/cross_section/CROSS-SECTION-UNIVERSE-FEASIBILITY-V1.json",
        "reports/cross_section/CROSS-SECTION-SURVIVORSHIP-AUDIT-V1.json",
    ):
        payload = read_json(relative)
        assert_no_real_effect_leakage(payload)
        assert payload["ACTUAL_CROSS_SECTION_EFFECT_OBSERVED"] is False
    with pytest.raises(UniversePolicyViolation):
        assert_no_real_effect_leakage({"nested": {"pooled_beta": 1.0}})
    with pytest.raises(UniversePolicyViolation):
        assert_no_real_effect_leakage({"rows": [{"per_asset_beta": 0.0}]})


def test_gate_blocks_preregistration_when_any_prerequisite_fails() -> None:
    gate = read_json("reports/power/CROSS-SECTION-POWER-GATE-V1.json")
    failing = [key for key, value in gate["prerequisite_gates"].items() if value != "PASS"]
    powered = gate["power"]["power_at_MESI"] >= TARGET_POWER
    if failing or not powered:
        assert gate["CROSS_SECTION_POWER_GATE_STATUS"] == "REDESIGN_REQUIRED"
        assert gate["preregistration_authorized"] is False
        assert gate["actual_execution_authorized"] is False
    assert all(value is False for value in gate["leakage_guard"].values())


def test_development_window_bounds_are_frozen() -> None:
    assert DEVELOPMENT_START_US == 1_546_300_800_000_000
    assert DEVELOPMENT_END_US == 1_735_689_540_000_000


# --- product and accounting ---------------------------------------------------------
def test_product_universe_and_accounting_are_unchanged() -> None:
    state = read_json("state/current_state.json")
    record = state["cross_section_feasibility"]
    assert record["product_universe"] == "BTCUSDT_SPOT_V1_UNCHANGED"
    assert record["cross_section_product_authorized"] is False
    assert record["multi_asset_trading_implemented"] is False
    assert record["material_economic_hypotheses_executed"] == 0
    assert record["zero_alignment_effect_observed"] is False
    assert record["aligned_modified"] is False
    assert record["preregistration_authorized"] is False
    assert state["symbols"] == ["BTCUSDT"]
    assert state["experiments_completed"] == 26
    assert state["statistical_governance"]["known_discovery_family_size"] == 12
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["adaptive_search"]["sealed_queries"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False
    assert state["paper_trading"]["real_money"] is False


def test_no_multi_asset_trading_surface_exists() -> None:
    from app.main import app

    for route in app.routes:
        path = str(getattr(route, "path", "")).lower()
        assert "cross_section" not in path and "universe" not in path
        assert "multi_asset" not in path
    source = "\n".join(
        item.read_text(encoding="utf-8") for item in (ROOT / "backend/app/product").rglob("*.py")
    )
    assert "cross_section" not in source
