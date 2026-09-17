"""Guards for the committed `PREDICTIVE-STAGE2-SETTLED-FUNDING-V1` records.

These run without market data. They prove the frozen records still match the code, the
admission artifact still hashes the implementation and the admitted source, both gates are
re-derived from the reported numbers, the family closes on two executed configurations, and
neither Stage-1 result was rewritten.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.predictive.internal_structure import ExperimentError
from app.predictive.settled_funding import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    EVALUATION_FOLDS,
    EXPERIMENT_IDS,
    FAMILY,
    FAMILY_REJECTED,
    FAMILY_SIZE,
    NOT_ELIGIBLE,
    REPORT_MARKDOWN_PATH,
    SEARCH_PLAN_PATH,
    admission,
    admission_identity,
    preregistration,
    preregistration_path,
    result_path,
    search_plan,
    stage1_disposition,
    trials_path,
)
from app.predictive.settled_funding_report import load_result, validate_settled_funding

ROOT = Path(__file__).resolve().parents[2]


def state() -> dict:
    return json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))


def test_the_committed_experiments_validate_against_their_frozen_records():
    findings = validate_settled_funding(ROOT, data_available=False)
    assert findings["status"] == "PASS"
    assert findings["data_replayed"] is False
    assert set(findings["classifications"]) == set(CONFIGURATION_ORDER)


def test_the_frozen_records_on_disk_are_what_the_code_declares():
    assert json.loads((ROOT / SEARCH_PLAN_PATH).read_text(encoding="utf-8")) == search_plan()
    assert json.loads((ROOT / ADMISSION_PATH).read_text(encoding="utf-8")) == admission(ROOT)
    for model_version in CONFIGURATION_ORDER:
        committed = json.loads(
            (ROOT / preregistration_path(model_version)).read_text(encoding="utf-8")
        )
        assert committed == preregistration(model_version)
    assert state()["predictive_stage2_settled_funding"]["admission_identity_sha256"] == (
        admission_identity(ROOT)
    )


def test_the_admission_precedes_any_result_and_pins_the_admitted_source():
    record = admission(ROOT)
    assert record["status"] == "PASS"
    assert record["market_results_observed"] == record["model_fits_executed"] == 0
    assert record["sealed_queries"] == record["post_cutoff_access"] == 0
    manifest = json.loads((ROOT / record["source"]["manifest"]).read_text(encoding="utf-8"))
    assert record["source"]["canonical_file_sha256"] == manifest["canonical"]["file_sha256"]
    assert record["source"]["fields_read"] == ["funding_time", "funding_rate"]
    assert record["source"]["predictive_contract"] != record["source"]["historical_contract"]
    assert (ROOT / record["source"]["predictive_contract"]).is_file()


def test_both_configurations_were_executed_and_the_family_closed():
    result = load_result(ROOT)
    record = state()["predictive_stage2_settled_funding"]
    budget = result["search_budget"]
    assert budget["configurations_consumed"] == FAMILY_SIZE == 2
    assert budget["configurations_remaining"] == 0
    assert budget["result_dependent_early_stop"] is False
    assert record["configurations_consumed"] == 2
    assert set(record["configurations"]) == set(EXPERIMENT_IDS.values())
    for model_version in CONFIGURATION_ORDER:
        assert (ROOT / result_path(model_version)).is_file()
        trials = json.loads((ROOT / trials_path(model_version)).read_text(encoding="utf-8"))
        assert len(trials) == len(EVALUATION_FOLDS) == 5
        assert [item["fold"] for item in trials] == list(EVALUATION_FOLDS)
    assert state()["predictive_research_objective"]["predictive_experiments_completed"] == 4


def test_the_negative_family_disposition_is_preserved_with_no_sealed_eligibility():
    result = load_result(ROOT)
    disposition = result["family_disposition"]
    record = state()["predictive_stage2_settled_funding"]
    assert disposition["disposition"] == FAMILY_REJECTED
    assert record["family_disposition"] == FAMILY_REJECTED
    assert disposition["advancing_configurations"] == []
    assert disposition["post_hoc_winner_selected"] is False
    assert disposition["sealed_queried"] is False
    assert disposition["champion_created"] is False
    assert disposition["prospective_observer_created"] is False
    assert disposition["descendant_tuned"] is False
    for value in disposition["sealed_eligibility"].values():
        assert value == NOT_ELIGIBLE
    for entry in record["configurations"].values():
        assert entry["sealed_eligibility"] == NOT_ELIGIBLE
        assert entry["failed_gates"]


def test_every_win_rate_is_recorded_with_sample_size_and_coverage():
    result = load_result(ROOT)
    for model_version in CONFIGURATION_ORDER:
        pooled = result["configurations"][model_version]["candidate"]["pooled_directional"]
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


def test_the_stage1_closure_is_recorded_and_its_results_are_untouched():
    current = state()
    disposition = stage1_disposition()
    assert (
        current["predictive_stage1_disposition"]["family_disposition"]
        == (disposition["family_disposition"])
    )
    assert load_result(ROOT)["stage1_disposition"] == disposition
    # The two executed Stage-1 records keep exactly the classifications they were given.
    assert current["predictive_internal_structure"]["terminal_classification"] == (
        "NO_ADVANCE_INTERNAL_LINEAR_V1"
    )
    assert current["predictive_internal_nonlinear"]["terminal_classification"] == (
        "NO_ADVANCE_INTERNAL_HGBR_V1"
    )
    assert current["predictive_internal_structure"]["stage1_configurations_remaining"] == 1
    assert current["predictive_internal_nonlinear"]["stage1_configurations_remaining"] == 0


def test_the_markdown_report_is_generated_from_the_committed_result():
    markdown = (ROOT / REPORT_MARKDOWN_PATH).read_text(encoding="utf-8")
    record = state()["predictive_stage2_settled_funding"]
    assert record["family_disposition"] in markdown
    assert FAMILY in markdown
    assert "a settlement stamped exactly at the decision instant is unavailable" in markdown
    for entry in record["configurations"].values():
        assert entry["terminal_classification"] in markdown
        for gate in entry["failed_gates"]:
            assert gate in markdown


def test_the_validator_rejects_a_classification_edited_after_the_fact(tmp_path):
    import shutil

    copy = tmp_path / "repository"
    for relative in (
        SEARCH_PLAN_PATH,
        ADMISSION_PATH,
        *(preregistration_path(name) for name in CONFIGURATION_ORDER),
        *(result_path(name) for name in CONFIGURATION_ORDER),
        *(trials_path(name) for name in CONFIGURATION_ORDER),
        "docs/contracts/PREDICTIVE_SETTLED_FUNDING_STRUCTURE_V1.md",
        "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json",
        "reports/research/PREDICTIVE-STAGE2-SETTLED-FUNDING-V1.json",
        "reports/research/PREDICTIVE-STAGE2-SETTLED-FUNDING-V1.md",
        "reports/research/PREDICTIVE-BASELINES-V1.json",
    ):
        destination = copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    for relative in ("backend/app/predictive", "scripts/run_predictive_settled_funding.py"):
        source, destination = ROOT / relative, copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, destination)

    report = copy / "reports/research/PREDICTIVE-STAGE2-SETTLED-FUNDING-V1.json"
    tampered = json.loads(report.read_text(encoding="utf-8"))
    first = CONFIGURATION_ORDER[0]
    tampered["configurations"][first]["terminal_classification"] = "ADVANCE_FUNDING_LINEAR_V1"
    tampered["configurations"][first]["advancement_gate"]["failed_conditions"] = []
    report.write_text(
        json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    with pytest.raises(ExperimentError):
        validate_settled_funding(copy, data_available=False)
