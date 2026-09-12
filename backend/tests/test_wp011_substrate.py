"""WP-011 Phase 1: macro point-in-time semantics, the adaptive model, and admission."""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pytest
from app.research.evaluation_protocol import utc_us
from app.research.ewls import (
    HALF_LIFE_DAYS,
    MODEL_VERSION,
    SIGNAL_THRESHOLD,
    EwlsModelError,
    fit_ewls,
    model_hash,
    recency_weights,
    weighted_moments,
)
from app.research.macro import (
    MACRO_FEATURES,
    MacroDataError,
    MacroFeatureSource,
    _months_earlier,
    _Vintage,
    effective_model_index,
    monthly_effective_instants,
)
from app.research.supervised import FULL_FEATURES
from app.research.wp011 import (
    ABLATION_VARIANT,
    EXPERIMENTS,
    PRIMARY_VARIANT,
    VARIANTS,
    WP011Error,
    load_protocol,
    novelty_decisions,
    preflight,
    validate_admission,
    validate_allocation,
    validate_preregistrations,
    validate_protocol,
)

ROOT = Path(__file__).resolve().parents[2]
DAY_US = 86_400_000_000
EFFECTIVE = utc_us("2021-01-01T00:00:00Z")


def _vintage(available: str, observation: date, value: float) -> _Vintage:
    return _Vintage(utc_us(available), observation, value)


def _source(**series: list[_Vintage]) -> MacroFeatureSource:
    base = {
        "DFF": [_vintage("2020-01-02T00:00:00Z", date(2020, 1, 1), 1.5)],
        "DGS10": [_vintage("2020-01-02T00:00:00Z", date(2020, 1, 1), 2.0)],
        "T10Y2Y": [_vintage("2020-01-02T00:00:00Z", date(2020, 1, 1), 0.3)],
        "VIXCLS": [_vintage("2020-01-02T00:00:00Z", date(2020, 1, 1), 15.0)],
        "NFCI": [_vintage("2020-01-02T00:00:00Z", date(2020, 1, 1), -0.5)],
        "UNRATE": [_vintage("2020-01-02T00:00:00Z", date(2020, 1, 1), 4.0)],
        "WALCL": [
            _vintage("2020-01-02T00:00:00Z", date(2019, 11, 27), 4_000_000.0),
            _vintage("2020-01-02T00:00:00Z", date(2019, 12, 25), 4_100_000.0),
        ],
        "CPIAUCSL": [
            _vintage("2020-01-02T00:00:00Z", date(2018, 11, 1), 250.0),
            _vintage("2020-01-02T00:00:00Z", date(2019, 11, 1), 255.0),
        ],
    }
    base.update(series)
    return MacroFeatureSource(base)


# --- macro point-in-time semantics ------------------------------------------------


def test_a_value_is_invisible_until_its_own_availability_time() -> None:
    source = _source()
    before = utc_us("2020-01-01T00:00:00Z")
    after = utc_us("2020-01-02T00:00:00Z")
    assert source.at(before) is None
    assert source.at(after) is not None


def test_a_later_revision_cannot_leak_backward() -> None:
    source = _source(
        DFF=[
            _vintage("2020-01-02T00:00:00Z", date(2020, 1, 1), 1.5),
            _vintage("2020-06-01T00:00:00Z", date(2020, 1, 1), 9.9),
        ]
    )
    early = source.at(utc_us("2020-05-31T00:00:00Z"))
    late = source.at(utc_us("2020-06-01T00:00:00Z"))
    assert early is not None and late is not None
    assert early.values[0] == 1.5, "the revision must not be visible before it was published"
    assert late.values[0] == 9.9


def test_the_frozen_eight_macro_features_are_produced_in_order() -> None:
    row = _source().at(utc_us("2020-01-02T00:00:00Z"))
    assert row is not None
    assert len(row.values) == len(MACRO_FEATURES) == 8
    assert MACRO_FEATURES == (
        "DFF_LEVEL",
        "DGS10_LEVEL",
        "T10Y2Y_LEVEL",
        "VIX_LEVEL",
        "NFCI_LEVEL",
        "WALCL_LOG_CHANGE_28D",
        "CPI_YOY",
        "UNRATE_LEVEL",
    )
    assert row.values[0] == 1.5 and row.values[3] == 15.0 and row.values[7] == 4.0


def test_walcl_uses_a_point_in_time_value_at_or_before_28_days_earlier() -> None:
    row = _source().at(utc_us("2020-01-02T00:00:00Z"))
    assert row is not None
    assert row.values[5] == pytest.approx(math.log(4_100_000.0 / 4_000_000.0))


def test_cpi_year_over_year_uses_observation_month_semantics() -> None:
    row = _source().at(utc_us("2020-01-02T00:00:00Z"))
    assert row is not None
    assert row.values[6] == pytest.approx(100.0 * (255.0 / 250.0 - 1.0))
    assert _months_earlier(date(2020, 3, 1), 12) == date(2019, 3, 1)
    assert _months_earlier(date(2020, 1, 1), 12) == date(2019, 1, 1)


def test_missing_required_history_makes_the_row_ineligible_never_imputed() -> None:
    # No CPI observation twelve months before the newest one.
    source = _source(CPIAUCSL=[_vintage("2020-01-02T00:00:00Z", date(2019, 11, 1), 255.0)])
    assert source.at(utc_us("2020-01-02T00:00:00Z")) is None


def test_a_missing_series_is_refused_outright() -> None:
    with pytest.raises(MacroDataError, match="missing ALFRED series history"):
        MacroFeatureSource({"DFF": [_vintage("2020-01-02T00:00:00Z", date(2020, 1, 1), 1.0)]})


def test_post_cutoff_or_misaligned_macro_signals_are_refused() -> None:
    source = _source()
    with pytest.raises(MacroDataError, match="misaligned or post-cutoff"):
        source.at(utc_us("2025-01-02T00:00:00Z"))
    with pytest.raises(MacroDataError, match="misaligned or post-cutoff"):
        source.at(utc_us("2020-01-02T00:00:00Z") + 60_000_000)


# --- monthly cadence ---------------------------------------------------------------


def test_models_become_effective_at_the_first_utc_hour_of_each_month() -> None:
    effective = monthly_effective_instants(
        utc_us("2019-01-02T00:00:00Z"), utc_us("2019-04-15T00:00:00Z")
    )
    assert effective == tuple(utc_us(f"2019-{month:02d}-01T00:00:00Z") for month in (1, 2, 3, 4))


def test_full_walk_forward_uses_seventy_two_monthly_models() -> None:
    effective = monthly_effective_instants(
        utc_us("2019-01-02T00:00:00Z"), utc_us("2024-12-31T00:00:00Z")
    )
    assert len(effective) == 72
    assert effective[0] == utc_us("2019-01-01T00:00:00Z")
    assert effective[-1] == utc_us("2024-12-01T00:00:00Z")


def test_a_signal_hour_uses_the_most_recent_already_effective_model() -> None:
    effective = (
        utc_us("2019-02-01T00:00:00Z"),
        utc_us("2019-03-01T00:00:00Z"),
        utc_us("2019-04-01T00:00:00Z"),
    )
    assert effective_model_index(effective, utc_us("2019-02-01T00:00:00Z")) == 0
    assert effective_model_index(effective, utc_us("2019-03-31T23:00:00Z")) == 1
    assert effective_model_index(effective, utc_us("2019-04-01T00:00:00Z")) == 2
    with pytest.raises(MacroDataError, match="no monthly model is effective"):
        effective_model_index(effective, utc_us("2019-01-15T00:00:00Z"))


# --- the adaptive model ------------------------------------------------------------


def test_the_half_life_is_exactly_one_hundred_and_eighty_days() -> None:
    assert HALF_LIFE_DAYS == 180.0
    weights = recency_weights(
        np.array([EFFECTIVE - 180 * DAY_US, EFFECTIVE - 1], dtype="<i8"), EFFECTIVE
    )
    assert float(weights[0] / weights[1]) == pytest.approx(0.5, abs=1e-9)
    older = recency_weights(np.array([EFFECTIVE - 360 * DAY_US], dtype="<i8"), EFFECTIVE)
    assert float(older[0]) == pytest.approx(0.25, abs=1e-9)


def test_training_rows_must_precede_the_effective_instant() -> None:
    with pytest.raises(EwlsModelError, match="must precede the model effective instant"):
        recency_weights(np.array([EFFECTIVE], dtype="<i8"), EFFECTIVE)


def test_scaling_uses_the_same_weights_as_the_fit() -> None:
    values = np.array([[1.0], [3.0]], dtype=np.float64)
    weights = np.array([3.0, 1.0], dtype=np.float64)
    means, stds = weighted_moments(values, weights)
    assert float(means[0]) == pytest.approx(1.5)
    assert float(stds[0]) == pytest.approx(math.sqrt((3 * 0.25 + 1 * 2.25) / 4))


def test_a_degenerate_feature_fails_closed() -> None:
    values = np.ones((10, 1), dtype=np.float64)
    weights = np.ones(10, dtype=np.float64)
    with pytest.raises(EwlsModelError, match="weighted standard deviation is <= 1e-12"):
        weighted_moments(values, weights)


def test_the_weighted_fit_recovers_known_coefficients() -> None:
    rng = np.random.default_rng(11)
    matrix = rng.normal(size=(400, 3))
    beta = np.array([1.0, -2.0, 0.5])
    labels = matrix @ beta
    times = np.array([EFFECTIVE - (400 - i) * DAY_US // 4 for i in range(400)], dtype="<i8")
    model = fit_ewls(
        matrix,
        labels,
        times,
        ("a", "b", "c"),
        effective_us=EFFECTIVE,
        training_matrix_hash="m",
        training_label_hash="l",
        dependency_hash="d",
    )
    assert model.rank == 4
    assert np.allclose(model.coefficients / model.stds, beta, atol=1e-8)
    assert model.training_rows == 400
    assert 0 < model.effective_sample_size <= 400


def test_recent_rows_dominate_the_fit() -> None:
    """A conflicting old regime must not outweigh the recent one."""
    times = np.array(
        [EFFECTIVE - (1200 - i) * DAY_US for i in range(400)]
        + [EFFECTIVE - (400 - i) * DAY_US // 4 for i in range(400)],
        dtype="<i8",
    )
    rng = np.random.default_rng(3)
    matrix = rng.normal(size=(800, 1))
    labels = np.concatenate([-5.0 * matrix[:400, 0], 5.0 * matrix[400:, 0]])
    model = fit_ewls(
        matrix,
        labels,
        times,
        ("x",),
        effective_us=EFFECTIVE,
        training_matrix_hash="m",
        training_label_hash="l",
        dependency_hash="d",
    )
    assert float(model.coefficients[0]) > 0.0, "the recent regime must dominate"


def test_the_model_record_declares_no_search_and_no_refit() -> None:
    rng = np.random.default_rng(5)
    matrix = rng.normal(size=(100, 2))
    times = np.array([EFFECTIVE - (100 - i) * DAY_US for i in range(100)], dtype="<i8")
    model = fit_ewls(
        matrix,
        matrix @ np.array([1.0, 1.0]),
        times,
        ("a", "b"),
        effective_us=EFFECTIVE,
        training_matrix_hash="m",
        training_label_hash="l",
        dependency_hash="d",
    )
    record = model.as_record()
    assert record["model_version"] == MODEL_VERSION
    assert record["half_life_days"] == 180.0
    assert record["half_life_variants"] == 0
    assert record["hyperparameters_searched"] == 0
    assert record["thresholds_searched"] == 0
    assert record["regularization"] == "NONE"
    assert record["coefficient_thresholding"] is False
    assert record["feature_dropping"] is False
    assert record["validation_refit"] is False
    assert record["signal_threshold"] == SIGNAL_THRESHOLD == 0.0
    assert record["full_rank"] is True
    assert len(model_hash(model)) == 64


# --- frozen protocol, admission and preregistration --------------------------------


def test_the_protocol_freezes_sixteen_and_eight_features() -> None:
    protocol = load_protocol(ROOT)
    assert tuple(protocol["features"][PRIMARY_VARIANT]) == FULL_FEATURES + MACRO_FEATURES
    assert tuple(protocol["features"][ABLATION_VARIANT]) == FULL_FEATURES
    assert len(protocol["features"][PRIMARY_VARIANT]) == 16
    assert len(protocol["features"][ABLATION_VARIANT]) == 8


def test_the_protocol_freezes_the_half_life_cadence_and_purge() -> None:
    protocol = load_protocol(ROOT)
    assert protocol["training"]["half_life_days"] == 180
    assert protocol["training"]["half_life_variants"] == 0
    assert protocol["training"]["purge_boundary_hours"] == 216
    assert protocol["model"]["update_cadence"] == "FIRST_UTC_HOUR_OF_EACH_CALENDAR_MONTH"
    assert protocol["model"]["validation_refit"] is False
    assert protocol["numeric_parameter_variants"] == 0
    assert protocol["model_fits"] == 144


@pytest.mark.parametrize(
    "mutation",
    [
        {"path": ("training", "half_life_days"), "value": 90},
        {"path": ("training", "purge_boundary_hours"), "value": 24},
        {"path": ("model", "signal_threshold"), "value": 0.1},
        {"path": ("model", "validation_refit"), "value": True},
        {"path": ("execution", "stop_fraction"), "value": 0.03},
    ],
)
def test_any_frozen_declaration_drift_fails_closed(mutation: dict) -> None:
    document = json.loads(json.dumps(load_protocol(ROOT)))
    section, key = mutation["path"]
    document[section][key] = mutation["value"]
    with pytest.raises(WP011Error):
        validate_protocol(document)


def test_a_dropped_feature_fails_closed() -> None:
    document = json.loads(json.dumps(load_protocol(ROOT)))
    document["features"][PRIMARY_VARIANT] = document["features"][PRIMARY_VARIANT][:-1]
    with pytest.raises(WP011Error, match="frozen 8 internal \\+ 8 macro"):
        validate_protocol(document)


def test_the_adaptive_family_is_admitted_as_a_new_root_before_results() -> None:
    decisions = novelty_decisions(ROOT)
    assert decisions[0]["variant"] == PRIMARY_VARIANT
    assert decisions[0]["classification"] == "NEW_FAMILY"
    assert decisions[0]["matched_experiment_ids"] == []
    assert decisions[1]["classification"] == "DESCENDANT_MECHANISM_CHANGE"
    admission = validate_admission(ROOT)
    assert admission["market_results_observed_at_admission"] == 0
    assert admission["renamed_to_force_novelty"] is False
    assert admission["classifier_modified"] is False


def test_the_allocation_declares_the_exact_budget() -> None:
    allocation = validate_allocation(ROOT)
    assert allocation["new_economic_hypotheses"] == 1
    assert allocation["model_configurations"] == 2
    assert allocation["profile_evaluations"] == 8
    assert allocation["supervised_model_fits"] == 144
    assert allocation["numeric_parameter_variants"] == 0
    assert allocation["half_life_variants"] == 0
    assert allocation["hyperparameter_searches"] == 0
    assert allocation["threshold_searches"] == 0
    assert allocation["sealed_queries"] == 0
    assert allocation["adaptive_decision_increment"] == 1
    assert allocation["result_dependent_fork_increment"] == 1


def test_both_configurations_are_preregistered_before_any_result() -> None:
    hashes = validate_preregistrations(ROOT)
    assert set(hashes) == set(VARIANTS)
    for variant in VARIANTS:
        document = json.loads(
            (ROOT / f"research/experiments/{EXPERIMENTS[variant]}/preregistration.json").read_text(
                encoding="utf-8"
            )
        )
        assert document["status"] == "PREREGISTERED"
        assert document["parameter_space"]["half_life_days"] == 180
        assert document["parameter_space"]["half_life_variants"] == 0
        assert document["parameter_space"]["feature_subset_searches"] == 0
        assert document["dataset"]["maximum_timestamp"] == "2024-12-31T23:59:00Z"
        assert "MACRO_POINT_IN_TIME_VINTAGE_NO_FUTURE_REVISION" in document["leakage_controls"]


def test_preflight_passes_with_no_market_result_observed() -> None:
    report = preflight(ROOT)
    assert report["status"] == "PASS"
    assert report["family_classification"] == "NEW_FAMILY"
    assert report["market_results_observed"] == 0
    assert report["sealed_queries"] == 0
    assert report["feature_counts"] == {PRIMARY_VARIANT: 16, ABLATION_VARIANT: 8}
    assert report["half_life_days"] == 180


# --- source and scientific separation ----------------------------------------------


def test_the_committed_macro_asof_audit_passes() -> None:
    report = json.loads(
        (ROOT / "reports/validation/WP-011-MACRO-ASOF-AUDIT.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "PASS"
    assert report["checks"]["later_revision_cannot_leak_backward"] == "PASS"
    assert report["checks"]["independent_asof_agreement"] == "PASS"
    assert report["backward_leaks"] == 0
    assert report["values_visible_before_availability"] == 0
    assert report["revision_boundaries_checked"] > 0


def test_the_alfred_source_integrity_remains_accepted() -> None:
    integrity = json.loads(
        (ROOT / "reports/validation/WP-009-ALFRED-INTEGRITY.json").read_text(encoding="utf-8")
    )
    assert integrity["status"] == "PASS"
    for check in (
        "exact_eight_series",
        "historical_vintage_states",
        "next_day_conservative_availability",
        "later_revision_cannot_leak_backward",
        "no_post_2024_vintage",
        "no_current_revised_substitution",
        "no_interpolation",
    ):
        assert integrity["checks"][check] == "PASS"


def test_wp011_reads_no_paper_evidence_or_live_product_data() -> None:
    import ast

    for name in ("macro.py", "ewls.py", "wp011.py", "wp011_lab.py"):
        source = (ROOT / "backend/app/research" / name).read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not {m for m in modules if "product" in m}, f"{name} reaches the product surface"
        assert "PAPER_TRADES" not in source
        assert "paper" not in source.lower() or name == "wp011.py"


def test_wp009_gdelt_remains_paused_and_unused() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["exogenous_acquisition_pause"]["status"] == "PARTIAL"
    assert state["exogenous_acquisition_pause"]["wp009_finalized"] is False
    protocol = load_protocol(ROOT)
    assert "GDELT" not in json.dumps(protocol)
