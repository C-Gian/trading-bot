from __future__ import annotations

import json
from pathlib import Path

from app.predictive.macro_vintage import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    EXPERIMENT_IDS,
    PRIOR_EXPERIMENT_RESULTS,
    SEARCH_PLAN_PATH,
    admission,
    admission_identity,
    preregistration,
    preregistration_path,
    search_plan,
)
from app.predictive.macro_vintage_audit import AUDIT_PATH, BLOCKED

ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_the_source_gate_failed_before_any_outcome_or_fit():
    audit = read(AUDIT_PATH)
    assert audit["status"] == BLOCKED
    assert audit["target_bearing_model_fitted"] is False
    assert audit["coverage"]["admissible_folds"] == []
    assert audit["coverage"]["btc_close_column_loaded"] is False
    assert audit["coverage"]["btc_return_values_inspected"] is False
    assert audit["coverage"]["btc_direction_labels_inspected"] is False
    assert audit["coverage"]["candidate_predictions_inspected"] is False
    assert audit["coverage"]["fold_selection_rule"] == "TIMESTAMPS_AND_SOURCE_VALIDITY_ONLY"
    assert all(record["coverage"] < 0.90 for record in audit["coverage"]["by_fold"].values())


def test_the_point_in_time_and_later_vintage_checks_passed():
    audit = read(AUDIT_PATH)
    assert audit["provenance"]["passed"] is True
    assert audit["semantics"]["passed"] is True
    assert audit["semantics"]["independent_snapshot_mismatches"] == 0
    assert (
        audit["semantics"]["checks"]["ADDING_LATER_VINTAGE_CANNOT_CHANGE_EARLIER_FEATURE_VECTOR"]
        is True
    )
    assert audit["source"]["current_revised_substitution"] is False
    assert audit["source"]["post_2024_vintages"] == 0
    assert audit["source"]["interpolation"] is False


def test_the_plan_preregistrations_and_blocked_admission_are_frozen():
    assert read(SEARCH_PLAN_PATH) == search_plan()
    assert read(ADMISSION_PATH) == admission(ROOT)
    for model_version in CONFIGURATION_ORDER:
        record = read(preregistration_path(model_version))
        assert record == preregistration(model_version, ROOT)
        assert record["model_fits"] == record["outer_predictions"] == 0
        assert record["configuration_consumed"] is False
        experiment = EXPERIMENT_IDS[model_version]
        directory = ROOT / "research/experiments" / experiment
        assert not (directory / "result.json").exists()
        assert not (directory / "trials.json").exists()


def test_prior_predictive_results_are_hash_pinned_and_unchanged():
    record = admission(ROOT)
    assert set(record["prior_experiment_result_sha256"]) == set(PRIOR_EXPERIMENT_RESULTS)
    assert len(set(record["prior_experiment_result_sha256"].values())) == 8
    assert record["configurations_consumed"] == record["model_fits_executed"] == 0
    assert record["outer_predictions_observed"] == 0


def test_state_records_the_fail_closed_checkpoint_without_a_new_experiment():
    state = read("state/current_state.json")
    record = state["predictive_stage3_macro_vintage"]
    # The predecessor stays the immutable source block it was; the executor checkpoint and
    # the generation's experiment count have since moved on to its remediation.
    assert state["latest_executor_checkpoint"] == (
        "PREDICTIVE-GENERATION-V2-SELECTIVE-LONG-REBASELINE-V1"
    )
    assert state["predictive_research_objective"]["predictive_experiments_completed"] == 10
    assert record["status"] == BLOCKED
    assert record["admission_identity_sha256"] == admission_identity(ROOT)
    assert record["included_folds"] == []
    assert record["model_fits"] == record["configurations_consumed"] == 0
    assert record["sealed_queries"] == 0
    assert record["champion_status"] == "NONE"
    assert record["real_money"] is False
