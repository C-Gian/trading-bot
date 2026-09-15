from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from app.research.statistical_governance import (
    BLOCKED_NEVER_OBSERVED,
    CONFIGURATION,
    COST_OR_DELAY_PROFILE,
    MATCHED_CONTROL,
    MATERIAL_ECONOMIC_HYPOTHESIS,
    REPRODUCTION,
    WALK_FORWARD_FIT,
    StatisticalGovernanceError,
    build_aligned_provenance_audit,
    build_material_hypothesis_ledger,
    build_repository_ledger,
    compute_mde,
    holm_bonferroni,
    normalize_provenance_entry,
    reconstruct_statistical_evidence,
)

ROOT = Path(__file__).resolve().parents[2]


def _records() -> list[dict[str, str]]:
    return [
        {
            "experiment_id": "PRIMARY",
            "hypothesis_id": "HYPOTHESIS",
            "hypothesis_role": "ECONOMIC_CORE",
        },
        {
            "experiment_id": "ABLATION",
            "hypothesis_id": "HYPOTHESIS",
            "hypothesis_role": "STRUCTURAL_ABLATION",
        },
        {
            "experiment_id": "CONTROL",
            "hypothesis_id": "HYPOTHESIS",
            "hypothesis_role": "MATCHED_KNOWN_CONTROL",
        },
        {
            "experiment_id": "BLOCKED",
            "hypothesis_id": "BLOCKED_HYPOTHESIS",
            "hypothesis_role": "ECONOMIC_CORE",
        },
    ]


def _ledger(records: list[dict[str, str]]) -> dict:
    return build_material_hypothesis_ledger(
        records,
        observed_experiment_ids={"PRIMARY", "ABLATION", "CONTROL"},
        blocked_hypothesis_ids={"BLOCKED_HYPOTHESIS"},
        profile_evaluations_observed=4,
        walk_forward_fits_observed=5,
        reproduction_count=1,
        registered_configuration_count=4,
        registered_profile_count=8,
        registered_fit_count=10,
        unquantified_pre_repo_exposure=True,
    )


def test_profiles_controls_fits_reproductions_and_blocked_are_not_discoveries() -> None:
    ledger = _ledger(_records())
    assert ledger["known_discovery_family"] == ["HYPOTHESIS"]
    assert ledger["counts"] == {
        BLOCKED_NEVER_OBSERVED: 1,
        CONFIGURATION: 4,
        COST_OR_DELAY_PROFILE: 4,
        MATCHED_CONTROL: 1,
        MATERIAL_ECONOMIC_HYPOTHESIS: 1,
        REPRODUCTION: 1,
        WALK_FORWARD_FIT: 5,
    }
    assert all(
        not event["discovery_family_member"]
        for event in ledger["events"]
        if event["classification"] != MATERIAL_ECONOMIC_HYPOTHESIS
    )


def test_ledger_is_deterministic_under_input_ordering() -> None:
    forward = _ledger(_records())
    backward = _ledger(list(reversed(_records())))
    assert forward == backward
    assert forward["events_sha256"] == backward["events_sha256"]


def test_repository_ledger_excludes_wp016_and_counts_wp017_once() -> None:
    ledger = build_repository_ledger(ROOT)
    assert ledger["known_family_size"] == 12
    assert ledger["registered_material_hypothesis_count"] == 13
    assert (
        ledger["known_discovery_family"].count(
            "CFTC_LEVERAGED_FUNDS_NET_POSITIONING_ADDS_INFORMATION_V1"
        )
        == 1
    )
    assert "WIKIPEDIA_ATTENTION_SHOCK_ADDS_INFORMATION_V1" not in ledger["known_discovery_family"]
    assert ledger["unquantified_pre_repo_exposure"] is True
    assert ledger["known_count_is_lower_bound"] is True
    assert ledger["missing_historical_trials_estimated"] is False


def test_holm_matches_synthetic_example_and_is_order_invariant() -> None:
    expected = {"a": 0.03, "b": 0.06, "c": 0.06}
    assert holm_bonferroni({"a": 0.01, "b": 0.04, "c": 0.03}) == expected
    assert holm_bonferroni({"c": 0.03, "a": 0.01, "b": 0.04}) == expected
    ordered = sorted(zip((0.01, 0.03, 0.04), (0.03, 0.06, 0.06), strict=True))
    assert all(0 <= adjusted <= 1 for _, adjusted in ordered)
    assert [adjusted for _, adjusted in ordered] == sorted(adjusted for _, adjusted in ordered)


def test_all_required_aligned_constants_have_fail_closed_provenance() -> None:
    audit = build_aligned_provenance_audit()
    assert len(audit["parameters"]) == 8
    assert {item["parameter_id"] for item in audit["parameters"]} == {
        "ALIGNED_BREAKOUT_LOOKBACK",
        "ALIGNED_CONTEXT_LENGTH",
        "ALIGNED_PERSISTENCE_THRESHOLD",
        "ALIGNED_VOLUME_REFERENCE_LOOKBACK",
        "ALIGNED_PARTICIPATION_THRESHOLD",
        "ALIGNED_STOP",
        "ALIGNED_TARGET",
        "ALIGNED_EXPIRY",
    }
    unsupported = normalize_provenance_entry(
        {"parameter_id": "UNSUPPORTED", "provenance_status": "INHERITED", "evidence": []}
    )
    assert unsupported["provenance_status"] == "UNKNOWN_PROVENANCE"
    assert unsupported["known_before_relevant_result_exposure"] is None


def test_machine_reconstruction_matches_aligned_governed_values() -> None:
    audit = reconstruct_statistical_evidence(ROOT)
    aligned = next(
        row
        for row in audit["statistics"]
        if row["hypothesis_id"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    )
    assert aligned["raw_trade_count"] == 125
    assert aligned["mean_net_R"] == pytest.approx(0.1373934676, abs=1e-10)
    assert aligned["governed_effective_sample_size"] == pytest.approx(116.35, abs=0.01)
    assert aligned["naive_test_statistic"] is not None
    assert aligned["unadjusted_p_value"] is not None
    assert aligned["holm_adjusted_p_value"] is not None
    assert aligned["dependence_adjusted_statistic"] is None


def test_missing_raw_evidence_never_uses_win_loss_averages_as_exact_data() -> None:
    audit = reconstruct_statistical_evidence(ROOT)
    funding = next(
        row
        for row in audit["statistics"]
        if row["hypothesis_id"] == "SETTLED_FUNDING_ADDS_POSITIONING_INFORMATION_V1"
    )
    assert funding["mean_net_R"] == -0.0814500414
    assert funding["sample_standard_deviation"] is None
    assert funding["naive_test_statistic"] is None
    assert funding["statistical_status"] == "EXACT_STATISTIC_UNAVAILABLE"
    assert funding["unavailable_reason"] == (
        "RAW_TRADE_OUTCOMES_NOT_PRESERVED_IN_GOVERNED_RESULT_ARTIFACT"
    )


def test_mde_behaves_monotonically_and_fails_closed() -> None:
    base = {
        "sample_standard_deviation": 1.0,
        "effective_sample_size": 100.0,
        "alpha": 0.05,
        "power_target": 0.80,
        "directional": True,
        "dependence_method": "GOVERNED_POSITIVE_ACF_LAGS_1_TO_5_ESS_DIAGNOSTIC",
    }

    def calculate(**overrides: Any) -> float:
        parameters = {**base, **overrides}
        return compute_mde(
            sample_standard_deviation=float(parameters["sample_standard_deviation"]),
            effective_sample_size=float(parameters["effective_sample_size"]),
            alpha=float(parameters["alpha"]),
            power_target=float(parameters["power_target"]),
            directional=bool(parameters["directional"]),
            dependence_method=str(parameters["dependence_method"]),
        )

    value = calculate()
    assert value == pytest.approx(0.248648, abs=1e-6)
    assert calculate(effective_sample_size=50.0) > value
    assert calculate(sample_standard_deviation=2.0) > value
    assert calculate(alpha=0.01) > value
    assert calculate(power_target=0.90) > value
    with pytest.raises(StatisticalGovernanceError, match="dependence basis"):
        calculate(dependence_method="INVENTED")
    with pytest.raises(StatisticalGovernanceError, match="valid domain"):
        calculate(sample_standard_deviation=0.0)


def test_detectability_adds_no_mesi_and_changes_no_historical_verdict() -> None:
    audit = reconstruct_statistical_evidence(ROOT)
    assert audit["historical_mesi_invented"] is False
    assert audit["historical_classifications_changed"] is False
    assert all(item["historical_mesi"] is None for item in audit["detectability"])
    assert all(
        item["economic_power_interpretation"] == "ECONOMIC_POWER_INTERPRETATION_UNAVAILABLE"
        for item in audit["detectability"]
    )
    result = json.loads(
        (ROOT / "research/experiments/EXP-ALG-009-ALIGNED/result.json").read_text(encoding="utf-8")
    )
    aligned = next(
        item
        for item in audit["detectability"]
        if item["hypothesis_id"] == "ALIGNED_PARTICIPATION_CONTINUATION_V1"
    )
    assert (
        aligned["terminal_historical_classification"]
        == result["secondary_results"]["terminal_classification"]
    )


def test_safety_state_remains_closed() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["real_money_authorized"] is False
    assert state["attention_context_challenger"]["market_results_observed"] is False
    assert state["research_runtime"]["wp016_status"] == "BLOCKED_BEFORE_EXECUTION"
