"""WP-012 completed-result, reconciliation, and governance invariants."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_wp012_frozen_profiles_and_terminal_results() -> None:
    comparison = read_json("reports/research/WP-012-COMPARISON.json")
    assert comparison["primary_variant"] == "REGIME_TWO_EXPERTS"
    assert comparison["control_variant"] == "GLOBAL_SINGLE_EXPERT_MATCHED"
    assert comparison["regime"]["threshold"] == 0.0
    assert comparison["regime"]["threshold_variants"] == 0
    expected_profiles = {"DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"}
    for configuration in comparison["configurations"].values():
        assert set(configuration["profiles"]) == expected_profiles
        assert configuration["terminal_classification"] == "REJECT_COST_DOMINATED"
    primary = comparison["configurations"]["REGIME_TWO_EXPERTS"]
    control = comparison["configurations"]["GLOBAL_SINGLE_EXPERT_MATCHED"]
    assert primary["primary_result"] == -0.1071860713
    assert control["primary_result"] == -0.1103044148
    assert primary["profiles"]["DEFAULT"]["metrics"]["trade_count"] == 989
    assert control["profiles"]["DEFAULT"]["metrics"]["trade_count"] == 1001
    assert comparison["conditioning_effect"]["paired"] is False


def test_wp012_regime_and_expert_diagnostics_are_truthful() -> None:
    diagnostics = read_json("reports/research/WP-012-REGIME-DIAGNOSTICS.json")
    primary = diagnostics["configurations"]["REGIME_TWO_EXPERTS"]
    assert primary["per_regime"]["NORMAL_OR_LOOSE"]["executed_trades"] == 989
    assert primary["per_regime"]["TIGHT"]["eligible_validation_hours"] == 336
    assert primary["per_regime"]["TIGHT"]["executed_trades"] == 0
    assert primary["per_regime"]["TIGHT"]["mean_net_r"] is None

    stability = read_json("reports/research/WP-012-EXPERT-STABILITY.json")
    tight = stability["configurations"]["REGIME_TWO_EXPERTS"]["experts"]["TIGHT"]
    assert tight["fits"] == 4
    assert tight["unique_model_hashes"] == 1
    assert tight["fit_rows"] == [336, 336, 336, 336]
    assert "not four independent temporal confirmations" in stability["interpretation_guard"]


def test_wp012_independent_reconciliation_passes_every_check() -> None:
    report = read_json("reports/validation/WP-012-MODEL-RECONCILIATION.json")
    assert report["status"] == "PASS"
    assert report["mismatches"] == []
    assert set(report["checks"].values()) == {"PASS"}
    assert report["independent_expert_refits"] == 16
    assert report["independent_gate_counts"] == {"NORMAL_OR_LOOSE": 64152, "TIGHT": 336}
    assert report["maximum_prediction_gap"] < report["tolerance"]


def test_wp012_result_records_preserve_governance() -> None:
    for experiment in (
        "EXP-ML-018-REGIME-TWO-EXPERTS",
        "EXP-ML-019-GLOBAL-MATCHED-CONTROL",
    ):
        result = read_json(f"research/experiments/{experiment}/result.json")
        assert result["status"] == "COMPLETED"
        assert result["validation_outcome"] == "PASS"
        assert result["secondary_results"]["sealed_queries"] == 0
        assert result["secondary_results"]["independent_reconciliation"] == "PASS"
        assert result["trial_accounting"] == {"declared_budget": 4, "executed_trials": 4}

    state = read_json("state/current_state.json")
    assert state["experiments_completed"] == 21
    assert state["latest_executor_checkpoint"] == "WP-013"
    assert state["latest_reviewed_checkpoint"] == "WP-012"
    assert state["regime_conditioned_challenger"]["research_director_verdict"] == "ACCEPTED"
    assert state["champion_status"] == "NONE"
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["paper_trades_completed"] == 0
    assert state["real_money_authorized"] is False
