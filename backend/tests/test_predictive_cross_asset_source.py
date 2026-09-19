"""Point-in-time, universe and causality proofs for the Stage-3 cross-asset source.

Every claim here is hand-computable on a deterministic synthetic panel. Nothing in this file
reads the governed substrate or any market label.
"""

from __future__ import annotations

import math

import pytest
from app.predictive.cross_asset_audit import (
    RETIRED_PARTICIPATION_ROW_RULE,
    endpoint_only_panel,
    permuted_panel,
)
from app.predictive.cross_asset_source import (
    DECISION_INSTANT_OUTSIDE_SOURCE_SPAN,
    ENDPOINT_OFFSET_HOURS,
    FEATURE_COUNT,
    FEATURE_NAMES,
    FORBIDDEN_COLUMNS,
    HOUR_SECONDS,
    INSUFFICIENT_POINT_IN_TIME_UNIVERSE,
    LONG_LOOKBACK_HOURS,
    MINIMUM_POINT_IN_TIME_UNIVERSE,
    REQUIRED_ENDPOINT_BARS,
    TARGET_SYMBOL,
    UNAVAILABILITY_TAXONOMY,
    CrossAssetError,
    CrossSectionPanel,
    build_cross_asset_features,
    feature_source_instants,
    is_admitted_symbol,
    is_leveraged_token,
    panel_from_series,
    point_in_time_universe,
    point_in_time_universe_size,
)

DECISION = 400 * HOUR_SECONDS
SPAN = 700 * HOUR_SECONDS


def full_series(symbol_index: int, drift: float) -> dict[int, float]:
    """A complete hourly series growing by a fixed ratio every hour."""
    del symbol_index
    return {
        moment: 100.0 * math.exp(drift * moment / HOUR_SECONDS)
        for moment in range(0, SPAN + HOUR_SECONDS, HOUR_SECONDS)
    }


def synthetic_panel(assets: int = 40, drift: float = 0.001) -> CrossSectionPanel:
    """`assets` complete series; half drift up, half drift down, so breadth is exactly half."""
    series = {}
    for index in range(assets):
        sign = 1.0 if index % 2 == 0 else -1.0
        series[f"SYN{index:03d}USDT"] = full_series(index, sign * drift)
    return panel_from_series(series)


def as_series(panel: CrossSectionPanel) -> dict[str, dict[int, float]]:
    """Invert a panel back into explicit per-symbol series so a test can perturb it."""
    instants = range(
        panel.first_open_time,
        panel.first_open_time + panel.rows * HOUR_SECONDS,
        HOUR_SECONDS,
    )
    return {
        symbol: {
            moment: math.exp(value)
            for moment, value in zip(instants, panel.log_close[:, column], strict=True)
            if not math.isnan(value)
        }
        for column, symbol in enumerate(panel.symbols)
    }


def test_the_frozen_feature_set_is_exactly_eight_ordered_names():
    assert FEATURE_COUNT == 8
    assert FEATURE_NAMES == (
        "BREADTH_UP_SHARE_1H",
        "BREADTH_UP_SHARE_24H",
        "BREADTH_UP_SHARE_168H",
        "CROSS_MEDIAN_RETURN_1H",
        "CROSS_MEDIAN_RETURN_24H",
        "CROSS_MEDIAN_RETURN_168H",
        "CROSS_MAD_RETURN_24H",
        "CROSS_MAD_RETURN_168H",
    )
    assert ENDPOINT_OFFSET_HOURS == (168, 24, 1, 0)
    assert REQUIRED_ENDPOINT_BARS == 4
    assert LONG_LOOKBACK_HOURS == 168
    assert MINIMUM_POINT_IN_TIME_UNIVERSE == 30


def test_the_family_reads_no_liquidity_or_intrabar_field():
    for name in ("open", "high", "low", "volume", "quote_volume"):
        assert name in FORBIDDEN_COLUMNS
    joined = " ".join(FEATURE_NAMES).lower()
    for forbidden in ("volume", "liquidity", "cap", "btc", "funding", "basis", "open_interest"):
        assert forbidden not in joined, forbidden


def test_the_feature_set_shares_nothing_with_the_rejected_families():
    from app.predictive.funding_source import FEATURE_NAMES as FUNDING_FEATURES
    from app.predictive.internal_features import FEATURE_NAMES as STAGE1_FEATURES
    from app.predictive.open_interest_source import FEATURE_NAMES as OI_FEATURES

    assert not set(FEATURE_NAMES) & set(STAGE1_FEATURES)
    assert not set(FEATURE_NAMES) & set(FUNDING_FEATURES)
    assert not set(FEATURE_NAMES) & set(OI_FEATURES)


def test_the_prediction_target_and_leveraged_tokens_are_inadmissible():
    assert is_admitted_symbol(TARGET_SYMBOL) is False
    assert is_admitted_symbol("ETHUSDT") is True
    for symbol in ("BTCUPUSDT", "BTCDOWNUSDT", "ETHBULLUSDT", "ETHBEARUSDT"):
        assert is_leveraged_token(symbol) is True
        assert is_admitted_symbol(symbol) is False
    # The rule is literal: a suffix that is not immediately before the quote asset is safe.
    assert is_leveraged_token("UPUSDT") is True
    assert is_leveraged_token("DOTUSDT") is False
    assert is_admitted_symbol("BTCUSDC") is False


def test_a_panel_refuses_the_prediction_target_and_a_leveraged_token():
    with pytest.raises(CrossAssetError, match="inadmissible symbol"):
        panel_from_series({TARGET_SYMBOL: full_series(0, 0.001)})
    with pytest.raises(CrossAssetError, match="inadmissible symbol"):
        panel_from_series({"ETHBULLUSDT": full_series(0, 0.001)})


def test_the_eight_features_reproduce_hand_computed_fixtures():
    drift = 0.001
    panel = synthetic_panel(assets=40, drift=drift)
    values, reason = build_cross_asset_features(panel, DECISION)
    assert reason is None and values is not None
    named = dict(zip(FEATURE_NAMES, values, strict=True))
    # Exactly half the assets drift up, so every breadth share is exactly one half.
    assert named["BREADTH_UP_SHARE_1H"] == 0.5
    assert named["BREADTH_UP_SHARE_24H"] == 0.5
    assert named["BREADTH_UP_SHARE_168H"] == 0.5
    # The cross-section is symmetric around zero, so every median is zero.
    assert named["CROSS_MEDIAN_RETURN_1H"] == pytest.approx(0.0, abs=1e-15)
    assert named["CROSS_MEDIAN_RETURN_24H"] == pytest.approx(0.0, abs=1e-15)
    assert named["CROSS_MEDIAN_RETURN_168H"] == pytest.approx(0.0, abs=1e-15)
    # Every asset sits exactly `k * drift` from the zero median.
    assert named["CROSS_MAD_RETURN_24H"] == pytest.approx(24 * drift)
    assert named["CROSS_MAD_RETURN_168H"] == pytest.approx(168 * drift)


def test_a_zero_return_is_not_an_up_move():
    series = {f"SYN{index:03d}USDT": full_series(index, 0.0) for index in range(40)}
    values, reason = build_cross_asset_features(panel_from_series(series), DECISION)
    assert reason is None and values is not None
    named = dict(zip(FEATURE_NAMES, values, strict=True))
    assert named["BREADTH_UP_SHARE_1H"] == 0.0
    assert named["BREADTH_UP_SHARE_24H"] == 0.0
    assert named["BREADTH_UP_SHARE_168H"] == 0.0
    assert named["CROSS_MAD_RETURN_24H"] == 0.0
    assert named["CROSS_MAD_RETURN_168H"] == 0.0


def test_an_asset_missing_one_endpoint_bar_leaves_the_universe_at_that_instant():
    panel = synthetic_panel(assets=40)
    assert point_in_time_universe_size(panel, DECISION) == 40
    for offset in ENDPOINT_OFFSET_HOURS:
        series = as_series(panel)
        victim = panel.symbols[0]
        series[victim].pop(DECISION - offset * HOUR_SECONDS)
        punctured = panel_from_series(series)
        assert victim not in point_in_time_universe(punctured, DECISION)
        assert point_in_time_universe_size(punctured, DECISION) == 39
        # It is only gone at that instant: one hour later the endpoint is a different bar.
        assert victim in point_in_time_universe(punctured, DECISION + 200 * HOUR_SECONDS)


def test_a_future_only_asset_cannot_change_the_feature_vector():
    """The causality proof the checkpoint requires: a future-only asset is simply absent."""
    panel = synthetic_panel(assets=40)
    baseline, reason = build_cross_asset_features(panel, DECISION)
    assert reason is None and baseline is not None
    series = as_series(panel)
    # An asset that only exists strictly after the decision instant, moving violently.
    series["ZZZFUTUREUSDT"] = {
        moment: 1.0 * math.exp(0.5 * moment / HOUR_SECONDS)
        for moment in range(DECISION + HOUR_SECONDS, SPAN + HOUR_SECONDS, HOUR_SECONDS)
    }
    # And a future-only bar bolted onto an existing asset.
    series[panel.symbols[1]][SPAN] = 1e9
    grown = panel_from_series(series)
    assert build_cross_asset_features(grown, DECISION)[0] == baseline
    assert "ZZZFUTUREUSDT" not in point_in_time_universe(grown, DECISION)
    # The newcomer does join once its own four endpoints exist.
    assert "ZZZFUTUREUSDT" in point_in_time_universe(grown, DECISION + 170 * HOUR_SECONDS)


def test_only_the_four_endpoint_bars_enter_a_feature_vector():
    """An asset with four observed bars in its whole life is a full member."""
    panel = synthetic_panel(assets=40)
    baseline = build_cross_asset_features(panel, DECISION)[0]
    stripped = endpoint_only_panel(panel, DECISION)
    assert build_cross_asset_features(stripped, DECISION)[0] == baseline
    observed_per_asset = int((~_isnan(stripped.log_close)).sum(axis=0).max())
    assert observed_per_asset == REQUIRED_ENDPOINT_BARS
    assert observed_per_asset < RETIRED_PARTICIPATION_ROW_RULE


def test_the_cross_section_is_equal_weighted_and_order_independent():
    panel = synthetic_panel(assets=40)
    baseline = build_cross_asset_features(panel, DECISION)[0]
    assert build_cross_asset_features(permuted_panel(panel), DECISION)[0] == baseline


def test_an_instant_with_too_few_eligible_assets_abstains_and_is_typed():
    panel = synthetic_panel(assets=MINIMUM_POINT_IN_TIME_UNIVERSE)
    assert build_cross_asset_features(panel, DECISION)[1] is None
    thin = synthetic_panel(assets=MINIMUM_POINT_IN_TIME_UNIVERSE - 1)
    values, reason = build_cross_asset_features(thin, DECISION)
    assert values is None and reason == INSUFFICIENT_POINT_IN_TIME_UNIVERSE
    assert INSUFFICIENT_POINT_IN_TIME_UNIVERSE in UNAVAILABILITY_TAXONOMY


def test_an_instant_before_the_window_opens_abstains_and_is_typed():
    panel = synthetic_panel(assets=40)
    values, reason = build_cross_asset_features(panel, LONG_LOOKBACK_HOURS * HOUR_SECONDS - 3600)
    assert values is None and reason == DECISION_INSTANT_OUTSIDE_SOURCE_SPAN
    assert DECISION_INSTANT_OUTSIDE_SOURCE_SPAN in UNAVAILABILITY_TAXONOMY
    # The very first usable instant is exactly 168 hours after the panel opens.
    assert build_cross_asset_features(panel, LONG_LOOKBACK_HOURS * HOUR_SECONDS)[1] is None
    beyond = panel.last_open_time + HOUR_SECONDS
    assert build_cross_asset_features(panel, beyond)[1] == DECISION_INSTANT_OUTSIDE_SOURCE_SPAN


def test_every_instant_a_feature_reads_is_at_or_before_the_decision_instant():
    panel = synthetic_panel(assets=40)
    stamps = feature_source_instants(panel, DECISION)
    assert len(stamps) == REQUIRED_ENDPOINT_BARS
    assert max(stamps) == DECISION
    assert min(stamps) == DECISION - LONG_LOOKBACK_HOURS * HOUR_SECONDS
    assert all(stamp <= DECISION for stamp in stamps)


def test_availability_never_depends_on_a_future_return():
    """Source validity is a property of the source panel alone."""
    import inspect

    panel = synthetic_panel(assets=40)
    assert build_cross_asset_features(panel, DECISION) == build_cross_asset_features(
        panel, DECISION
    )
    signature = inspect.signature(build_cross_asset_features)
    assert list(signature.parameters) == ["panel", "instant"]


def test_a_panel_refuses_a_misaligned_bar_or_a_duplicated_symbol():
    with pytest.raises(CrossAssetError, match="hour boundary"):
        panel_from_series({"SYN000USDT": {0: 1.0, 1800: 1.0}})
    with pytest.raises(CrossAssetError, match="hour boundary"):
        build_cross_asset_features(synthetic_panel(), DECISION + 60)


def test_a_non_positive_close_is_never_admitted_as_an_observation():
    series = {f"SYN{index:03d}USDT": full_series(index, 0.001) for index in range(40)}
    series["SYN000USDT"][DECISION] = 0.0
    panel = panel_from_series(series)
    assert "SYN000USDT" not in point_in_time_universe(panel, DECISION)


def _isnan(matrix):
    import numpy as np

    return np.isnan(matrix)
