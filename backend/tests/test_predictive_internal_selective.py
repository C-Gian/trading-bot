from __future__ import annotations

import json
import math

import pytest
from app.predictive import DOWN, NEUTRAL, UP
from app.predictive.internal_features import (
    LOOKBACK_BAR_INCOMPLETE,
    LOOKBACK_BAR_MISSING,
    NEGATIVE_VOLUME,
    NON_POSITIVE_CLOSE,
    REQUIRED_BARS,
    ZERO_EFFICIENCY_DENOMINATOR_VALUE,
    ZERO_RANGE_CLOSE_POSITION_VALUE,
    OhlcvBar,
    assert_feature_causality,
    build_feature_vector,
    feature_source_open_times,
    index_ohlcv,
)
from app.predictive.internal_selective import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    EXPERIMENT_IDS,
    FAMILY,
    FAMILY_SIZE,
    FEATURE_PROOF_PATH,
    HYPOTHESIS_IDS,
    INTERVAL_MASS,
    PER_CONFIGURATION_ALPHA,
    PRIOR_V1_RESULT_PATHS,
    PRIOR_V2_RESULT_PATHS,
    ROOT,
    TERMINAL_CLASSIFICATIONS,
    admission,
    feature_cache,
    preregistration,
    search_plan,
)
from app.predictive.internal_selective_features import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    INHERITED_FROM,
    feature_contract,
    reconcile_with_v1,
)
from app.predictive.internal_selective_model import (
    CALIBRATION_EMBARGO_HOURS,
    HGBR_MODEL_VERSION,
    HGBR_PARAMETERS,
    INFERENCE_SEED,
    LINEAR_MODEL_VERSION,
    LINEAR_PARAMETERS,
    PLATT_PARAMETERS,
    InternalSelectiveModelError,
    calibration_split,
    fit_probability_head,
    model_specification,
)
from app.predictive.labels import HOUR_SECONDS, Label
from app.predictive.selective_long import ACTION_THRESHOLD, GATE_NAMES

HOUR = HOUR_SECONDS
BASE = 1_600_000_000 - 1_600_000_000 % HOUR


def series(count: int, *, start: float = 100.0, step: float = 0.5) -> list[OhlcvBar]:
    bars = []
    for index in range(count):
        close = start + step * index
        bars.append(
            OhlcvBar(
                open_time=BASE + index * HOUR,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=10.0 + index % 7,
                complete=True,
            )
        )
    return bars


def valid_index() -> tuple[dict[int, OhlcvBar], int]:
    bars = series(REQUIRED_BARS + 48)
    return index_ohlcv(bars), bars[REQUIRED_BARS - 1].open_time


# --- feature identity: inherited, never rewritten ---------------------------------------


def test_feature_identity_inherits_the_frozen_v1_definition() -> None:
    assert FEATURE_SET_VERSION == "PREDICTIVE_V2_INTERNAL_CAUSAL_FEATURES_V1"
    assert INHERITED_FROM == "PREDICTIVE_INTERNAL_CAUSAL_FEATURES_V1"
    contract = feature_contract()
    assert contract["definition_rewritten"] is False
    assert contract["definition_module"] == "backend/app/predictive/internal_features.py"
    assert contract["stage1_substrate_debt"] == (
        "DEFERRED_UNREPAIRED_169_HOUR_RULE_REUSED_UNCHANGED"
    )


def test_feature_set_is_exactly_the_frozen_eighteen_in_order() -> None:
    assert FEATURE_COUNT == 18
    assert FEATURE_NAMES == (
        "logret_1h",
        "logret_6h",
        "logret_24h",
        "logret_72h",
        "logret_168h",
        "rv_6h",
        "rv_24h",
        "rv_72h",
        "rv_168h",
        "signed_efficiency_24h",
        "signed_efficiency_72h",
        "signed_efficiency_168h",
        "up_fraction_24h",
        "up_fraction_168h",
        "close_position_24h",
        "close_position_168h",
        "log_volume_relative_24h",
        "log_volume_regime_24_168h",
    )


def test_fixed_fixture_vectors_reconcile_with_the_v1_builder() -> None:
    index, instant = valid_index()
    fixtures = tuple(instant + offset * HOUR for offset in range(0, 40, 7))
    reconciliation = reconcile_with_v1(index, fixtures)
    assert reconciliation["identical_to_v1_definition"] is True
    assert reconciliation["matched"] == len(fixtures)
    assert reconciliation["mismatched"] == []


# --- causality --------------------------------------------------------------------------


def test_mutating_any_bar_after_t_cannot_change_the_vector_at_t() -> None:
    index, instant = valid_index()
    baseline, reason = build_feature_vector(index, instant)
    assert baseline is not None and reason is None
    mutated = dict(index)
    for open_time in list(mutated):
        if open_time > instant:
            mutated[open_time] = OhlcvBar(
                open_time=open_time,
                high=9.9e7,
                low=1e-7,
                close=4.2e6,
                volume=7.5e5,
                complete=True,
            )
    assert build_feature_vector(mutated, instant)[0] == baseline


def test_a_guarded_index_proves_no_future_bar_is_requested() -> None:
    index, instant = valid_index()
    assert_feature_causality(index, instant)


def test_the_causal_surface_is_exactly_the_169_bars_ending_at_t() -> None:
    _, instant = valid_index()
    sources = feature_source_open_times(instant)
    assert len(sources) == REQUIRED_BARS == 169
    assert sources[0] == instant - 168 * HOUR
    assert sources[-1] == instant
    assert all(later - earlier == HOUR for earlier, later in zip(sources, sources[1:]))


@pytest.mark.parametrize("hours", [1, 6, 24, 72, 168])
def test_logret_window_endpoints_are_exact(hours: int) -> None:
    index, instant = valid_index()
    values, _ = build_feature_vector(index, instant)
    assert values is not None
    position = {1: 0, 6: 1, 24: 2, 72: 3, 168: 4}[hours]
    expected = math.log(index[instant].close / index[instant - hours * HOUR].close)
    assert values[position] == pytest.approx(expected, rel=1e-12)


# --- availability: the frozen V1 rule, not repaired --------------------------------------


def test_a_missing_lookback_bar_fails_closed() -> None:
    index, instant = valid_index()
    oldest = feature_source_open_times(instant)[0]
    assert build_feature_vector(
        {key: value for key, value in index.items() if key != oldest}, instant
    ) == (None, LOOKBACK_BAR_MISSING)


def test_an_incomplete_lookback_bar_fails_closed() -> None:
    index, instant = valid_index()
    oldest = feature_source_open_times(instant)[0]
    bar = index[oldest]
    index[oldest] = OhlcvBar(
        open_time=oldest,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
        complete=False,
    )
    assert build_feature_vector(index, instant) == (None, LOOKBACK_BAR_INCOMPLETE)


def test_a_non_positive_close_and_a_negative_volume_fail_closed() -> None:
    index, instant = valid_index()
    oldest = feature_source_open_times(instant)[0]
    bad_close = dict(index)
    bad_close[oldest] = OhlcvBar(oldest, 1.0, 0.0, 0.0, 1.0, True)
    assert build_feature_vector(bad_close, instant) == (None, NON_POSITIVE_CLOSE)
    bad_volume = dict(index)
    bar = index[oldest]
    bad_volume[oldest] = OhlcvBar(oldest, bar.high, bar.low, bar.close, -1.0, True)
    assert build_feature_vector(bad_volume, instant) == (None, NEGATIVE_VOLUME)


def test_the_two_named_degenerate_denominators_keep_their_frozen_values() -> None:
    flat = index_ohlcv(series(REQUIRED_BARS, step=0.0))
    instant = BASE + (REQUIRED_BARS - 1) * HOUR
    values, _ = build_feature_vector(flat, instant)
    assert values is not None
    assert all(values[position] == ZERO_EFFICIENCY_DENOMINATOR_VALUE for position in (9, 10, 11))

    zero_range = index_ohlcv(
        [
            OhlcvBar(BASE + position * HOUR, 100.0, 100.0, 100.0, 5.0, True)
            for position in range(REQUIRED_BARS)
        ]
    )
    flat_values, _ = build_feature_vector(zero_range, instant)
    assert flat_values is not None
    assert all(flat_values[position] == ZERO_RANGE_CLOSE_POSITION_VALUE for position in (14, 15))


def test_feature_unavailability_is_counted_and_never_imputed() -> None:
    bars = series(REQUIRED_BARS + 10)
    index = index_ohlcv(bars)
    del index[bars[0].open_time]
    labels = [
        Label(
            open_time=bar.open_time,
            decision_close=bar.close,
            horizon_close=bar.close * 1.01,
            r_24h=0.01,
            direction=UP,
        )
        for bar in bars[REQUIRED_BARS - 1 :]
    ]
    cache, reasons = feature_cache(index, labels)
    assert len(labels) - len(cache) == sum(reasons.values()) == 1
    assert reasons[LOOKBACK_BAR_MISSING] == 1
    assert labels[0].open_time not in cache


# --- frozen family design ----------------------------------------------------------------


def test_the_family_is_exactly_two_configurations_with_the_declared_identities() -> None:
    assert FAMILY == "PREDICTIVE_V2_INTERNAL_STRUCTURE_SELECTIVE_FAMILY_V1"
    assert FAMILY_SIZE == 2
    assert CONFIGURATION_ORDER == (LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION)
    assert EXPERIMENT_IDS == {
        "V2_INTERNAL_LINEAR_V1": "EXP-PRED-V2-003-INTERNAL-LINEAR",
        "V2_INTERNAL_HGBR_V1": "EXP-PRED-V2-004-INTERNAL-HGBR",
    }
    assert HYPOTHESIS_IDS == {
        "V2_INTERNAL_LINEAR_V1": "H-PRED-V2-INTERNAL-001",
        "V2_INTERNAL_HGBR_V1": "H-PRED-V2-INTERNAL-002",
    }
    assert TERMINAL_CLASSIFICATIONS[LINEAR_MODEL_VERSION] == (
        "ADVANCE_V2_INTERNAL_LINEAR_V1",
        "NO_ADVANCE_V2_INTERNAL_LINEAR_V1",
    )
    assert TERMINAL_CLASSIFICATIONS[HGBR_MODEL_VERSION] == (
        "ADVANCE_V2_INTERNAL_HGBR_V1",
        "NO_ADVANCE_V2_INTERNAL_HGBR_V1",
    )


def test_the_frozen_inference_and_threshold_are_unchanged() -> None:
    plan = search_plan()
    assert ACTION_THRESHOLD == 0.60
    assert plan["action_threshold"] == 0.60
    assert INFERENCE_SEED == 20260922
    assert plan["inference"]["seed"] == 20260922
    assert plan["inference"]["block_length_hours"] == 48
    assert plan["inference"]["replicates"] == 10_000
    assert plan["inference"]["familywise_alpha"] == 0.05
    assert PER_CONFIGURATION_ALPHA == 0.025
    assert INTERVAL_MASS == 0.975
    assert plan["inference"]["blocks_cross_fold_boundaries"] is False
    assert plan["all_ten_conditions_must_hold"] is True
    assert list(plan["advancement"]) == list(GATE_NAMES)
    assert len(GATE_NAMES) == 10


def test_the_frozen_model_parameters_match_the_declared_design() -> None:
    assert LINEAR_PARAMETERS == {
        "penalty": "l2",
        "C": 1.0,
        "class_weight": None,
        "fit_intercept": True,
        "solver": "lbfgs",
        "max_iter": 2000,
        "tol": 1e-8,
    }
    assert HGBR_PARAMETERS == {
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 15,
        "min_samples_leaf": 50,
        "l2_regularization": 1.0,
        "max_bins": 255,
        "early_stopping": False,
        "random_state": 20260922,
    }
    assert PLATT_PARAMETERS["penalty"] is None
    for model in CONFIGURATION_ORDER:
        specification = model_specification(model)
        assert specification["magnitude_estimator"] is None
        assert specification["hyperparameter_search"] is False
        assert specification["threshold_search"] is False
        assert specification["v1_fitted_model_or_prediction_loaded"] is False
        assert specification["calibration_embargo_hours"] == CALIBRATION_EMBARGO_HOURS == 48


def test_the_search_budget_is_two_with_no_result_dependent_fork() -> None:
    budget = search_plan()["search_budget"]
    assert budget["configurations_planned"] == budget["configurations_reserved"] == 2
    assert budget["result_dependent_forks"] == 0


def test_the_plan_declares_every_anti_rescue_boundary() -> None:
    boundaries = search_plan()["boundaries"]
    assert boundaries["v1_family_rescued_or_rescored"] is False
    assert boundaries["v1_model_probability_tail_consulted"] is False
    assert boundaries["v1_fitted_model_or_prediction_loaded"] is False
    assert boundaries["calendar_v2_family_tuned_or_reused_as_model_evidence"] is False
    assert boundaries["stage1_substrate_debt_repaired"] is False
    assert boundaries["real_money"] is False
    controls = search_plan()["controls"]
    assert controls["primary"] == "FULL_FOLD_UP_RATE"
    assert controls["primary_visible_to_fitting_calibration_or_selection"] is False
    assert controls["feature_availability_redefines_primary_control"] is False


def test_each_preregistration_declares_one_trial_and_no_search() -> None:
    for model in CONFIGURATION_ORDER:
        record = preregistration(model)
        assert record["status"] == "PREREGISTERED_BEFORE_FIRST_OUTER_PREDICTION"
        assert record["trial_budget"] == 1
        assert record["parameter_search"] is False
        assert record["threshold_search"] is False
        assert record["feature_search"] is False
        assert record["post_result_tuning"] is False
        assert record["magnitude_declared"] is False
        assert record["v1_model_outputs_used"] is False
        assert record["sealed_query_authorized"] is False
        assert record["minimum_important_effect"] == 0.05


# --- fitting procedure -------------------------------------------------------------------


def test_the_calibration_split_is_chronological_with_a_48h_embargo() -> None:
    open_times = [BASE + index * HOUR for index in range(1000)]
    split = calibration_split(open_times)
    assert split.boundary_index == 800
    assert split.boundary_open_time == open_times[800]
    assert split.base_fit_rows + split.calibration_rows + split.dropped_to_embargo == 1000
    # Base fit keeps `moment + 48h <= boundary`; calibration keeps `moment >= boundary`. On a
    # gapless hourly grid that leaves the 47 rows strictly inside (boundary - 48h, boundary).
    assert split.dropped_to_embargo == CALIBRATION_EMBARGO_HOURS - 1 == 47
    assert split.base_fit_rows == 800 - CALIBRATION_EMBARGO_HOURS + 1
    assert split.calibration_rows == 200


def test_a_non_chronological_training_portion_fails_closed() -> None:
    with pytest.raises(InternalSelectiveModelError):
        calibration_split([BASE + 2 * HOUR, BASE + HOUR])


def test_a_fitting_side_without_both_classes_fails_closed() -> None:
    count = 400
    open_times = [BASE + index * HOUR for index in range(count)]
    features = [tuple(float(index % 5) for _ in range(FEATURE_COUNT)) for index in range(count)]
    directions = [UP] * count
    with pytest.raises(InternalSelectiveModelError):
        fit_probability_head(LINEAR_MODEL_VERSION, open_times, features, directions)


def test_a_non_directional_training_row_is_refused() -> None:
    open_times = [BASE + index * HOUR for index in range(10)]
    features = [tuple(0.0 for _ in range(FEATURE_COUNT)) for _ in range(10)]
    with pytest.raises(InternalSelectiveModelError):
        fit_probability_head(LINEAR_MODEL_VERSION, open_times, features, [NEUTRAL] + [UP] * 9)


@pytest.mark.parametrize("model", [LINEAR_MODEL_VERSION, HGBR_MODEL_VERSION])
def test_the_head_returns_calibrated_probabilities_in_range(model: str) -> None:
    count = 900
    open_times = [BASE + index * HOUR for index in range(count)]
    features = [
        tuple(math.sin(index / (position + 3)) for position in range(FEATURE_COUNT))
        for index in range(count)
    ]
    directions = [UP if math.sin(index / 7.0) > 0 else DOWN for index in range(count)]
    head = fit_probability_head(model, open_times, features, directions)
    probabilities = head.probability_up(features[:50])
    assert len(probabilities) == 50
    assert all(0.0 <= value <= 1.0 for value in probabilities)


def test_the_head_refuses_the_wrong_feature_width() -> None:
    count = 900
    open_times = [BASE + index * HOUR for index in range(count)]
    features = [
        tuple(math.sin(index / (position + 3)) for position in range(FEATURE_COUNT))
        for index in range(count)
    ]
    directions = [UP if math.sin(index / 7.0) > 0 else DOWN for index in range(count)]
    head = fit_probability_head(LINEAR_MODEL_VERSION, open_times, features, directions)
    with pytest.raises(InternalSelectiveModelError):
        head.probability_up([(0.0, 1.0)])


# --- frozen artifacts on disk ------------------------------------------------------------


def test_the_admission_pins_every_prior_predictive_result() -> None:
    path = ROOT / ADMISSION_PATH
    if not path.is_file():
        pytest.skip("the family has not been frozen yet")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    assert frozen == admission(ROOT)
    assert frozen["status"] == "FROZEN_BEFORE_FIRST_OUTER_PREDICTION"
    assert frozen["v1_result_count"] == len(PRIOR_V1_RESULT_PATHS) == 10
    assert set(frozen["v2_prior_result_sha256"]) == set(PRIOR_V2_RESULT_PATHS)
    assert frozen["inference_seed"] == 20260922
    assert frozen["sealed_queries"] == 0
    assert frozen["champion"] == "NONE"
    assert frozen["real_money"] is False
    assert frozen["stage1_substrate_debt"] == "DEFERRED_UNREPAIRED"
    assert frozen["v1_fitted_model_or_prediction_loaded"] is False


def test_the_feature_proofs_pass_before_any_fit() -> None:
    path = ROOT / FEATURE_PROOF_PATH
    if not path.is_file():
        pytest.skip("the feature proofs have not been produced yet")
    proof = json.loads(path.read_text(encoding="utf-8"))
    assert proof["status"] == "PASS_BEFORE_FIRST_MODEL_FIT"
    assert proof["model_fits"] == 0
    assert proof["outer_predictions"] == 0
    assert proof["stage1_substrate_debt_repaired"] is False
    assert all(proof["checks"].values())
    assert proof["v1_reconciliation"]["identical_to_v1_definition"] is True
