"""ALIGNED_GATE_INTENSITY_COMMON_EFFECT_V1 design invariants and leakage barriers."""

import hashlib
import json
from pathlib import Path

import pytest
from app.research.cross_section import assert_no_real_effect_leakage
from app.research.gate_intensity import (
    DEVELOPMENT_YEARS,
    EFFECTIVE_ALPHA,
    FAMILY_STATUS_ON_FAILURE,
    GATE_INTENSITY_MESI_BPS_PER_GATE,
    GATE_INTENSITY_VALUES,
    GATE_WEIGHTS,
    LEGAL_SHIFT_WEEKS,
    MAXIMUM_SHIFT_WEEKS,
    MINIMUM_ACCEPTED_VECTORS,
    MINIMUM_ASSET_CLUSTER_RETENTION,
    MINIMUM_ROW_RETENTION,
    MINIMUM_SHIFT_WEEKS,
    NEW_GATE_PARAMETERS,
    PROSPECTIVE_FAMILY_SIZE,
    REQUESTED_REPLICATE_VECTORS,
    TARGET_POWER,
    GateScoreViolation,
    ZeroShiftForbidden,
    aligned_from_intensity,
    build_shift_vectors,
    gate_intensity,
    mesi_bps_per_gate,
    shift_family_digest,
    shift_microseconds,
    validate_shift_weeks,
)

ROOT = Path(__file__).resolve().parents[2]
WEEK_HOURS = 7 * 24


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    content = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


# --- sparse cross-section closure ----------------------------------------------------
def test_sparse_cross_section_true_beta_remains_unavailable() -> None:
    state = read_json("state/current_state.json")
    sparse = state["cross_section_feasibility"]
    assert sparse["zero_alignment_effect_observed"] is False
    assert sparse["material_economic_hypotheses_executed"] == 0
    gate = read_json("reports/power/CROSS-SECTION-POWER-GATE-V1.json")
    assert all(value is False for value in gate["leakage_guard"].values())
    assert gate["ACTUAL_CROSS_SECTION_EFFECT_OBSERVED"] is False


def test_sparse_closure_is_not_a_rejection() -> None:
    sparse = read_json("state/current_state.json")["cross_section_feasibility"]
    assert sparse["sparse_disposition"] == (
        "POWER_BLOCKED_INFERENCE_CALIBRATION_FAILED_NOT_EXECUTED"
    )
    assert sparse["sparse_disposition"] not in {
        "REJECT",
        "NOT_SUPPORTED",
        "INCONCLUSIVE",
        "INCONCLUSIVE_MARKET_EVIDENCE",
    }
    parent = read_json("research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1.json")[
        "parent_disposition"
    ]
    assert parent["is_reject"] is False
    assert parent["is_inconclusive_market_evidence"] is False
    assert parent["is_evidence_beta_not_positive"] is False
    assert parent["same_hypothesis_inference_rescue_authorized"] is False


def test_event_reconciliation_is_exact_and_typed() -> None:
    report = read_json("reports/cross_section/CROSS-SECTION-EVENT-RECONCILIATION-V1.json")
    assert report["support_artifact_signals"] == 3380
    assert report["power_panel_signals"] == 3378
    assert report["signal_difference"] == 2
    assert report["removed_signal_count"] == 2
    assert report["asset_cluster_difference"] == 1
    assert len(report["removed_signal_rows"]) == 2
    assert report["arithmetic_reconciles"] is True
    assert report["every_removed_row_has_typed_reason"] is True
    assert all(item["removal_rule"] for item in report["removed_signal_rows"])
    assert report["removal_rule"]["discretionary"] is False
    assert report["removal_rule"]["performance_dependent"] is False
    # The rule is whole-sample, so the reconciliation fails closed rather than passing.
    assert report["removal_rule"]["point_in_time"] is False
    assert report["EVENT_RECONCILIATION_STATUS"] == (
        "FAIL_CLOSED_NON_POINT_IN_TIME_PARTICIPATION_RULE"
    )
    outcome = report["outcome_availability_reconciliation"]
    assert outcome["outcome_panel_is_strict_subset"] is True
    assert outcome["signals_lost_to_outcome_requirement"] == 0


# --- frozen score --------------------------------------------------------------------
def test_gate_intensity_is_an_unweighted_integer_zero_to_three() -> None:
    assert GATE_WEIGHTS == (1, 1, 1)
    assert NEW_GATE_PARAMETERS == 0
    assert GATE_INTENSITY_VALUES == (0, 1, 2, 3)
    seen = set()
    for direction in (False, True):
        for breakout in (False, True):
            for participation in (False, True):
                score = gate_intensity(direction, breakout, participation)
                assert isinstance(score, int) and score in GATE_INTENSITY_VALUES
                assert score == int(direction) + int(breakout) + int(participation)
                seen.add(score)
    assert seen == {0, 1, 2, 3}


def test_aligned_fires_exactly_when_intensity_is_three() -> None:
    assert aligned_from_intensity(3) is True
    for score in (0, 1, 2):
        assert aligned_from_intensity(score) is False
    report = read_json("reports/cross_section/GATE-INTENSITY-SCORE-V1.json")
    assert report["aligned_equals_intensity_three"] is True
    assert report["intensity_is_integer_0_to_3"] is True
    assert report["aligned_signal_count"] == report["intensity_three_count"] == 3380
    assert set(report["rows_by_intensity"]) == {"0", "1", "2", "3"}
    assert sum(report["rows_by_intensity"].values()) == report["panel_rows"]


def test_no_new_gate_parameter_or_weight_exists() -> None:
    protocol = read_json("research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1.json")
    score = protocol["score"]
    assert score["weights"] == [1, 1, 1]
    assert score["weighted"] is False
    assert score["new_thresholds"] == 0
    assert score["new_gate_parameters"] == 0
    assert score["parameter_fitting"] is False
    assert score["optimization"] is False
    assert score["continuous_rescaling"] is False
    assert score["asset_specific_normalization"] is False
    assert score["aligned_modified"] is False


def test_gate_intensity_guard_rejects_an_out_of_range_score(monkeypatch) -> None:
    from app.research import gate_intensity as module

    monkeypatch.setattr(module, "GATE_INTENSITY_VALUES", (0, 1, 2))
    with pytest.raises(GateScoreViolation):
        module.gate_intensity(True, True, True)


def test_exactly_one_primary_coefficient_and_no_bucket_rescue() -> None:
    protocol = read_json("research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1.json")
    primary = protocol["primary_estimand"]
    assert primary["count"] == 1
    assert primary["coefficient"] == "beta_gate"
    assert primary["fixed_effects"] == ["ASSET", "DECISION_TIME"]
    assert primary["nonlinear_score_model"] is False
    assert primary["per_bucket_coefficients"] is False
    assert primary["gate_interactions"] is False
    assert primary["per_asset_winner_selection"] is False
    assert primary["evaluated_at_true_alignment"] is False
    assert protocol["future_outcome"]["horizon_hours"] == 24


# --- calendar-synchronous randomization ----------------------------------------------
def test_every_legal_shift_is_a_non_zero_whole_week_in_band() -> None:
    assert MINIMUM_SHIFT_WEEKS == 2 and MAXIMUM_SHIFT_WEEKS == 13
    assert 0 not in LEGAL_SHIFT_WEEKS
    assert len(LEGAL_SHIFT_WEEKS) == 2 * (MAXIMUM_SHIFT_WEEKS - MINIMUM_SHIFT_WEEKS + 1)
    for weeks in LEGAL_SHIFT_WEEKS:
        assert MINIMUM_SHIFT_WEEKS <= abs(weeks) <= MAXIMUM_SHIFT_WEEKS
        assert validate_shift_weeks(weeks) == weeks
        assert shift_microseconds(weeks) % (WEEK_HOURS * 3_600_000_000) == 0


def test_zero_and_out_of_band_displacements_are_rejected() -> None:
    for forbidden in (0, 1, -1, 14, -14, 52):
        with pytest.raises(ZeroShiftForbidden):
            validate_shift_weeks(forbidden)
    with pytest.raises(ZeroShiftForbidden):
        shift_microseconds(0)


def test_shift_family_is_unique_deterministic_and_outcome_independent() -> None:
    first = build_shift_vectors(REQUESTED_REPLICATE_VECTORS)
    second = build_shift_vectors(REQUESTED_REPLICATE_VECTORS)
    assert len(first) == REQUESTED_REPLICATE_VECTORS == 1024
    assert [v.weeks_by_year for v in first] == [v.weeks_by_year for v in second]
    assert shift_family_digest(first) == shift_family_digest(second)
    assert len({v.weeks_by_year for v in first}) == len(first)
    for vector in first:
        assert len(vector.weeks_by_year) == len(DEVELOPMENT_YEARS) == 6
        assert all(weeks != 0 for weeks in vector.weeks_by_year)
        assert set(vector.mapping()) == set(DEVELOPMENT_YEARS)
    family = read_json("reports/cross_section/GATE-INTENSITY-RANDOMIZATION-FAMILY-V1.json")
    assert family["family_sha256"] == shift_family_digest(first)
    assert family["derived_from"] == "SEED_AND_CALENDAR_GEOMETRY_ONLY_NEVER_OUTCOMES"
    assert family["zero_shift_present"] is False
    assert family["circular_wrap"] is False
    assert family["all_years_covered"] is True


def test_one_displacement_per_year_is_shared_by_every_asset() -> None:
    protocol = read_json("research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1.json")
    randomization = protocol["randomization"]
    assert randomization["one_common_signed_displacement_per_year"] is True
    assert randomization["shared_by_all_assets_within_year"] is True
    assert randomization["preserves_cross_asset_synchrony"] is True
    assert randomization["preserves_hour_of_week_structure"] is True
    assert randomization["preserves_year_regime_membership"] is True
    assert randomization["preserves_asset_identity"] is True
    assert randomization["unit"] == "WHOLE_UTC_WEEK"
    assert randomization["circular_wrap"] is False
    assert randomization["requires_eligibility_at_source_and_destination"] is True
    # A single displacement per year means every asset moves by the same calendar amount.
    for vector in build_shift_vectors(8):
        assert len(set(vector.mapping().values()) | set(vector.weeks_by_year)) == len(
            set(vector.weeks_by_year)
        )


def test_retired_placebo_is_not_reused() -> None:
    protocol = read_json("research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1.json")
    retired = protocol["retired_placebo"]
    assert retired["reused_as_primary_randomization"] is False
    assert retired["participation_rule_reintroduced"] is False
    assert retired["retired_for_inference"] is True
    assert "CROSS_ASSET_SYNCHRONY_NOT_PRESERVED" in retired["reasons"]


# --- support, inference, threshold, power --------------------------------------------
def test_support_thresholds_were_fixed_before_power() -> None:
    assert MINIMUM_ROW_RETENTION == 0.70
    assert MINIMUM_ASSET_CLUSTER_RETENTION == 0.80
    assert MINIMUM_ACCEPTED_VECTORS == 512
    support = read_json("research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1.json")["support_gate"]
    assert support["thresholds_fixed_before_power"] is True
    assert support["inspects_performance"] is False
    assert support["loosening_allowed"] is False
    assert support["second_shift_family_allowed"] is False
    assert support["required_year_coverage"] == len(DEVELOPMENT_YEARS) == 6


def test_empirical_randomization_governs_future_inference() -> None:
    inference = read_json("research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1.json")["inference"]
    assert inference["primary"] == "EMPIRICAL_RANDOMIZATION"
    assert inference["analytic_cluster_role"] == ("DIAGNOSTIC_ONLY_NEVER_OVERRIDES_RANDOMIZATION")
    assert inference["zero_shift_beta_computed"] is False
    assert inference["critical_value_rule"] == "CONSERVATIVE_EMPIRICAL_ORDER_STATISTIC"
    assert inference["prospective_family_size"] == PROSPECTIVE_FAMILY_SIZE == 13
    assert inference["effective_alpha"] == pytest.approx(0.05 / 13)
    assert inference["sidedness"] == "ONE_SIDED_POSITIVE"


def test_threshold_and_power_target_are_frozen() -> None:
    assert mesi_bps_per_gate() == GATE_INTENSITY_MESI_BPS_PER_GATE == 8.0
    assert GATE_INTENSITY_MESI_BPS_PER_GATE * 3 == 24.0
    assert EFFECTIVE_ALPHA == pytest.approx(0.05 / 13)
    assert TARGET_POWER == 0.80
    threshold = read_json("research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1.json")[
        "economic_threshold"
    ]
    assert threshold["GATE_INTENSITY_MESI_BPS_PER_GATE"] == 8.0
    assert threshold["lowered_after_power"] is False
    assert threshold["claims_product_return"] is False


def test_zero_shift_beta_is_structurally_inaccessible() -> None:
    gate = read_json("reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1.json")
    assert gate["leakage_guard"]["gate_intensity_zero_shift_beta_computed"] is False
    assert gate["leakage_guard"]["sparse_zero_alignment_beta_computed"] is False
    assert gate["leakage_guard"]["real_t_computed"] is False
    assert gate["leakage_guard"]["real_p_computed"] is False
    assert gate["leakage_guard"]["per_asset_real_effect_computed"] is False
    assert gate["leakage_guard"]["trading_verdict_emitted"] is False
    assert gate["power"]["computed"] is False
    assert gate["power"]["power_at_8_bps_per_gate"] is None
    for relative in (
        "reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1.json",
        "reports/cross_section/GATE-INTENSITY-SCORE-V1.json",
        "reports/cross_section/GATE-INTENSITY-RANDOMIZATION-FAMILY-V1.json",
        "reports/cross_section/CROSS-SECTION-EVENT-RECONCILIATION-V1.json",
    ):
        payload = read_json(relative)
        assert_no_real_effect_leakage(payload)
        assert payload["ACTUAL_CROSS_SECTION_EFFECT_OBSERVED"] is False


def test_gate_failure_parks_further_aligned_descendants() -> None:
    gate = read_json("reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1_1.json")
    record = read_json("state/current_state.json")["gate_intensity_descendant"]
    assert FAMILY_STATUS_ON_FAILURE == "PARKED_DEVELOPMENT_SEARCH_EXHAUSTED"
    if gate["GATE_INTENSITY_POWER_GATE_STATUS"] != "READY_FOR_PREREGISTRATION":
        assert gate["ALIGNED_DEVELOPMENT_FAMILY_STATUS"] == FAMILY_STATUS_ON_FAILURE
        assert record["aligned_development_family_status"] == FAMILY_STATUS_ON_FAILURE
        assert gate["preregistration_authorized"] is False
        assert record["preregistration_authorized"] is False
    assert record["final_authorized_descendant"] is True


def test_v1_1_causal_panel_uses_only_point_in_time_eligibility_and_outcome_resolution() -> None:
    report = read_json(
        "reports/cross_section/CROSS-SECTION-GATE-INTENSITY-PANEL-RECONCILIATION-V1_1.json"
    )
    rule = report["causal_inclusion_rule"]
    assert rule["point_in_time_universe_eligibility"] is True
    assert rule["gate_intensity_computable_at_decision_time"] is True
    assert rule["frozen_24h_outcome_resolvable"] is True
    assert rule["minimum_whole_epoch_lifetime"] is None
    assert rule["retired_504_row_filter_used"] is False
    assert rule["future_epoch_length_used"] is False
    assert rule["future_delisting_date_used"] is False
    assert rule["future_eligible_row_count_used"] is False
    assert rule["future_signal_count_used"] is False
    assert rule["future_survival_required"] is False
    assert report["base_rows"] == 2_556_535
    assert report["analysis_rows"] == 2_556_366
    assert report["removed_rows"] == 169
    assert report["base_epochs"] == report["analysis_epochs"] == 390
    assert report["base_intensity_3_events"] == report["analysis_intensity_3_events"] == 3380
    assert report["events_removed"] == 0
    assert report["clusters_removed"] == []
    assert report["every_removed_row_has_typed_reason"] is True
    assert report["all_removals_are_frozen_outcome_contract_only"] is True
    assert len(report["removed_row_detail"]) == report["removed_rows"]
    assert all(item["removal_reason"] for item in report["removed_row_detail"])
    assert all(
        item["reason_type"] == "FROZEN_24H_OUTCOME_RESOLUTION"
        for item in report["removed_row_detail"]
    )
    assert report["EVENT_RECONCILIATION_STATUS"] == "PASS"


def test_retired_sparse_artifacts_and_3380_to_3378_history_are_immutable() -> None:
    expected = {
        "reports/cross_section/CROSS-SECTION-EVENT-RECONCILIATION-V1.json": (
            "cb81cd4f53cd1a3fb2de022492b647172693be462236de878e744264728e28c1"
        ),
        "reports/cross_section/CROSS-SECTION-PLACEBO-CALIBRATION-V1.json": (
            "2173590eae9b289d220cdd772bdb558c42516f5ff23115103d7b08d0aafd6383"
        ),
        "reports/power/CROSS-SECTION-POWER-GATE-V1.json": (
            "52487ac2b35fe8b6905b41e0c88f77326dce47b35040ee0bef22b345bbd39b71"
        ),
    }
    assert {path: sha256(path) for path in expected} == expected
    legacy = read_json("reports/cross_section/CROSS-SECTION-EVENT-RECONCILIATION-V1.json")
    assert legacy["support_artifact_signals"] == 3380
    assert legacy["power_panel_signals"] == 3378
    assert legacy["removed_signal_count"] == 2


def test_frozen_family_was_not_regenerated_and_support_gate_is_terminal() -> None:
    support = read_json("reports/cross_section/GATE-INTENSITY-RANDOMIZATION-SUPPORT-V1_1.json")
    assert support["source_family_artifact_sha256"] == (
        "4c94c99248ca759c0843824107b9c4c4b6743b1c0aa4e47f02b7c0348b9f4592"
    )
    assert support["family_sha256"] == (
        "7e135af46a20c30d8c1f19e39d56b663254ab293b007c84a694437e82e8cf12d"
    )
    assert support["vectors_regenerated"] is False
    assert support["thresholds"] == {
        "minimum_row_retention": 0.7,
        "minimum_asset_cluster_retention": 0.8,
        "required_year_coverage": 6,
        "minimum_accepted_vectors": 512,
    }
    assert support["accepted_vectors"] == 0
    assert support["requested_vectors"] == 1024
    assert support["retention_distributions"]["row_retention"]["maximum"] < 0.7
    assert support["retention_distributions"]["years_represented"] == {
        key: 6.0 for key in ("minimum", "p05", "p25", "median", "p75", "p95", "maximum")
    }
    assert support["RANDOMIZATION_SUPPORT_STATUS"] == "REDESIGN_REQUIRED"


def test_v1_1_stopped_before_any_beta_or_power_and_permanently_parked() -> None:
    protocol = read_json("research/protocols/ALIGNED-GATE-INTENSITY-POWER-V1_1.json")
    gate = read_json("reports/power/ALIGNED-GATE-INTENSITY-POWER-GATE-V1_1.json")
    assert protocol["hypothesis_id"] == "ALIGNED_GATE_INTENSITY_COMMON_EFFECT_V1"
    assert protocol["material_economic_hypothesis_changed"] is False
    assert protocol["material_economic_hypotheses_executed"] == 0
    assert protocol["power"]["synthetic_slopes_bps_per_gate"] == [0.0, 4.0, 8.0, 16.0, 32.0]
    assert protocol["power"]["zero_shift_forbidden"] is True
    assert protocol["power"]["zero_alignment_beta_computed"] is False
    assert protocol["power"]["shifted_betas_computed"] is False
    assert protocol["power"]["synthetic_power_computed"] is False
    assert gate["power"]["computed"] is False
    assert gate["power"]["empirical_null_sd_bps_per_gate"] is None
    assert gate["power"]["critical_beta_bps_per_gate"] is None
    assert gate["power"]["minimum_detectable_effect_bps_per_gate"] is None
    assert gate["power"]["power_at_8_bps_per_gate"] is None
    assert gate["prerequisite_gates"]["RANDOMIZATION_INFERENCE_STATUS"] == "NOT_RUN_BLOCKED"
    assert gate["GATE_INTENSITY_POWER_GATE_STATUS"] == "REDESIGN_REQUIRED"
    assert gate["ALIGNED_DEVELOPMENT_FAMILY_STATUS"] == ("PARKED_DEVELOPMENT_SEARCH_EXHAUSTED")
    assert all(value is False for value in gate["leakage_guard"].values())


# --- product and accounting ----------------------------------------------------------
def test_product_and_accounting_are_unchanged() -> None:
    state = read_json("state/current_state.json")
    record = state["gate_intensity_descendant"]
    assert record["product_universe"] == "BTCUSDT_SPOT_V1_UNCHANGED"
    assert record["multi_asset_trading_implemented"] is False
    assert record["material_economic_hypotheses_executed"] == 0
    assert state["symbols"] == ["BTCUSDT"]
    assert state["experiments_completed"] == 26
    assert state["statistical_governance"]["known_discovery_family_size"] == 12
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["adaptive_search"]["sealed_queries"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False
    assert state["paper_trading"]["real_money"] is False


def test_the_descendant_consumed_one_adaptive_decision_and_fork() -> None:
    state = read_json("state/current_state.json")
    # Includes the later ADR-0033 public taker-flow direction (+1 decision, +1 fork).
    assert state["adaptive_search"]["adaptive_decisions"] == 16 + 1
    assert state["adaptive_search"]["result_dependent_forks"] == 13 + 1
    direction = read_json(
        "research/memory/registry/directions/ALIGNED-GATE-INTENSITY-DESCENDANT.json"
    )
    assert direction["adaptive_decision_increment"] == 1
    assert direction["result_dependent_fork_increment"] == 1
    assert direction["material_economic_hypotheses_executed"] == 0
    assert direction["market_outcomes_observed"] is False
    assert direction["sealed_queries"] == 0
