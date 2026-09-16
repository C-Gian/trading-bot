"""Guards for the committed `PREDICTIVE-INTERNAL-NONLINEAR-V1` records.

These run without market data. They prove the frozen records and the Research Director's
coverage ruling still match the code, the admission artifact still hashes the implementation
that produced the result, the advancement gate follows from the reported numbers, the
Stage-1 family is closed, and the executed linear checkpoint was neither changed nor
rescued.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.predictive.internal_nonlinear import (
    ADMISSION_PATH,
    NO_ADVANCE,
    PREREGISTRATION_PATH,
    REPORT_MARKDOWN_PATH,
    STAGE1_FAMILY_CLOSED,
    admission,
    admission_identity,
    coverage_policy_decision,
    preregistration,
)
from app.predictive.internal_nonlinear_report import load_result, validate_internal_nonlinear
from app.predictive.internal_structure import ExperimentError

ROOT = Path(__file__).resolve().parents[2]


def state() -> dict:
    return json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))


def test_the_committed_experiment_validates_against_its_own_frozen_records():
    findings = validate_internal_nonlinear(ROOT, data_available=False)
    assert findings["status"] == "PASS"
    assert findings["data_replayed"] is False
    assert findings["stage1_family_status"] == STAGE1_FAMILY_CLOSED
    assert findings["coverage_policy_option"] == "OPTION_1_EXECUTE_UNCHANGED"


def test_the_frozen_records_on_disk_are_what_the_code_declares():
    assert (
        json.loads((ROOT / PREREGISTRATION_PATH).read_text(encoding="utf-8")) == preregistration()
    )
    assert json.loads((ROOT / ADMISSION_PATH).read_text(encoding="utf-8")) == admission(ROOT)
    assert state()["predictive_internal_nonlinear"]["admission_identity_sha256"] == (
        admission_identity(ROOT)
    )


def test_the_coverage_ruling_is_recorded_everywhere_and_weakened_nowhere():
    ruling = coverage_policy_decision()
    result = load_result(ROOT)
    prereg = json.loads((ROOT / PREREGISTRATION_PATH).read_text(encoding="utf-8"))
    admitted = json.loads((ROOT / ADMISSION_PATH).read_text(encoding="utf-8"))
    assert prereg["coverage_policy_decision"] == ruling
    assert admitted["coverage_policy_decision"] == ruling
    assert result["coverage_policy_decision"] == ruling
    assert ruling["option_taken"] == "OPTION_1_EXECUTE_UNCHANGED"
    assert ruling["decided_before_any_hgbr_outer_evaluation_number"] is True
    assert ruling["gates_waived"] is False
    assert ruling["gates_reinterpreted"] is False
    assert ruling["gates_removed"] is False
    assert ruling["coverage_thresholds_changed"] is False
    assert ruling["all_advancement_conditions_all_must_hold"] is True
    assert ruling["directional_result_may_rescue_formal_advancement"] is False


def test_the_coverage_gates_still_bind_in_the_committed_result():
    """The ruling predicted these two would fail; the gate records them as failures."""
    result = load_result(ROOT)
    failed = result["advancement_gate"]["failed_conditions"]
    assert "POOLED_COVERAGE_AT_LEAST_0_95" in failed
    assert "EVERY_FOLD_COVERAGE_AT_LEAST_0_90" in failed
    assert result["terminal_classification"] == NO_ADVANCE
    assert result["advancement_gate"]["all_must_hold"] is True
    assert result["advancement_gate"]["secondary_metrics_used_to_rescue"] is False


def test_the_stage1_family_is_closed_with_nothing_reserved():
    result = load_result(ROOT)
    budget = result["search_budget"]
    record = state()["predictive_internal_nonlinear"]
    assert budget["stage1_configurations_consumed"] == 2
    assert budget["stage1_configurations_remaining"] == 0
    assert budget["configurations_reserved"] == []
    assert budget["configurations_executed"] == [
        "INTERNAL_LINEAR_DUAL_HEAD_V1",
        "INTERNAL_HGBR_DUAL_HEAD_V1",
    ]
    assert budget["family_status"] == STAGE1_FAMILY_CLOSED
    assert record["stage1_family_status"] == STAGE1_FAMILY_CLOSED
    assert state()["predictive_research_objective"]["predictive_experiments_completed"] == 2


def test_the_linear_checkpoint_was_replayed_reconciled_and_left_unchanged():
    against_linear = load_result(ROOT)["linear_comparison"]
    assert against_linear["classification"] == "DESCRIPTIVE_NOT_A_PREREGISTERED_TEST"
    assert against_linear["independent_reconciliation"] == "PASS"
    assert against_linear["replay_consumes_stage1_budget"] is False
    assert against_linear["linear_results_changed"] is False
    linear = json.loads(
        (
            ROOT / "research/experiments/EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD/result.json"
        ).read_text(encoding="utf-8")
    )
    assert against_linear["linear_terminal_classification"] == linear["terminal_classification"]
    assert (
        against_linear["pooled"]["linear_win_rate"]
        == linear["candidate"]["pooled_directional"]["win_rate"]
    )
    # Both configurations abstain on exactly the same timestamps, as the ruling said.
    assert against_linear["abstention_sets_identical"] is True
    assert against_linear["directional_agreement"]["declared_sets_identical"] is True


def test_the_win_rate_is_never_recorded_without_sample_size_and_coverage():
    pooled = load_result(ROOT)["candidate"]["pooled_directional"]
    assert pooled["win_rate"] is not None
    assert pooled["coverage"] is not None
    assert pooled["actionable_directional_predictions"] > 0
    assert (
        pooled["actionable_directional_predictions"]
        + pooled["abstentions"]
        + pooled["declared_side_on_neutral_truth"]
        == pooled["eligible_decision_timestamps"]
    )
    assert pooled["brier_score"] is not None
    assert len(pooled["reliability_table"]) == 10


def test_the_markdown_report_is_generated_from_the_committed_result():
    markdown = (ROOT / REPORT_MARKDOWN_PATH).read_text(encoding="utf-8")
    record = state()["predictive_internal_nonlinear"]
    assert record["terminal_classification"] in markdown
    assert "OPTION_1_EXECUTE_UNCHANGED" in markdown
    assert "PREDICTIVE-INTERNAL-STRUCTURE-V1 results unchanged" in markdown
    for name in record["failed_gates"]:
        assert name in markdown


def test_the_validator_rejects_a_ruling_edited_after_the_fact(tmp_path):
    import shutil

    copy = tmp_path / "repository"
    for relative in (
        PREREGISTRATION_PATH,
        ADMISSION_PATH,
        "research/protocols/PREDICTIVE-STAGE1-INTERNAL-SEARCH-PLAN-V1.json",
        "research/experiments/EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD/result.json",
        "research/experiments/EXP-PRED-002-INTERNAL-HGBR-DUAL-HEAD/result.json",
        "reports/research/PREDICTIVE-INTERNAL-NONLINEAR-V1.json",
        "reports/research/PREDICTIVE-INTERNAL-NONLINEAR-V1.md",
        "reports/research/PREDICTIVE-BASELINES-V1.json",
    ):
        destination = copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    for relative in ("backend/app/predictive", "scripts/run_predictive_internal_nonlinear.py"):
        source, destination = ROOT / relative, copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, destination)

    prereg_path = copy / PREREGISTRATION_PATH
    tampered = json.loads(prereg_path.read_text(encoding="utf-8"))
    tampered["coverage_policy_decision"]["gates_waived"] = True
    prereg_path.write_text(
        json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    with pytest.raises(ExperimentError):
        validate_internal_nonlinear(copy, data_available=False)
