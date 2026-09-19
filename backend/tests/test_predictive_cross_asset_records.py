"""Guards for the committed `PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1` records.

These run without market data. They prove the source audit precedes the results and chose the
folds on source availability alone, the frozen records still match the code, both gates are
re-derived from the reported numbers, the family closes on two executed configurations, and no
earlier predictive result was rewritten.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.predictive.cross_asset import (
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
from app.predictive.cross_asset_audit import AUDIT_PATH, PASS
from app.predictive.cross_asset_report import load_result, validate_cross_asset
from app.predictive.internal_structure import ExperimentError

ROOT = Path(__file__).resolve().parents[2]
RECORD_KEY = "predictive_stage3_cross_asset_breadth"


def state() -> dict:
    return json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))


def audit() -> dict:
    return json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))


def test_the_committed_experiments_validate_against_their_frozen_records():
    findings = validate_cross_asset(ROOT, data_available=False)
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
    assert state()[RECORD_KEY]["admission_identity_sha256"] == admission_identity(ROOT)


def test_the_source_audit_precedes_the_results_and_chose_folds_on_availability_alone():
    record = audit()
    assert record["status"] == PASS
    assert record["target_bearing_model_fitted"] is False
    coverage = record["coverage"]
    assert coverage["return_values_inspected"] is False
    assert coverage["labels_inspected"] is False
    assert coverage["candidate_predictions_inspected"] is False
    assert coverage["fold_selection_rule"] == "DETERMINISTIC_SOURCE_AVAILABILITY_ONLY"
    assert coverage["admissible_folds"] == ["2020", "2021", "2022", "2023", "2024"]
    assert coverage["admissible_eligible_timestamps"] >= 40_000
    # 2019 was excluded by two stated source conditions, not by outcome.
    conditions = coverage["by_fold"]["2019"]["conditions"]
    assert coverage["by_fold"]["2019"]["included"] is False
    assert conditions["COVERAGE_AT_LEAST_0_95"] is False
    assert conditions["AT_LEAST_180_DAYS_OF_CAUSAL_PRE_FOLD_HISTORY"] is False


def test_the_point_in_time_claims_were_exercised_rather_than_asserted():
    semantics = audit()["semantics"]
    probes = [probe for probe in semantics["probes"] if probe["available"]]
    assert probes
    for probe in probes:
        assert probe["endpoint_only_panel_reproduces_the_vector"] is True
        assert probe["column_permutation_reproduces_the_vector"] is True
        assert probe["point_in_time_universe"] >= 30
    # An endpoint-only panel gives each asset four bars in its whole life, far under 504.
    assert semantics["endpoint_only_panel_rows_per_asset"] == 4
    assert semantics["retired_participation_row_rule"] == 504
    for name in (
        "ONLY_THE_FOUR_ENDPOINT_BARS_ENTER_A_FEATURE",
        "NO_BAR_AFTER_THE_DECISION_INSTANT_ENTERS_A_FEATURE",
        "NO_FUTURE_SURVIVAL_FILTER",
        "NO_WHOLE_SAMPLE_PARTICIPATION_THRESHOLD",
        "RETIRED_504_ROW_PARTICIPATION_RULE_NOT_REVIVED",
        "NO_MARKET_CAP_FUTURE_VOLUME_OR_SURVIVOR_WEIGHTING",
        "PREDICTION_TARGET_ABSENT_FROM_THE_PANEL",
        "NO_LEVERAGED_TOKEN_IN_THE_PANEL",
    ):
        assert semantics["checks"][name] is True, name


def test_the_admitted_source_is_the_governed_archive_and_excludes_the_target():
    source = admission(ROOT)["source"]
    manifest = json.loads((ROOT / source["manifest"]).read_text(encoding="utf-8"))
    assert source["substrate_file_sha256"] == manifest["substrate"]["sha256"]
    assert source["provider"] == "Binance" and source["market_type"] == "spot"
    assert source["interval"] == "1h" and source["quote_asset"] == "USDT"
    assert source["credential_free"] is True
    assert source["third_party_vendor_used"] is False
    assert source["reconstructed_or_backfilled"] is False
    assert source["historical_cross_section_results_imported"] is False
    assert source["target_symbol_excluded_from_cross_section"] is True
    assert source["fields_read"] == ["symbol", "open_time", "close"]
    for name in ("open", "high", "low", "volume", "quote_volume"):
        assert name in source["forbidden_fields"]
    assert source["interpolation"] is False and source["forward_fill"] is False
    assert source["nearest_bar_substitution"] is False
    assert source["cross_sectional_weighting"] == "EQUAL_WEIGHTED"
    assert source["minimum_point_in_time_universe"] == 30
    assert source["required_endpoint_bars"] == 4


def test_both_configurations_were_executed_and_the_family_closed():
    result = load_result(ROOT)
    record = state()[RECORD_KEY]
    budget = result["search_budget"]
    assert budget["configurations_consumed"] == FAMILY_SIZE == 2
    assert budget["configurations_remaining"] == 0
    assert budget["result_dependent_early_stop"] is False
    assert record["configurations_consumed"] == 2
    assert set(record["configurations"]) == set(EXPERIMENT_IDS.values())
    included = result["folds"]["included_folds"]
    assert record["required_non_negative_folds"] == required_non_negative_folds(len(included)) == 4
    for model_version in CONFIGURATION_ORDER:
        assert (ROOT / result_path(model_version)).is_file()
        trials = json.loads((ROOT / trials_path(model_version)).read_text(encoding="utf-8"))
        assert [item["fold"] for item in trials] == included
    assert state()["predictive_research_objective"]["predictive_experiments_completed"] == 8
    assert record["paired_bootstrap_seed"] == PAIRED_SEED == 20260919


def test_the_family_declares_no_magnitude_and_none_was_fitted():
    result = load_result(ROOT)
    assert state()[RECORD_KEY]["magnitude_declared"] is False
    assert result["scoring"]["magnitude_declared"] is False
    for model_version in CONFIGURATION_ORDER:
        configuration = result["configurations"][model_version]
        pooled = configuration["candidate"]["pooled_directional"]
        assert configuration["model"]["declares_magnitude"] is False
        assert pooled["magnitude_flag"] == "MAGNITUDE_NOT_DECLARED"
        assert pooled["magnitude_mae_percentage_points"] is None
        assert configuration["model_fits"] == {
            "direction_base": len(included_folds(result)),
            "direction_calibration": len(included_folds(result)),
            "total": 2 * len(included_folds(result)),
        }


def included_folds(result: dict) -> list[str]:
    return list(result["folds"]["included_folds"])


def test_the_negative_family_disposition_is_preserved_with_no_sealed_eligibility():
    result = load_result(ROOT)
    disposition = result["family_disposition"]
    record = state()[RECORD_KEY]
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


def test_the_adverse_interval_is_recorded_without_being_inverted():
    """The first interval in this generation to exclude zero does so on the wrong side."""
    result = load_result(ROOT)
    for model_version in CONFIGURATION_ORDER:
        primary = result["configurations"][model_version]["primary_comparison"]
        lower, upper = primary["paired_interval"]["interval"]
        assert lower < 0.0 and upper < 0.0
        assert primary["pooled_delta"] < 0.0
        assert (
            "PAIRED_INTERVAL_LOWER_BOUND_ABOVE_ZERO"
            in (result["configurations"][model_version]["advancement_gate"]["failed_conditions"])
        )
    assert result["boundaries"]["previous_24h_sign_persistence_inverted"] is False
    assert result["boundaries"]["post_result_tuning"] is False
    assert result["family_disposition"]["descendant_tuned"] is False


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
    assert current["predictive_stage2_open_interest"]["family_disposition"] == FAMILY_REJECTED
    assert current["predictive_stage1_disposition"]["family_disposition"] == FAMILY_REJECTED


def test_the_markdown_report_is_generated_from_the_committed_result():
    markdown = (ROOT / REPORT_MARKDOWN_PATH).read_text(encoding="utf-8")
    record = state()[RECORD_KEY]
    assert record["family_disposition"] in markdown
    assert FAMILY in markdown
    assert "BTCUSDT is removed from the cross-section entirely" in markdown
    assert "no future-survival filter" in markdown
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
        "docs/contracts/PREDICTIVE_CROSS_ASSET_BREADTH_CONTEXT_V1.md",
        "data/manifests/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.json",
        "reports/research/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1.json",
        "reports/research/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1.md",
        "reports/research/PREDICTIVE-BASELINES-V1.json",
    ):
        destination = copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    for relative in ("backend/app/predictive", "scripts/run_predictive_cross_asset.py"):
        source, destination = ROOT / relative, copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, destination)

    report = copy / "reports/research/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1.json"
    tampered = json.loads(report.read_text(encoding="utf-8"))
    first = CONFIGURATION_ORDER[0]
    tampered["configurations"][first]["terminal_classification"] = (
        "ADVANCE_CROSS_ASSET_BREADTH_LINEAR_V1"
    )
    tampered["configurations"][first]["advancement_gate"]["failed_conditions"] = []
    report.write_text(
        json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    with pytest.raises(ExperimentError):
        validate_cross_asset(copy, data_available=False)
