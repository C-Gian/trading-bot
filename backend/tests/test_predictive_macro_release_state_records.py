from __future__ import annotations

import json
from pathlib import Path

from app.predictive.internal_structure import content_hash
from app.predictive.macro_release_state import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    EXPERIMENT_IDS,
    FAMILY,
    FAMILY_SIZE,
    HYPOTHESIS_IDS,
    MINIMUM_IMPORTANT_EFFECT,
    NOT_ELIGIBLE,
    PAIRED_SEED,
    PREDECESSOR_RECORDS,
    PRIOR_EXPERIMENT_RESULTS,
    REPORT_JSON_PATH,
    SEARCH_PLAN_PATH,
    admission,
    admission_identity,
    preregistration,
    preregistration_path,
    required_non_negative_folds,
    result_path,
    search_plan,
    trials_path,
)
from app.predictive.macro_release_state_audit import (
    CANDIDATE_FOLDS,
    FOLD_COVERAGE_GATE,
    MINIMUM_ADMISSIBLE_FOLDS,
    MINIMUM_TRAINING_HISTORY_DAYS,
    PASS,
    POOLED_COVERAGE_GATE,
)
from app.predictive.macro_release_state_report import (
    configuration_result_document,
    markdown_bytes,
    report_bytes,
    trials_document,
    validate_macro_release_state,
)
from app.predictive.macro_release_state_source import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    FEATURE_SET_VERSION,
    PREDECESSOR_FEATURE_SET_VERSION,
)

ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = "reports/validation/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1-SOURCE-AUDIT.json"


def read(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_the_source_gate_decided_every_fold_before_any_outcome_or_fit():
    audit = read(AUDIT_PATH)
    assert audit["status"] == PASS
    assert audit["target_bearing_model_fitted"] is False
    coverage = audit["coverage"]
    assert coverage["candidate_folds"] == list(CANDIDATE_FOLDS)
    assert coverage["fold_selection_rule"] == "TIMESTAMPS_AND_SOURCE_VALIDITY_ONLY"
    assert coverage["btc_close_column_loaded"] is False
    assert coverage["btc_return_values_inspected"] is False
    assert coverage["btc_direction_labels_inspected"] is False
    assert coverage["candidate_predictions_inspected"] is False
    assert audit["boundaries"]["btc_outcomes_read_for_gate"] is False
    assert audit["boundaries"]["model_predictions_read_for_gate"] is False
    assert len(coverage["admissible_folds"]) >= MINIMUM_ADMISSIBLE_FOLDS
    assert coverage["pooled_source_feature_coverage"] >= POOLED_COVERAGE_GATE
    for name in coverage["admissible_folds"]:
        record = coverage["by_fold"][name]
        assert record["coverage"] >= FOLD_COVERAGE_GATE
        assert record["causal_feature_valid_history_days"] >= MINIMUM_TRAINING_HISTORY_DAYS
    for name in coverage["excluded_candidate_folds"]:
        assert coverage["by_fold"][name]["included"] is False


def test_the_release_state_semantics_and_cadence_integrity_were_demonstrated():
    audit = read(AUDIT_PATH)
    assert audit["provenance"]["passed"] is True
    semantics = audit["semantics"]
    assert semantics["passed"] is True
    assert semantics["independent_snapshot_mismatches"] == 0
    assert semantics["exact_month_anchor_mismatches"] == 0
    assert semantics["exact_month_anchor_revision_distinguishing_cases"] > 0
    for name in (
        "ADDING_LATER_VINTAGE_CANNOT_CHANGE_EARLIER_FEATURE_VECTOR",
        "LATER_VINTAGE_BECOMES_VISIBLE_ONLY_AFTER_AVAILABILITY",
        "A_FUTURE_MONTHLY_RELEASE_IS_INVISIBLE_BEFORE_AVAILABILITY",
        "A_LATEST_KNOWN_MONTHLY_RELEASE_PERSISTS_BETWEEN_RELEASES",
        "EXACT_MONTH_ANCHORS_COME_FROM_THE_SAME_ASOF_T_SNAPSHOT",
        "A_LATER_REVISION_OF_A_HISTORICAL_MONTH_IS_NOT_READ",
        "CURRENT_LEVEL_HAS_NO_EXPIRY_RELATIVE_TO_DECISION_TIME",
    ):
        assert semantics["checks"][name], name
    integrity = audit["source_cadence_integrity"]
    assert integrity["passed"] is True
    for record in integrity["by_series"].values():
        assert record["maximum_observation_gap_days"] <= record["maximum_allowed_gap_days"]
    assert audit["source"]["current_revised_substitution"] is False
    assert audit["source"]["post_2024_vintages"] == 0
    assert audit["source"]["interpolation"] is False
    assert audit["source"]["current_state_expiry_relative_to_decision_time"] is False


def test_the_predecessor_source_block_is_preserved_and_not_reclassified():
    audit = read(AUDIT_PATH)
    assert audit["predecessor_checkpoint"] == "PREDICTIVE-STAGE3-MACRO-VINTAGE-V1"
    assert audit["predecessor_disposition"] == "BLOCKED_MACRO_SOURCE_COVERAGE_V1"
    assert audit["predecessor_reclassified"] is False
    predecessor = read("reports/validation/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1-SOURCE-AUDIT.json")
    assert predecessor["status"] == "BLOCKED_MACRO_SOURCE_COVERAGE_V1"
    assert predecessor["coverage"]["admissible_folds"] == []
    assert predecessor["target_bearing_model_fitted"] is False
    record = admission(ROOT)
    assert set(record["predecessor_record_sha256"]) == set(PREDECESSOR_RECORDS)
    for path, digest in record["predecessor_record_sha256"].items():
        assert content_hash(ROOT / path) == digest, path
    state = read("state/current_state.json")
    assert state["predictive_stage3_macro_vintage"]["status"] == (
        "BLOCKED_MACRO_SOURCE_COVERAGE_V1"
    )
    assert state["predictive_stage3_macro_vintage"]["model_fits"] == 0
    assert state["predictive_stage3_macro_vintage"]["configurations_consumed"] == 0


def test_all_eight_prior_predictive_results_are_unchanged():
    record = admission(ROOT)
    assert set(record["prior_experiment_result_sha256"]) == set(PRIOR_EXPERIMENT_RESULTS)
    assert len(set(record["prior_experiment_result_sha256"].values())) == 8
    for path, digest in record["prior_experiment_result_sha256"].items():
        assert content_hash(ROOT / path) == digest, path


def test_the_plan_preregistrations_and_admission_precede_the_result():
    assert read(SEARCH_PLAN_PATH) == search_plan()
    record = read(ADMISSION_PATH)
    assert record == admission(ROOT)
    assert record["status"] == "PASS" and record["execution_authorized"] is True
    assert record["model_fits_executed"] == record["market_results_observed"] == 0
    assert record["family_configurations_consumed_before_this_run"] == 0
    assert record["source_semantics_versions_consumed"] == 1
    assert record["sealed_queries"] == 0 and record["real_money"] is False
    for model_version in CONFIGURATION_ORDER:
        committed = read(preregistration_path(model_version))
        assert committed == preregistration(model_version, ROOT)
        assert committed["status"] == "PREREGISTERED"
        assert committed["hypothesis_id"] == HYPOTHESIS_IDS[model_version]
        assert committed["model"]["declares_magnitude"] is False
        assert committed["model"]["hyperparameter_search"] is False
        assert committed["model"]["probability_threshold_searched"] is False
        assert committed["advancement_gate"]["sealed_query_authorized_on_pass"] is False
        assert committed["primary_effect"]["minimum_important_effect"] == (MINIMUM_IMPORTANT_EFFECT)
        assert committed["inference"]["seed"] == PAIRED_SEED


def test_the_feature_set_is_v1s_quantities_under_v2_semantics():
    plan = read(SEARCH_PLAN_PATH)
    features = plan["feature_set"]
    assert features["version"] == FEATURE_SET_VERSION
    assert plan["source_semantics"]["supersedes"] == PREDECESSOR_FEATURE_SET_VERSION
    assert features["count"] == FEATURE_COUNT == 13
    assert features["ordered_names"] == list(FEATURE_NAMES)
    assert features["identical_quantities_and_order_to_v1"] is True
    assert plan["source_semantics"]["state_persistence_is_not_interpolation"] is True
    assert plan["source_semantics"]["interpolation_or_backfill"] is False
    assert plan["budget"]["source_semantics_versions_authorized"] == 1
    assert "A_THIRD_MACRO_SOURCE_REDESIGN_IN_GENERATION_V1" in plan["forbidden"]


def test_both_configurations_were_executed_and_scored_as_preregistered():
    result = read(REPORT_JSON_PATH)
    assert result["family"] == FAMILY
    assert result["search_budget"]["configurations_consumed"] == FAMILY_SIZE
    assert result["search_budget"]["configurations_remaining"] == 0
    assert result["search_budget"]["result_dependent_early_stop"] is False
    assert result["search_budget"]["source_semantics_versions_remaining"] == 0
    assert result["family_disposition"]["post_hoc_winner_selected"] is False
    assert result["family_disposition"]["macro_source_design_closed"] is True
    folds = result["folds"]["included_folds"]
    assert len(folds) == len(read(AUDIT_PATH)["coverage"]["admissible_folds"])
    for model_version in CONFIGURATION_ORDER:
        configuration = result["configurations"][model_version]
        assert configuration["experiment_id"] == EXPERIMENT_IDS[model_version]
        assert configuration["model_fits"]["total"] == 2 * len(folds)
        gate = configuration["advancement_gate"]
        assert gate["all_must_hold"] is True
        assert gate["secondary_metric_used_to_rescue"] is False
        assert gate["required_non_negative_folds"] == required_non_negative_folds(len(folds))
        assert read(result_path(model_version)) == configuration_result_document(
            result, model_version
        )
        assert read(trials_path(model_version)) == trials_document(result, model_version)
        assert len(read(trials_path(model_version))) == len(folds)


def test_a_rejected_family_claims_no_sealed_eligibility_or_champion():
    result = read(REPORT_JSON_PATH)
    disposition = result["family_disposition"]
    if not disposition["advancing_configurations"]:
        assert disposition["disposition"] == "REJECTED_DEVELOPMENT_NO_SEALED"
        for value in disposition["sealed_eligibility"].values():
            assert value == NOT_ELIGIBLE
    assert disposition["sealed_queried"] is False
    assert disposition["champion_created"] is False
    assert disposition["prospective_observer_created"] is False
    assert disposition["descendant_tuned"] is False
    assert result["boundaries"]["sealed_queries"] == 0
    assert result["boundaries"]["real_money"] is False
    assert result["boundaries"]["predecessor_reclassified"] is False
    assert result["boundaries"]["third_macro_source_redesign"] is False
    assert result["boundaries"]["coverage_gate_lowered_after_observation"] is False


def test_the_committed_reports_are_generated_from_the_committed_result():
    result = read(REPORT_JSON_PATH)
    assert (ROOT / REPORT_JSON_PATH).read_bytes().replace(b"\r\n", b"\n") == report_bytes(result)
    markdown = ROOT / "reports/research/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1.md"
    assert markdown.read_bytes().replace(b"\r\n", b"\n") == markdown_bytes(result)


def test_the_deterministic_validator_recomputes_every_advancement_gate():
    findings = validate_macro_release_state(ROOT)
    assert findings["status"] == "PASS"
    assert findings["data_replayed"] is False
    assert set(findings["classifications"]) == set(CONFIGURATION_ORDER)


def test_state_records_the_executed_checkpoint():
    state = read("state/current_state.json")
    record = state["predictive_stage3_macro_release_state"]
    result = read(REPORT_JSON_PATH)
    assert state["latest_executor_checkpoint"] == (
        "PREDICTIVE-GENERATION-V2-SELECTIVE-LONG-REBASELINE-V1"
    )
    assert record["status"] == "COMPLETE"
    assert record["admission_identity_sha256"] == admission_identity(ROOT)
    assert record["included_folds"] == result["folds"]["included_folds"]
    assert record["configurations_consumed"] == FAMILY_SIZE
    assert record["source_semantics_versions_consumed"] == 1
    assert record["source_semantics_versions_remaining"] == 0
    assert record["predecessor_checkpoint"] == "PREDICTIVE-STAGE3-MACRO-VINTAGE-V1"
    assert record["predecessor_reclassified"] is False
    assert record["sealed_queries"] == 0
    assert record["champion_status"] == state["champion_status"] == "NONE"
    assert record["real_money"] is False
    assert state["predictive_research_objective"]["predictive_experiments_completed"] == 10
