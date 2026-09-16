"""Guards for the committed `PREDICTIVE-INTERNAL-STRUCTURE-V1` records.

These run without market data. They prove the frozen records still match the code, the
admission artifact still hashes the implementation that produced the result, the
advancement gate follows from the reported numbers rather than from the classification
string written beside them, and the negative result is preserved exactly as observed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.predictive.internal_report import load_result, validate_internal_structure
from app.predictive.internal_structure import (
    ADMISSION_PATH,
    EXPERIMENT_ID,
    NO_ADVANCE,
    PREREGISTRATION_PATH,
    REPORT_MARKDOWN_PATH,
    RESERVED_EXPERIMENT_ID,
    SEARCH_PLAN_PATH,
    ExperimentError,
    admission,
    admission_identity,
    preregistration,
    search_plan,
)

ROOT = Path(__file__).resolve().parents[2]


def state() -> dict:
    return json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))


def test_the_committed_experiment_validates_against_its_own_frozen_records():
    findings = validate_internal_structure(ROOT, data_available=False)
    assert findings["status"] == "PASS"
    assert findings["data_replayed"] is False
    assert findings["stage1_configurations_consumed"] == 1


def test_the_frozen_records_on_disk_are_what_the_code_declares():
    assert json.loads((ROOT / SEARCH_PLAN_PATH).read_text(encoding="utf-8")) == search_plan()
    assert (
        json.loads((ROOT / PREREGISTRATION_PATH).read_text(encoding="utf-8")) == preregistration()
    )
    assert json.loads((ROOT / ADMISSION_PATH).read_text(encoding="utf-8")) == admission(ROOT)


def test_the_admission_artifact_still_hashes_the_implementation_it_admitted():
    record = admission(ROOT)
    assert record["status"] == "PASS"
    assert record["market_results_observed"] == record["model_fits_executed"] == 0
    assert record["sealed_queries"] == record["post_cutoff_access"] == 0
    assert state()["predictive_internal_structure"]["admission_identity_sha256"] == (
        admission_identity(ROOT)
    )


def test_the_reserved_configuration_was_not_executed_and_is_still_scheduled():
    assert not (ROOT / "research/experiments" / RESERVED_EXPERIMENT_ID).exists()
    record = state()["predictive_internal_structure"]
    assert record["reserved_configuration"] == "INTERNAL_HGBR_DUAL_HEAD_V1"
    assert record["reserved_configuration_executed"] is False
    assert record["stage1_configurations_remaining"] == 1


def test_the_negative_result_is_preserved_exactly_as_observed():
    result = load_result(ROOT)
    record = state()["predictive_internal_structure"]
    assert result["experiment_id"] == EXPERIMENT_ID
    assert result["terminal_classification"] == NO_ADVANCE
    assert record["terminal_classification"] == NO_ADVANCE
    # Every predeclared gate that failed is named, not summarised away.
    assert record["failed_gates"] == result["advancement_gate"]["failed_conditions"]
    assert record["failed_gates"]
    assert result["advancement_gate"]["secondary_metrics_used_to_rescue"] is False
    assert result["boundaries"]["post_result_tuning"] is False


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
    # The candidate declares a probability, so it is calibrated like any other.
    assert pooled["brier_score"] is not None
    assert len(pooled["reliability_table"]) == 10


def test_the_markdown_report_is_generated_from_the_committed_result():
    markdown = (ROOT / REPORT_MARKDOWN_PATH).read_text(encoding="utf-8")
    record = state()["predictive_internal_structure"]
    assert record["terminal_classification"] in markdown
    assert "PREDICTIVE-BASELINES-V1, unchanged" in markdown
    for name in record["failed_gates"]:
        assert name in markdown


def test_the_validator_rejects_a_result_whose_gate_was_edited_after_the_fact(tmp_path):
    import shutil

    copy = tmp_path / "repository"
    for relative in (
        SEARCH_PLAN_PATH,
        PREREGISTRATION_PATH,
        ADMISSION_PATH,
        "research/experiments/EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD/result.json",
        "reports/research/PREDICTIVE-INTERNAL-STRUCTURE-V1.json",
        "reports/research/PREDICTIVE-INTERNAL-STRUCTURE-V1.md",
        "reports/research/PREDICTIVE-BASELINES-V1.json",
    ):
        destination = copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    for relative in (
        "backend/app/predictive",
        "scripts/run_predictive_internal_structure.py",
    ):
        source = ROOT / relative
        destination = copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, destination)

    result_path = copy / "research/experiments/EXP-PRED-001-INTERNAL-LINEAR-DUAL-HEAD/result.json"
    tampered = json.loads(result_path.read_text(encoding="utf-8"))
    tampered["terminal_classification"] = "ADVANCE_INTERNAL_LINEAR_V1"
    tampered["advancement_gate"]["failed_conditions"] = []
    payload = json.dumps(tampered, indent=2, sort_keys=True) + "\n"
    result_path.write_text(payload, encoding="utf-8", newline="\n")
    (copy / "reports/research/PREDICTIVE-INTERNAL-STRUCTURE-V1.json").write_text(
        payload, encoding="utf-8", newline="\n"
    )
    with pytest.raises(ExperimentError):
        validate_internal_structure(copy, data_available=False)
