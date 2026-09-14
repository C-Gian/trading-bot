"""Result-free structural and synthetic validation for preregistered WP-017."""

from __future__ import annotations

import inspect
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from app.research.cftc import FEATURE as CFTC_FEATURE
from app.research.cftc import CFTCContextSource
from app.research.runtime_v2 import (
    RUNTIME_VERSION,
    OrderedPredictions,
    build_profile_prediction_views,
)
from app.research.supervised import FULL_FEATURES, SupervisedDataError, SupervisedRow
from app.research.wp014_model import HGBR_PARAMETERS
from app.research.wp017 import (
    CONTROL_VARIANT,
    EXPERIMENTS,
    PRIMARY_VARIANT,
    SUCCESS_CRITERIA,
    load_protocol,
    novelty_decision,
    preflight,
)
from app.research.wp017_lab import (
    CONTROL_FEATURES,
    PRIMARY_FEATURES,
    CFTCPositioningLab,
    WP017LabError,
)

ROOT = Path(__file__).resolve().parents[2]
HOUR_US = 3_600_000_000


def _us(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1_000_000)


class _FeatureSource:
    """Minimal governed F1-F8 source; the excluded hour has no internal features."""

    def __init__(self, available: set[int]):
        self.available = available

    def at(self, signal_us: int) -> SupervisedRow:
        if signal_us not in self.available:
            raise SupervisedDataError("no governed feature row")
        return SupervisedRow(
            signal_us,
            100.0,
            signal_us - HOUR_US,
            signal_us,
            signal_us,
            tuple(float(index) for index in range(len(FULL_FEATURES))),
        )


def _lab(feature_hours: set[int], cftc: CFTCContextSource) -> CFTCPositioningLab:
    walk_forward = {
        "folds": [
            {
                "fold_id": "DEV-2020",
                "train_start": "2019-01-01T00:00:00Z",
                "train_end_exclusive": "2019-12-22T00:00:00Z",
                "validation_start": "2019-12-31T00:00:00Z",
                "last_signal_inclusive": "2019-12-31T05:00:00Z",
            }
        ]
    }
    return CFTCPositioningLab(object(), _FeatureSource(feature_hours), cftc, walk_forward)


def _cftc(available: list[str], values: list[float]) -> CFTCContextSource:
    return CFTCContextSource(
        [_us(item) for item in available],
        [date(2019, 12, 1 + index) for index in range(len(available))],
        values,
    )


def test_frozen_protocol_adds_exactly_one_cftc_feature() -> None:
    protocol = load_protocol(ROOT)
    assert protocol["internal_features"] == list(FULL_FEATURES)
    assert tuple(protocol["control_feature_order"]) == CONTROL_FEATURES == FULL_FEATURES
    assert tuple(protocol["primary_feature_order"]) == PRIMARY_FEATURES
    assert PRIMARY_FEATURES == (*FULL_FEATURES, CFTC_FEATURE)
    assert len(PRIMARY_FEATURES) - len(CONTROL_FEATURES) == 1
    assert protocol["funding_feature_included"] is False
    assert protocol["hgbr_parameters"] == HGBR_PARAMETERS
    assert protocol["runtime_version"] == RUNTIME_VERSION == "RESEARCH_RUNTIME_V2_BATCH"
    assert protocol["folds"] == [2020, 2021, 2022, 2023, 2024]
    assert protocol["profiles"] == ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"]
    assert protocol["success_criteria"]["pass_requires_all"] == list(SUCCESS_CRITERIA)
    assert all(value == 0 for key, value in protocol["budget"].items() if key.endswith("variants"))
    assert protocol["budget"]["result_dependent_forks"] == 0
    assert protocol["budget"]["feature_subsets"] == protocol["budget"]["funding_combinations"] == 0
    assert protocol["cftc"]["cftc_contract_market_code"] == "133741"
    assert protocol["cftc"]["interpolation"] is False
    assert protocol["cftc"]["report_age_feature"] is False
    assert protocol["cftc"]["freshness_cutoff"] is False


def test_admission_and_preflight_exist_before_any_result() -> None:
    admission = novelty_decision(ROOT)
    primary, control = admission["variants"]
    assert primary["variant"] == PRIMARY_VARIANT
    assert primary["classification"] == "NEW_FAMILY" and primary["admitted"] is True
    assert control["variant"] == CONTROL_VARIANT
    assert control["classification"] == "KNOWN_INTERNAL_HGBR_MATCHED_CONTROL"
    assert control["authorized_as_matched_control"] is True
    gate = preflight(ROOT)
    assert gate["status"] == "PASS"
    assert gate["market_results_observed"] == gate["model_fits_executed"] == 0
    assert gate["post_cutoff_access"] == gate["sealed_queries"] == 0
    assert gate["matched_eligible_universe"] is True
    assert gate["new_feature_count"] == 1 and gate["only_new_feature"] == CFTC_FEATURE
    assert gate["runtime_version"] == RUNTIME_VERSION
    assert not any(
        (ROOT / "research/experiments" / experiment / "result.json").exists()
        for experiment in EXPERIMENTS.values()
    )


def test_committed_cftc_integrity_is_metadata_only_and_point_in_time_safe() -> None:
    integrity = json.loads((ROOT / "reports/validation/WP-017-CFTC-INTEGRITY.json").read_text())
    assert integrity["status"] == "PASS" and integrity["market_outcomes_read"] is False
    assert integrity["contract_market_code"] == "133741"
    assert integrity["raw_rows"] == 352 and integrity["canonical_eligible_rows"] == 351
    assert integrity["excluded_availability_after_cutoff"] == 1
    assert integrity["unresolved_publication_rows"] == 0
    assert integrity["postcutoff_rows_in_canonical"] == 0
    assert integrity["duplicate_market_report_rows"] == 0


def test_primary_and_control_share_exactly_identical_eligible_timestamps() -> None:
    hours = {_us(f"2019-12-31T{hour:02d}:00:00Z") for hour in range(6)}
    hours.add(_us("2019-12-30T23:00:00Z"))
    cftc = _cftc(["2019-12-31T02:00:00Z"], [0.25])
    lab = _lab(hours, cftc)
    plan = lab.validation_signals()
    eligible = lab.evaluation_signal_ids()
    # Hours before the CFTC report became available are excluded for BOTH configurations.
    assert eligible == tuple(_us(f"2019-12-31T{hour:02d}:00:00Z") for hour in range(2, 6))
    assert plan == [("DEV-2020", eligible)]
    primary_rows = [lab.row(signal) for signal in eligible]
    control_rows = [lab.row(signal) for signal in eligible]
    assert primary_rows == control_rows and all(row is not None for row in primary_rows)
    for row in primary_rows:
        assert row is not None
        primary_values = lab.values_for(PRIMARY_VARIANT, row)
        control_values = lab.values_for(CONTROL_VARIANT, row)
        assert len(primary_values) == len(PRIMARY_FEATURES)
        assert len(control_values) == len(CONTROL_FEATURES)
        assert primary_values[:-1] == control_values
        assert primary_values[-1] == 0.25


def test_internal_ineligibility_removes_the_hour_from_both_configurations() -> None:
    hours = {_us(f"2019-12-31T{hour:02d}:00:00Z") for hour in range(6)}
    hours.discard(_us("2019-12-31T03:00:00Z"))
    lab = _lab(hours, _cftc(["2019-12-30T00:00:00Z"], [-0.4]))
    assert _us("2019-12-31T03:00:00Z") not in lab.evaluation_signal_ids()
    assert lab.row(_us("2019-12-31T03:00:00Z")) is None


def test_latest_available_report_is_held_without_interpolation() -> None:
    hours = {_us(f"2019-12-31T{hour:02d}:00:00Z") for hour in range(6)}
    lab = _lab(
        hours,
        _cftc(["2019-12-31T01:00:00Z", "2019-12-31T04:00:00Z"], [-0.4, 0.9]),
    )
    for signal in lab.evaluation_signal_ids():
        lab.row(signal)
    held = {signal: lab.cftc_values[signal][2] for signal in lab.evaluation_signal_ids()}
    assert held[_us("2019-12-31T01:00:00Z")] == -0.4
    assert held[_us("2019-12-31T03:00:00Z")] == -0.4
    assert held[_us("2019-12-31T04:00:00Z")] == 0.9
    assert set(held.values()) == {-0.4, 0.9}


def test_report_available_later_never_leaks_into_an_earlier_signal() -> None:
    hours = {_us("2019-12-31T00:00:00Z")}
    lab = _lab(hours, _cftc(["2019-12-31T05:00:00Z"], [0.5]))
    assert lab.row(_us("2019-12-31T00:00:00Z")) is None
    assert lab.exclusions["cftc_unavailable"] == 1


def test_lab_rejects_a_context_that_reports_a_future_availability() -> None:
    class _Leaky:
        def at(self, signal_us: int) -> tuple[int, date, float]:
            return signal_us + HOUR_US, date(2019, 12, 31), 0.1

    lab = _lab({_us("2019-12-31T00:00:00Z")}, _Leaky())  # type: ignore[arg-type]
    with pytest.raises(WP017LabError, match="not legally available"):
        lab.row(_us("2019-12-31T00:00:00Z"))


def test_delay_profile_uses_the_previous_hour_and_others_reuse_one_prediction_set() -> None:
    signals = tuple(_us(f"2019-12-31T{hour:02d}:00:00Z") for hour in range(4))
    predictions = OrderedPredictions(signals, (0.1, 0.2, 0.3, 0.4))
    views = build_profile_prediction_views(predictions, signals[1:])
    assert views["DEFAULT"] is views["ZERO"] is views["DOUBLE"]
    assert views["DEFAULT"].values == (0.2, 0.3, 0.4)
    assert views["DELAY_1H"].signal_ids == signals[1:]
    assert views["DELAY_1H"].prediction_signal_ids == signals[:-1]
    assert views["DELAY_1H"].values == (0.1, 0.2, 0.3)


def test_signal_rule_is_exactly_prediction_above_zero() -> None:
    predictions = OrderedPredictions((1, 2, 3), (-0.5, 0.0, 0.5))
    assert predictions.positive_decisions() == (False, False, True)


def test_lab_source_has_no_alternative_cftc_group_normalizer_or_tuning_paths() -> None:
    source = inspect.getsource(CFTCPositioningLab).lower()
    # FittedFundingHGBR is only the reused frozen WP-015 estimator wrapper; the rejected
    # Binance funding feature itself must never appear.
    assert "latest_settled_funding_rate" not in source
    assert all(
        forbidden not in source
        for forbidden in (
            "asset_manager",
            "dealer",
            "other_rept",
            "nonrept",
            "zscore",
            "clip(",
            "rolling",
            "gridsearch",
            "early_stopping=true",
            "report_age",
        )
    )
    assert "wikimedia" not in source and "attention" not in source


def test_declared_dependencies_cover_the_runtime_and_reconciliation_paths() -> None:
    from app.research.wp017 import IMPLEMENTATION_PATHS

    required: tuple[str, ...] = (
        "backend/app/research/cftc.py",
        "backend/app/research/runtime_v2.py",
        "backend/app/research/wp017_lab.py",
        "backend/app/research/wp017_runner.py",
        "scripts/reconcile_wp017.py",
        "data/manifests/CFTC-CME-BITCOIN-TFF-DEV-v1.json",
    )
    assert set(required) <= set(IMPLEMENTATION_PATHS)
    for relative in IMPLEMENTATION_PATHS:
        assert (ROOT / relative).is_file(), relative


def test_preregistrations_freeze_the_success_criteria_and_one_feature_restriction() -> None:
    spaces: dict[str, Any] = {}
    for variant, experiment in EXPERIMENTS.items():
        document = json.loads(
            (ROOT / f"research/experiments/{experiment}/preregistration.json").read_text()
        )
        space = document["parameter_space"]
        spaces[variant] = space
        assert document["status"] == "PREREGISTERED"
        assert space["success_criteria"] == list(SUCCESS_CRITERIA)
        assert space["runtime_version"] == RUNTIME_VERSION
        assert space["signal_threshold"] == 0.0
        assert space["validation_years"] == [2020, 2021, 2022, 2023, 2024]
        assert space["purge_hours"] == 216
        assert space["matched_cftc_eligible_universe"] is True
        assert space["funding_feature_included"] is False
        assert space["sealed_data_access"] == "PROHIBITED"
        assert space["cftc_contract_market_code"] == "133741"
    assert spaces[PRIMARY_VARIANT]["only_new_feature"] == CFTC_FEATURE
    assert spaces[PRIMARY_VARIANT]["new_feature_count"] == 1
    assert spaces[CONTROL_VARIANT]["only_new_feature"] is None
    assert spaces[CONTROL_VARIANT]["new_feature_count"] == 0
    assert spaces[PRIMARY_VARIANT]["features"] == list(PRIMARY_FEATURES)
    assert spaces[CONTROL_VARIANT]["features"] == list(CONTROL_FEATURES)


def test_cutoff_boundary_row_is_absent_from_the_canonical_development_context() -> None:
    manifest = json.loads((ROOT / "data/manifests/CFTC-CME-BITCOIN-TFF-DEV-v1.json").read_text())
    coverage = manifest["coverage"]
    cutoff = datetime(2024, 12, 31, 23, 59, tzinfo=UTC)
    assert coverage["last_report_date"] == "2024-12-31"
    assert manifest["row_counts"]["excluded_availability_after_cutoff"] == 1
    last_available = datetime.fromisoformat(coverage["last_availability_timestamp"])
    assert last_available <= cutoff
    assert manifest["integrity"]["postcutoff_rows_in_canonical"] == 0
