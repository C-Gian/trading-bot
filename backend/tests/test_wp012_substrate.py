"""WP-012 Phase 1: the NFCI regime gate, the two-expert substrate, and admission."""

from __future__ import annotations

import ast
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from app.research.evaluation_protocol import HOUR_US, utc_us
from app.research.regime import (
    NORMAL_OR_LOOSE,
    REGIME_SERIES,
    REGIME_THRESHOLD,
    REGIME_VERSION,
    REGIMES,
    TIGHT,
    RegimeError,
    RegimeReading,
    RegimeSource,
    classify,
    independent_regime,
)
from app.research.supervised import FULL_FEATURES, IsolatedLabel
from app.research.wp012 import (
    ARCHITECTURE,
    CONTROL_VARIANT,
    EXPERIMENTS,
    GLOBAL_KEY,
    MAXIMUM_EXPERT_FITS,
    PRIMARY_VARIANT,
    VARIANTS,
    WP012Error,
    load_protocol,
    novelty_decisions,
    preflight,
    validate_admission,
    validate_allocation,
    validate_preregistrations,
    validate_protocol,
)
from app.research.wp012_lab import (
    PURGE_US,
    STRATEGY_VERSION,
    TRIAL_SCHEMA,
    RegimeExpertLab,
    RegimeRow,
    WP012LabError,
)

ROOT = Path(__file__).resolve().parents[2]


def _steps(*items: tuple[str, date, float]) -> list[tuple[int, date, float]]:
    return [(utc_us(available), observation, value) for available, observation, value in items]


# --- the frozen regime rule ---------------------------------------------------------


def test_the_threshold_is_exactly_zero_and_zero_is_not_tight() -> None:
    assert REGIME_THRESHOLD == 0.0
    assert classify(0.0) == NORMAL_OR_LOOSE
    assert classify(-1e-15) == NORMAL_OR_LOOSE
    assert classify(1e-15) == TIGHT


def test_there_are_exactly_two_regimes_and_nothing_between_them() -> None:
    assert REGIMES == (NORMAL_OR_LOOSE, TIGHT)
    assert {classify(value) for value in (-5.0, -0.1, 0.0, 0.1, 5.0)} == set(REGIMES)


def test_the_gate_reads_one_series_only() -> None:
    assert REGIME_SERIES == "NFCI"
    assert REGIME_VERSION == "FINANCIAL_CONDITIONS_REGIME_V1"


# --- point-in-time availability -----------------------------------------------------


def test_a_reading_is_invisible_until_its_own_availability_time() -> None:
    source = RegimeSource(_steps(("2020-03-05T00:00:00Z", date(2020, 2, 29), 0.5)))
    assert source.at(utc_us("2020-03-04T00:00:00Z")) is None
    reading = source.at(utc_us("2020-03-05T00:00:00Z"))
    assert reading is not None and reading.regime == TIGHT


def test_a_later_revision_cannot_change_an_earlier_regime() -> None:
    source = RegimeSource(
        _steps(
            ("2020-03-05T00:00:00Z", date(2020, 2, 29), -0.4),
            ("2020-09-01T00:00:00Z", date(2020, 2, 29), 0.9),
        )
    )
    before = source.at(utc_us("2020-08-31T00:00:00Z"))
    after = source.at(utc_us("2020-09-01T00:00:00Z"))
    assert before is not None and before.regime == NORMAL_OR_LOOSE
    assert after is not None and after.regime == TIGHT


def test_simultaneous_publications_collapse_to_the_newest_observation() -> None:
    source = RegimeSource(
        _steps(
            ("2020-03-05T00:00:00Z", date(2020, 2, 22), -0.4),
            ("2020-03-05T00:00:00Z", date(2020, 2, 29), 0.7),
        )
    )
    reading = source.at(utc_us("2020-03-05T00:00:00Z"))
    assert reading is not None
    assert reading.observation == date(2020, 2, 29) and reading.regime == TIGHT


def test_a_missing_reading_is_ineligible_and_never_imputed() -> None:
    source = RegimeSource(_steps(("2020-03-05T00:00:00Z", date(2020, 2, 29), 0.5)))
    assert source.at(utc_us("2019-01-02T00:00:00Z")) is None


def test_post_cutoff_or_misaligned_regime_signals_are_refused() -> None:
    source = RegimeSource(_steps(("2020-03-05T00:00:00Z", date(2020, 2, 29), 0.5)))
    with pytest.raises(RegimeError, match="misaligned or post-cutoff"):
        source.at(utc_us("2025-01-02T00:00:00Z"))
    with pytest.raises(RegimeError, match="misaligned or post-cutoff"):
        source.at(utc_us("2020-03-05T00:00:00Z") + 60_000_000)


def test_an_empty_vintage_history_is_refused_outright() -> None:
    with pytest.raises(RegimeError, match="no NFCI vintage history"):
        RegimeSource([])


def test_the_naive_rescan_reproduces_the_bisect_gate() -> None:
    records: list[dict[str, Any]] = [
        {
            "series_id": "NFCI",
            "observation_date": date(2020, 2, 29),
            "availability_time": datetime(2020, 3, 5, tzinfo=UTC),
            "value": -0.4,
        },
        {
            "series_id": "NFCI",
            "observation_date": date(2020, 2, 29),
            "availability_time": datetime(2020, 9, 1, tzinfo=UTC),
            "value": 0.9,
        },
        {
            "series_id": "DFF",
            "observation_date": date(2020, 2, 29),
            "availability_time": datetime(2020, 3, 5, tzinfo=UTC),
            "value": 99.0,
        },
    ]
    source = RegimeSource(
        _steps(
            ("2020-03-05T00:00:00Z", date(2020, 2, 29), -0.4),
            ("2020-09-01T00:00:00Z", date(2020, 2, 29), 0.9),
        )
    )
    for instant in ("2020-03-05T00:00:00Z", "2020-08-31T00:00:00Z", "2020-09-01T00:00:00Z"):
        signal = utc_us(instant)
        produced = source.at(signal)
        expected = independent_regime(records, signal)
        assert isinstance(produced, RegimeReading) and isinstance(expected, RegimeReading)
        assert (produced.regime, produced.nfci) == (expected.regime, expected.nfci)


# --- the two-expert substrate -------------------------------------------------------

FOLD = {
    "fold_id": "SYN-2021",
    "train_start": "2020-01-01T00:00:00Z",
    "train_end_exclusive": "2020-12-23T00:00:00Z",
    "validation_start": "2021-01-01T00:00:00Z",
    "validation_end_exclusive": "2022-01-01T00:00:00Z",
    "last_signal_inclusive": "2021-01-01T09:00:00Z",
}
BOUNDARY = utc_us(FOLD["train_end_exclusive"])


class SyntheticLab(RegimeExpertLab):
    """Exercises partitioning and feasibility without touching the real dataset."""

    def __init__(self, rows: dict[int, RegimeRow], labels: dict[int, IsolatedLabel]):
        self._synthetic_rows = rows
        self._synthetic_labels = labels
        self.exclusions = Counter()
        self.walk_forward = {"folds": [FOLD]}
        self.folds = [FOLD]

    def row(self, signal_us: int) -> RegimeRow | None:
        return self._synthetic_rows.get(signal_us)

    def label(self, row: RegimeRow) -> IsolatedLabel:
        return self._synthetic_labels[row.signal_us]


def synthetic(tight_count: int, *, outcome_offset_us: int = HOUR_US) -> SyntheticLab:
    """300 hourly rows ending one hour before the purge boundary.

    The final row's outcome lands exactly on the boundary, so 299 survive by default.
    """
    rng = np.random.default_rng(12)
    rows: dict[int, RegimeRow] = {}
    labels: dict[int, IsolatedLabel] = {}
    total = 300
    for index in range(total):
        signal_us = BOUNDARY - (total - index) * HOUR_US
        regime = TIGHT if index < tight_count else NORMAL_OR_LOOSE
        values = tuple(float(value) for value in rng.normal(size=len(FULL_FEATURES)))
        rows[signal_us] = RegimeRow(
            signal_us, 30000.0, regime, 0.5 if regime == TIGHT else -0.5, values
        )
        labels[signal_us] = IsolatedLabel(
            signal_us, "VALID", "TARGET", signal_us + outcome_offset_us, float(rng.normal())
        )
    return SyntheticLab(rows, labels)


def test_each_expert_sees_only_its_own_regime_rows() -> None:
    lab = synthetic(tight_count=120)
    fit = lab.fit_fold(PRIMARY_VARIANT, FOLD)
    assert set(fit.experts) == set(REGIMES)
    assert fit.infeasible == {}
    assert fit.manifests[TIGHT]["fit_rows"] == 120
    assert fit.manifests[NORMAL_OR_LOOSE]["fit_rows"] == 179
    assert fit.manifests[TIGHT]["fit_rows"] + fit.manifests[NORMAL_OR_LOOSE]["fit_rows"] == 299


def test_the_experts_are_independent_and_share_no_coefficient() -> None:
    lab = synthetic(tight_count=120)
    fit = lab.fit_fold(PRIMARY_VARIANT, FOLD)
    tight = fit.experts[TIGHT]
    loose = fit.experts[NORMAL_OR_LOOSE]
    assert not np.allclose(tight.coefficients, loose.coefficients)
    assert not np.allclose(tight.means, loose.means)
    assert tight.training_matrix_hash != loose.training_matrix_hash


def test_an_infeasible_regime_expert_is_refused_and_regimes_are_never_merged() -> None:
    lab = synthetic(tight_count=4)
    fit = lab.fit_fold(PRIMARY_VARIANT, FOLD)
    assert TIGHT not in fit.experts
    assert TIGHT in fit.infeasible
    assert "insufficient" in fit.infeasible[TIGHT] or "dimensions" in fit.infeasible[TIGHT]
    # The four TIGHT rows must not be absorbed into the surviving expert.
    assert fit.manifests[NORMAL_OR_LOOSE]["fit_rows"] == 295


def test_a_regime_with_no_training_row_at_all_is_recorded_not_invented() -> None:
    lab = synthetic(tight_count=0)
    fit = lab.fit_fold(PRIMARY_VARIANT, FOLD)
    assert fit.experts.keys() == {NORMAL_OR_LOOSE}
    assert fit.infeasible[TIGHT] == "no eligible training rows for this regime"


def test_the_matched_control_fits_one_expert_on_the_same_eligible_rows() -> None:
    lab = synthetic(tight_count=120)
    fit = lab.fit_fold(CONTROL_VARIANT, FOLD)
    assert fit.experts.keys() == {GLOBAL_KEY}
    assert fit.manifests[GLOBAL_KEY]["fit_rows"] == 299


def test_a_label_outcome_at_or_after_the_purge_boundary_is_excluded() -> None:
    lab = synthetic(tight_count=120, outcome_offset_us=50 * HOUR_US)
    fit = lab.fit_fold(PRIMARY_VARIANT, FOLD)
    excluded = lab.exclusions["outcome_after_purge_boundary"]
    assert excluded == 50
    fitted = sum(manifest["fit_rows"] for manifest in fit.manifests.values())
    assert fitted == 250
    for manifest in fit.manifests.values():
        assert manifest["max_training_label_outcome_us"] < BOUNDARY


def test_the_frozen_purge_boundary_cannot_be_moved() -> None:
    assert PURGE_US == 216 * HOUR_US
    lab = synthetic(tight_count=120)
    moved = dict(FOLD, validation_start="2020-12-24T00:00:00Z")
    with pytest.raises(WP012LabError, match="216h training purge boundary"):
        lab.fit_fold(PRIMARY_VARIANT, moved)


def test_an_hour_whose_expert_is_infeasible_gets_no_prediction_and_is_counted() -> None:
    lab = synthetic(tight_count=0)
    rng = np.random.default_rng(7)
    start = utc_us(FOLD["validation_start"])
    for offset in range(-1, 10):
        signal_us = start + offset * HOUR_US
        regime = TIGHT if offset % 2 else NORMAL_OR_LOOSE
        lab._synthetic_rows[signal_us] = RegimeRow(
            signal_us,
            30000.0,
            regime,
            0.5 if regime == TIGHT else -0.5,
            tuple(float(v) for v in rng.normal(size=len(FULL_FEATURES))),
        )
    fits = lab.fit_configuration(PRIMARY_VARIANT)
    predictions, uncovered = lab.predict(PRIMARY_VARIANT, fits)
    covered = [signal for signal in predictions if signal >= start]
    assert all(lab._synthetic_rows[signal].regime == NORMAL_OR_LOOSE for signal in covered)
    assert uncovered[f"{FOLD['fold_id']}:{TIGHT}"] == 6
    assert all(expert == NORMAL_OR_LOOSE for _, _, expert in predictions.values())


def test_exactly_one_expert_speaks_per_hour() -> None:
    lab = synthetic(tight_count=120)
    assert lab._expert_key(PRIMARY_VARIANT, TIGHT) == TIGHT
    assert lab._expert_key(PRIMARY_VARIANT, NORMAL_OR_LOOSE) == NORMAL_OR_LOOSE
    assert lab._expert_key(CONTROL_VARIANT, TIGHT) == GLOBAL_KEY


def test_no_macro_value_enters_an_expert_feature_matrix() -> None:
    lab = synthetic(tight_count=120)
    fit = lab.fit_fold(PRIMARY_VARIANT, FOLD)
    for model in fit.experts.values():
        assert model.feature_order == FULL_FEATURES
        assert len(model.coefficients) == 8
    protocol = load_protocol(ROOT)
    for variant in VARIANTS:
        assert tuple(protocol["features"][variant]) == FULL_FEATURES
    macro_names = ("DFF_LEVEL", "DGS10_LEVEL", "T10Y2Y_LEVEL", "VIX_LEVEL", "NFCI_LEVEL")
    assert not set(macro_names) & set(FULL_FEATURES)


def test_the_trial_schema_records_the_regime_and_the_expert() -> None:
    assert STRATEGY_VERSION == ARCHITECTURE
    names = [field.name for field in TRIAL_SCHEMA]
    assert "regime" in names and "expert" in names and "variant" in names


# --- frozen protocol, admission and preregistration ---------------------------------


def test_the_protocol_freezes_the_zero_threshold_and_forbids_variants() -> None:
    regime = load_protocol(ROOT)["regime"]
    assert regime["threshold"] == 0.0
    assert regime["threshold_variants"] == 0
    assert regime["regime_count_variants"] == 0
    assert regime["macro_variable_variants"] == 0
    assert regime["lag_variants"] == 0
    assert regime["transition_smoothing"] == "NONE"
    assert regime["hysteresis"] == "NONE"
    assert regime["macro_features_in_expert_matrix"] == 0
    assert regime["boundary_value_regime"] == NORMAL_OR_LOOSE


def test_the_protocol_freezes_the_purge_cadence_and_expert_budget() -> None:
    protocol = load_protocol(ROOT)
    assert protocol["training"]["purge_boundary_hours"] == 216
    assert protocol["model"]["update_cadence"] == "ONCE_PER_FOLD_NO_VALIDATION_REFIT"
    assert protocol["model"]["validation_refit"] is False
    assert protocol["numeric_parameter_variants"] == 0
    assert protocol["experts_per_fold"] == {PRIMARY_VARIANT: 2, CONTROL_VARIANT: 1}
    assert protocol["maximum_expert_fits"] == MAXIMUM_EXPERT_FITS == 18
    assert protocol["training"]["shared_coefficients_between_experts"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        {"path": ("regime", "threshold"), "value": 0.1},
        {"path": ("regime", "threshold_variants"), "value": 1},
        {"path": ("regime", "hysteresis"), "value": "TWO_SIDED"},
        {"path": ("regime", "macro_features_in_expert_matrix"), "value": 1},
        {"path": ("regime", "infeasible_expert_policy"), "value": "MERGE_REGIMES"},
        {"path": ("training", "purge_boundary_hours"), "value": 24},
        {"path": ("training", "shared_coefficients_between_experts"), "value": True},
        {"path": ("model", "signal_threshold"), "value": 0.1},
        {"path": ("model", "validation_refit"), "value": True},
        {"path": ("execution", "stop_fraction"), "value": 0.03},
    ],
)
def test_any_frozen_declaration_drift_fails_closed(mutation: dict) -> None:
    document = json.loads(json.dumps(load_protocol(ROOT)))
    section, key = mutation["path"]
    document[section][key] = mutation["value"]
    with pytest.raises(WP012Error):
        validate_protocol(document)


def test_adding_a_macro_feature_to_an_expert_fails_closed() -> None:
    document = json.loads(json.dumps(load_protocol(ROOT)))
    document["features"][PRIMARY_VARIANT] = [*document["features"][PRIMARY_VARIANT], "NFCI_LEVEL"]
    with pytest.raises(WP012Error, match="frozen eight internal features"):
        validate_protocol(document)


def test_a_third_regime_fails_closed() -> None:
    document = json.loads(json.dumps(load_protocol(ROOT)))
    document["regime"]["regimes"] = [*document["regime"]["regimes"], "EXTREME"]
    with pytest.raises(WP012Error, match="frozen regime gate"):
        validate_protocol(document)


def test_the_conditioned_family_is_admitted_as_a_new_root_before_results() -> None:
    decisions = novelty_decisions(ROOT)
    assert decisions[0]["variant"] == PRIMARY_VARIANT
    assert decisions[0]["classification"] == "NEW_FAMILY"
    assert decisions[0]["matched_experiment_ids"] == []
    assert decisions[1]["classification"] == "DESCENDANT_MECHANISM_CHANGE"
    assert decisions[0]["behavior_hash"] != decisions[1]["behavior_hash"]
    admission = validate_admission(ROOT)
    assert admission["market_results_observed_at_admission"] == 0
    assert admission["renamed_to_force_novelty"] is False
    assert admission["classifier_modified"] is False


def test_the_allocation_declares_the_exact_budget() -> None:
    allocation = validate_allocation(ROOT)
    assert allocation["new_economic_hypotheses"] == 1
    assert allocation["model_configurations"] == 2
    assert allocation["profile_evaluations"] == 8
    assert allocation["maximum_expert_fits"] == 18
    assert allocation["regime_threshold_variants"] == 0
    assert allocation["regime_count_variants"] == 0
    assert allocation["macro_variable_variants"] == 0
    assert allocation["numeric_parameter_variants"] == 0
    assert allocation["hyperparameter_searches"] == 0
    assert allocation["threshold_searches"] == 0
    assert allocation["sealed_queries"] == 0


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
        assert document["parameter_space"]["regime_threshold"] == 0.0
        assert document["parameter_space"]["regime_threshold_variants"] == 0
        assert document["parameter_space"]["macro_features_in_expert_matrix"] == 0
        assert document["parameter_space"]["features"] == list(FULL_FEATURES)
        assert document["dataset"]["maximum_timestamp"] == "2024-12-31T23:59:00Z"
        assert "REGIME_POINT_IN_TIME_VINTAGE_NO_FUTURE_REVISION" in document["leakage_controls"]
        assert "MISSING_REGIME_INELIGIBLE_NEVER_IMPUTED" in document["leakage_controls"]


def test_preflight_passes_with_no_market_result_observed() -> None:
    report = preflight(ROOT)
    assert report["status"] == "PASS"
    assert report["family_classification"] == "NEW_FAMILY"
    assert report["market_results_observed"] == 0
    assert report["sealed_queries"] == 0
    assert report["regime_threshold"] == 0.0
    assert report["macro_features_in_expert_matrix"] == 0
    assert report["feature_counts"] == {PRIMARY_VARIANT: 8, CONTROL_VARIANT: 8}


# --- committed evidence and scientific separation -----------------------------------


def test_the_committed_regime_asof_audit_passes() -> None:
    report = json.loads(
        (ROOT / "reports/validation/WP-012-REGIME-ASOF-AUDIT.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "PASS"
    assert report["threshold"] == 0.0
    assert report["threshold_variants"] == 0
    assert report["regime_changing_leaks"] == 0
    assert report["revision_boundaries_checked"] > 0
    for check in (
        "independent_regime_agreement",
        "exactly_two_regimes",
        "threshold_is_exactly_zero",
        "zero_is_normal_or_loose",
        "later_revision_cannot_change_earlier_regime",
        "no_post_cutoff_regime",
        "missing_nfci_is_ineligible_not_imputed",
    ):
        assert report["checks"][check] == "PASS"


def test_the_preexecution_structural_finding_is_recorded_before_any_result() -> None:
    finding = json.loads(
        (ROOT / "reports/validation/WP-012-PREEXECUTION-STRUCTURAL-FINDING.json").read_text(
            encoding="utf-8"
        )
    )
    assert finding["status"] == "PRE_EXECUTION_STRUCTURAL_FINDING"
    assert finding["detected_before_any_market_result"] is True
    assert finding["strategy_trials_executed"] == 0
    assert finding["result_artifacts_finalized"] == 0
    assert finding["scientific_scope_changed"] is False
    # Nothing was weakened in response to the finding.
    assert finding["unchanged"]["regime_threshold"] == 0.0
    assert finding["unchanged"]["regime_threshold_variants"] == 0
    assert finding["unchanged"]["regime_count"] == 2
    assert finding["unchanged"]["purge_boundary_hours"] == 216
    assert finding["unchanged"]["macro_in_expert_features"] is False
    assert "merging the regimes when one expert is infeasible" in finding["rejected_alternatives"]
    assert finding["regime_hours"]["per_fold"]["DEV-2020"]["validation_tight"] == 336


def test_wp012_reads_no_paper_evidence_or_live_product_data() -> None:
    for name in ("regime.py", "wp012.py", "wp012_lab.py"):
        source = (ROOT / "backend/app/research" / name).read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not {m for m in modules if "product" in m}, f"{name} reaches the product surface"
        assert "PAPER_TRADES" not in source
        assert "paper" not in source.lower()


def test_wp012_touches_no_sealed_data_and_stops_at_the_development_cutoff() -> None:
    protocol = load_protocol(ROOT)
    assert protocol["development_cutoff"] == "2024-12-31T23:59:00Z"
    assert protocol["evidence_stage"] == "EXPOSED_DEVELOPMENT_WALK_FORWARD"
    assert "SEALED" not in json.dumps(protocol).upper()
    last = max(utc_us(fold["last_signal_inclusive"]) for fold in protocol["folds"])
    assert last <= utc_us("2024-12-31T23:00:00Z")


def test_wp009_gdelt_remains_paused_and_unused() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["exogenous_acquisition_pause"]["status"] == "PARTIAL"
    assert state["exogenous_acquisition_pause"]["wp009_finalized"] is False
    assert "GDELT" not in json.dumps(load_protocol(ROOT))


def test_the_tight_block_is_a_single_contiguous_fortnight_in_2020() -> None:
    """Anchors the pre-execution structural finding to the frozen regime rule."""
    hours = json.loads(
        (ROOT / "reports/validation/WP-012-PREEXECUTION-STRUCTURAL-FINDING.json").read_text(
            encoding="utf-8"
        )
    )["regime_hours"]
    start = utc_us(hours["tight_block_start_utc"])
    end = utc_us(hours["tight_block_end_utc"])
    assert (end - start) // HOUR_US + 1 == hours["tight_total"] == 336
    assert hours["eligible_total"] == 64488
    audit = json.loads(
        (ROOT / "reports/validation/WP-012-REGIME-ASOF-AUDIT.json").read_text(encoding="utf-8")
    )
    assert audit["validation_hour_counts"][TIGHT] == hours["tight_total"]
    assert audit["validation_hour_counts"]["INELIGIBLE"] == 0
