"""WP-014 completed result, reconciliation, and governance invariants."""

from __future__ import annotations

import json
from pathlib import Path

from app.research.supervised import FULL_FEATURES
from app.research.wp014_model import HGBR_PARAMETERS

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = "SHALLOW_INTERNAL_HGBR"
CONTROL = "INTERNAL_LINEAR_MATCHED"


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_wp014_results_preserve_the_frozen_comparison() -> None:
    comparison = read_json("reports/research/WP-014-COMPARISON.json")
    assert comparison["model_version"] == "SHALLOW_INTERNAL_HGBR_V1"
    assert comparison["primary_variant"] == PRIMARY
    assert comparison["control_variant"] == CONTROL
    assert comparison["primary_vs_control"] == {
        "control_duplicate_of": "EXP-ML-014-LINEAR-NET-R-FULL",
        "default_net_expectancy_difference_r": 0.010411548199999995,
        "default_trade_count_difference": 268,
        "eligible_universe_matched": True,
        "executed_trade_sets_paired": False,
        "interpretation_guard": (
            "Matched eligible hours do not make executed trades paired because "
            "predictions and occupancy differ."
        ),
    }
    assert set(comparison["configurations"]) == {PRIMARY, CONTROL}
    assert all(
        record["terminal_classification"] == "REJECT_COST_DOMINATED"
        for record in comparison["configurations"].values()
    )
    assert all(
        set(record["profiles"]) == {"DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"}
        for record in comparison["configurations"].values()
    )


def test_wp014_primary_metrics_are_recorded_without_rescue() -> None:
    comparison = read_json("reports/research/WP-014-COMPARISON.json")
    primary = comparison["configurations"][PRIMARY]
    expected = {
        "DEFAULT": (-0.0998928666, -126.7640476522, 1269, 1, 129),
        "ZERO": (0.0201371727, 25.5540721671, 1269, 4, 129),
        "DOUBLE": (-0.2199228978, -279.0821572498, 1269, 0, 129),
        "DELAY_1H": (-0.0868001004, -112.2325297711, 1293, 1, 136),
    }
    for profile, (expectancy, cumulative, trades, nonnegative, minimum) in expected.items():
        result = primary["profiles"][profile]
        assert result["metrics"]["net_expectancy_r"] == expectancy
        assert result["metrics"]["cumulative_net_r"] == cumulative
        assert result["metrics"]["trade_count"] == trades
        assert result["stability"]["nonnegative_fold_count"] == nonnegative
        assert result["diagnostics"]["minimum_fold_trades"] == minimum
    assert primary["prediction_diagnostics"]["prediction_positive_hours"] == 10358
    assert primary["prediction_diagnostics"]["pooled_prediction_label_pearson"] == (
        0.03249332915839472
    )
    control = comparison["configurations"][CONTROL]
    assert control["profiles"]["DEFAULT"]["metrics"]["net_expectancy_r"] == -0.1103044148
    assert control["profiles"]["DEFAULT"]["metrics"]["trade_count"] == 1001
    assert control["prediction_diagnostics"]["pooled_prediction_label_pearson"] == (
        0.030509574361504192
    )


def test_wp014_independent_reconciliation_passed_at_frozen_tolerance() -> None:
    report = read_json("reports/validation/WP-014-MODEL-RECONCILIATION.json")
    assert report["status"] == "PASS"
    assert report["reconciliation"] == "INDEPENDENT_SHALLOW_INTERNAL_HGBR_V1"
    assert report["prediction_tolerance"] == 1e-10
    assert not report["mismatches"]
    assert set(report["checks"].values()) == {"PASS"}
    assert report["independent_model_refits"] == 12
    assert report["maximum_prediction_gap"] <= report["prediction_tolerance"]


def test_wp014_correlation_materiality_is_not_retroactively_invented() -> None:
    correction = read_json("reports/validation/WP-014-REPORTING-CORRECTION.json")
    assert correction["status"] == "PASS"
    assert correction["correction"] == "OOS_CORRELATION_MATERIALITY_NOT_ESTABLISHED"
    assert correction["difference"] == 0.00198375479689053
    assert correction["original_artifact_preserved"] is True
    assert correction["experiment_results_changed"] is False


def test_wp014_fold_models_pin_exact_hgbr_identity() -> None:
    document = read_json("research/experiments/EXP-ML-022-SHALLOW-INTERNAL-HGBR/fold-models.json")
    assert document["model_fits"] == 6
    assert len(document["fold_models"]) == 6
    for fold in document["fold_models"]:
        model = fold["model"]
        training = fold["training_manifest"]
        assert model["parameters"] == HGBR_PARAMETERS
        assert model["feature_order"] == list(FULL_FEATURES)
        assert model["input_scaling"] == "NONE_RAW_GOVERNED_VALUES"
        assert model["boosting_iterations"] == model["tree_count"] == 64
        assert model["trees_per_iteration"] == 1
        assert model["hyperparameters_searched"] == 0
        assert model["feature_variants"] == model["thresholds_searched"] == 0
        assert training["max_training_label_outcome_us"] < training["purge_boundary_exclusive_us"]
        assert training["training_signal_max_us"] < training["purge_boundary_exclusive_us"]
        for key in ("identity_sha256", "serialization_sha256"):
            assert len(model[key]) == 64


def test_wp014_result_records_and_state_are_consistent_and_safe() -> None:
    for experiment_id in (
        "EXP-ML-022-SHALLOW-INTERNAL-HGBR",
        "EXP-ML-023-INTERNAL-LINEAR-MATCHED",
    ):
        result = read_json(f"research/experiments/{experiment_id}/result.json")
        assert result["status"] == "COMPLETED"
        assert result["validation_outcome"] == "PASS"
        assert result["trial_accounting"] == {"declared_budget": 4, "executed_trials": 4}
        assert result["secondary_results"]["terminal_classification"] == ("REJECT_COST_DOMINATED")
        assert result["secondary_results"]["independent_reconciliation"] == "PASS"

    state = read_json("state/current_state.json")
    assert state["experiments_completed"] == 26
    assert state["latest_reviewed_checkpoint"] == "CROSS-SECTION-SPARSE-POWER-BLOCK-REVIEW"
    assert state["latest_executor_checkpoint"] == (
        "GATE-INTENSITY-CAUSAL-CORRECTION-POWER-RESUME-V1_1"
    )
    challenger = state["shallow_nonlinear_challenger"]
    assert challenger["terminal_classification"] == "REJECT_COST_DOMINATED"
    assert challenger["actual_model_fits"] == challenger["reserved_model_fits"] == 12
    assert challenger["model_reconciliation"] == "PASS"
    assert challenger["sealed_eligibility"] == "NOT_ELIGIBLE_REJECTED"
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["paper_trades_completed"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False
    assert b"## STATUS\nCOMPLETED" in (ROOT / "tasks/archive/WP-014.md").read_bytes()
