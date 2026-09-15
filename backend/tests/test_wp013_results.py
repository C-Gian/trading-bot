"""WP-013 completed result, reconciliation, and governance invariants."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_wp013_frozen_profiles_and_results() -> None:
    comparison = read_json("reports/research/WP-013-COMPARISON.json")
    assert comparison["primary_variant"] == "NFCI_CONTEXT_INTERACTIONS"
    assert comparison["control_variant"] == "INTERNAL_ONLY_MATCHED_NFCI"
    assert comparison["context_version"] == "NFCI_CONTEXT_V1"
    assert comparison["interaction_effect"]["eligible_universe_matched"] is True
    assert comparison["interaction_effect"]["executed_trade_sets_paired"] is False
    for configuration in comparison["configurations"].values():
        assert set(configuration["profiles"]) == {"DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"}
        assert configuration["terminal_classification"] == "REJECT_COST_DOMINATED"
    primary = comparison["configurations"]["NFCI_CONTEXT_INTERACTIONS"]
    control = comparison["configurations"]["INTERNAL_ONLY_MATCHED_NFCI"]
    assert primary["primary_result"] == -0.1086772939
    assert control["primary_result"] == -0.1103044148
    assert primary["profiles"]["DEFAULT"]["metrics"]["trade_count"] == 1060
    assert (
        comparison["interaction_effect"]["primary_minus_control_default_net_expectancy_r"]
        == 0.0016271209000000009
    )


def test_wp013_interactions_and_reconciliation() -> None:
    stability = read_json("reports/research/WP-013-INTERACTION-STABILITY.json")
    assert stability["stable_interaction_signs"] == 5
    assert stability["interaction_count"] == 8
    assert len(stability["condition_numbers"]) == 6
    assert set(stability["effective_raw_feature_slopes"]) == {
        "LOG_RETURN_1H",
        "LOG_RETURN_24H",
        "LOG_DISTANCE_TO_PRIOR_24H_HIGH",
        "REALIZED_VOL_24H",
        "LOG_RELATIVE_VOLUME_1H",
        "DIRECTIONAL_EFFICIENCY_4H",
        "TAKER_BUY_SHARE_1H_CENTERED",
        "TAKER_BUY_SHARE_4H_CENTERED",
    }
    report = read_json("reports/validation/WP-013-MODEL-RECONCILIATION.json")
    assert report["status"] == "PASS"
    assert report["mismatches"] == []
    assert set(report["checks"].values()) == {"PASS"}
    assert report["independent_model_refits"] == 12
    assert report["maximum_prediction_gap"] < report["tolerance"]


def test_wp013_result_records_and_safety_state() -> None:
    for experiment in (
        "EXP-ML-020-NFCI-CONTEXT-INTERACTIONS",
        "EXP-ML-021-INTERNAL-NFCI-MATCHED",
    ):
        result = read_json(f"research/experiments/{experiment}/result.json")
        assert result["status"] == "COMPLETED"
        assert result["validation_outcome"] == "PASS"
        assert result["secondary_results"]["independent_reconciliation"] == "PASS"
        assert result["trial_accounting"] == {"declared_budget": 4, "executed_trials": 4}
    state = read_json("state/current_state.json")
    assert state["experiments_completed"] == 26
    assert state["latest_executor_checkpoint"] == (
        "P2-METHODOLOGY-BLOCK-CLOSURE-RESEARCH-ARCHITECTURE-SYNTHESIS-V2"
    )
    assert state["latest_reviewed_checkpoint"] == "P2-METHODOLOGY-BLOCK-REVIEW"
    assert state["champion_status"] == "NONE"
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["paper_trades_completed"] == 0
    assert state["real_money_authorized"] is False
