"""Guards for the committed `PREDICTIVE-STAGE2-OPEN-INTEREST-V1` records.

These run without market data. They prove the source audit precedes the results and chose the
folds on source quality alone, the frozen records still match the code, both gates are
re-derived from the reported numbers, the family closes on two executed configurations, and
no earlier predictive result was rewritten.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.predictive.internal_structure import ExperimentError
from app.predictive.open_interest import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    EXPERIMENT_IDS,
    FAMILY,
    FAMILY_REJECTED,
    FAMILY_SIZE,
    NOT_ELIGIBLE,
    PAIRED_SEED,
    REPORT_MARKDOWN_PATH,
    SEARCH_PLAN_PATH,
    admission,
    admission_identity,
    director_decisions,
    preregistration,
    preregistration_path,
    required_non_negative_folds,
    result_path,
    search_plan,
    trials_path,
)
from app.predictive.open_interest_audit import AUDIT_PATH, PASS
from app.predictive.open_interest_report import load_result, validate_open_interest

ROOT = Path(__file__).resolve().parents[2]


def state() -> dict:
    return json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))


def audit() -> dict:
    return json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))


def test_the_committed_experiments_validate_against_their_frozen_records():
    findings = validate_open_interest(ROOT, data_available=False)
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
        assert committed == preregistration(model_version, ROOT)
    assert state()["predictive_stage2_open_interest"]["admission_identity_sha256"] == (
        admission_identity(ROOT)
    )


def test_the_source_audit_precedes_the_results_and_chose_folds_on_source_quality_alone():
    record = audit()
    assert record["status"] == PASS
    assert record["target_bearing_model_fitted"] is False
    coverage = record["coverage"]
    assert coverage["return_values_inspected"] is False
    assert coverage["candidate_predictions_inspected"] is False
    assert coverage["fold_selection_rule"] == "DETERMINISTIC_SOURCE_QUALITY_ONLY"
    assert coverage["admissible_folds"] == ["2022", "2023", "2024"]
    assert len(coverage["admissible_folds"]) >= 3
    assert coverage["admissible_eligible_timestamps"] >= 20_000
    # The two excluded folds were excluded by a stated source condition, not by outcome.
    assert coverage["by_fold"]["2020"]["included"] is False
    assert coverage["by_fold"]["2021"]["included"] is False
    assert (
        coverage["by_fold"]["2021"]["conditions"]["AT_LEAST_180_DAYS_OF_PRIOR_SOURCE_HISTORY"]
        is False
    )


def test_the_admitted_source_is_the_official_archive_and_nothing_else():
    source = admission(ROOT)["source"]
    manifest = json.loads((ROOT / source["manifest"]).read_text(encoding="utf-8"))
    assert source["source_class"] == "OFFICIAL_BINANCE_PUBLIC_DATA_ARCHIVE"
    assert source["credential_free"] is True
    assert source["third_party_vendor_used"] is False
    assert source["rest_snapshot_history_used"] is False
    assert source["reconstructed_or_backfilled"] is False
    assert source["canonical_file_sha256"] == manifest["canonical"]["file_sha256"]
    assert (
        source["official_checksums_verified"]
        == source["archive_days"]
        == manifest["archive"]["days"]
    )
    assert source["fields_read"] == ["create_time", "sum_open_interest"]
    assert source["open_interest_value_admitted"] is False
    assert "sum_open_interest_value" in source["forbidden_fields"]
    assert source["cadence_seconds"] == 300
    assert source["maximum_state_age_seconds"] == 600
    assert source["interpolation"] is False and source["forward_fill"] is False
    assert source["post_cutoff_records"] == 0
    assert manifest["integrity"]["conflicting_duplicate_timestamps"] == 0
    assert manifest["integrity"]["duplicate_policy"] == (
        "COLLAPSE_EXACT_REPETITION_FAIL_CLOSED_ON_CONFLICT"
    )


def test_both_configurations_were_executed_and_the_family_closed():
    result = load_result(ROOT)
    record = state()["predictive_stage2_open_interest"]
    budget = result["search_budget"]
    assert budget["configurations_consumed"] == FAMILY_SIZE == 2
    assert budget["configurations_remaining"] == 0
    assert budget["result_dependent_early_stop"] is False
    assert record["configurations_consumed"] == 2
    assert set(record["configurations"]) == set(EXPERIMENT_IDS.values())
    included = result["folds"]["included_folds"]
    assert record["required_non_negative_folds"] == required_non_negative_folds(len(included)) == 2
    for model_version in CONFIGURATION_ORDER:
        assert (ROOT / result_path(model_version)).is_file()
        trials = json.loads((ROOT / trials_path(model_version)).read_text(encoding="utf-8"))
        assert [item["fold"] for item in trials] == included
    assert state()["predictive_research_objective"]["predictive_experiments_completed"] == 6
    assert record["paired_bootstrap_seed"] == PAIRED_SEED == 20260917


def test_the_negative_family_disposition_is_preserved_with_no_sealed_eligibility():
    result = load_result(ROOT)
    disposition = result["family_disposition"]
    record = state()["predictive_stage2_open_interest"]
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


def test_the_director_decisions_rescue_nothing_and_prior_results_are_unchanged():
    decisions = director_decisions()
    current = state()
    assert load_result(ROOT)["director_decisions"] == decisions
    assert decisions["generation_continues"] is True
    assert decisions["target_or_horizon_changed"] is False
    assert decisions["canonical_hourly_gap_repaired"] is False
    assert decisions["contiguity_rule_relaxed"] is False
    assert decisions["basis_authorized"] is False
    assert decisions["rejected_family_results_immutable"] is True
    assert current["predictive_internal_structure"]["terminal_classification"] == (
        "NO_ADVANCE_INTERNAL_LINEAR_V1"
    )
    assert current["predictive_internal_nonlinear"]["terminal_classification"] == (
        "NO_ADVANCE_INTERNAL_HGBR_V1"
    )
    assert current["predictive_stage2_settled_funding"]["family_disposition"] == FAMILY_REJECTED
    assert current["predictive_stage1_disposition"]["family_disposition"] == FAMILY_REJECTED


def test_the_markdown_report_is_generated_from_the_committed_result():
    markdown = (ROOT / REPORT_MARKDOWN_PATH).read_text(encoding="utf-8")
    record = state()["predictive_stage2_open_interest"]
    assert record["family_disposition"] in markdown
    assert FAMILY in markdown
    assert "a record stamped exactly at the decision instant is unavailable" in markdown
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
        AUDIT_PATH,
        *(preregistration_path(name) for name in CONFIGURATION_ORDER),
        *(result_path(name) for name in CONFIGURATION_ORDER),
        *(trials_path(name) for name in CONFIGURATION_ORDER),
        "docs/contracts/PREDICTIVE_OPEN_INTEREST_STRUCTURE_V1.md",
        "data/manifests/BTCUSDT-USDM-OPEN-INTEREST-DEV-v1.json",
        "reports/research/PREDICTIVE-STAGE2-OPEN-INTEREST-V1.json",
        "reports/research/PREDICTIVE-STAGE2-OPEN-INTEREST-V1.md",
        "reports/research/PREDICTIVE-BASELINES-V1.json",
    ):
        destination = copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    for relative in ("backend/app/predictive", "scripts/run_predictive_open_interest.py"):
        source, destination = ROOT / relative, copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, destination)

    report = copy / "reports/research/PREDICTIVE-STAGE2-OPEN-INTEREST-V1.json"
    tampered = json.loads(report.read_text(encoding="utf-8"))
    first = CONFIGURATION_ORDER[0]
    tampered["configurations"][first]["terminal_classification"] = "ADVANCE_OPEN_INTEREST_LINEAR_V1"
    tampered["configurations"][first]["advancement_gate"]["failed_conditions"] = []
    report.write_text(
        json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    with pytest.raises(ExperimentError):
        validate_open_interest(copy, data_available=False)
