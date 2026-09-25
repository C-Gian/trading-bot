"""The Owner-authorized prediction-first rebaseline, and the observer it suspends.

These tests guard governance, not a result. Nothing here trains, fits or scores anything.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from app.main import create_app
from app.predictive.taker_flow_validation import expected_state_pointers
from app.product.shadow_observer import (
    AUTOMATIC_COLLECTION_ENABLED,
    AUTOMATIC_COLLECTION_STATUS,
    EVIDENCE_STORE_PATH,
    FINAL_DISPOSITION_PATH,
    HEALTH_STORE_PATH,
    PRESERVED_EVIDENCE_PATH,
)

ROOT = Path(__file__).resolve().parents[2]
STATE = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
DISPOSITION = json.loads((ROOT / FINAL_DISPOSITION_PATH).read_text(encoding="utf-8"))


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


# --- Constitution Version 2.0 ------------------------------------------------------


def test_constitution_preserves_version_2_and_version_1_verbatim() -> None:
    # Version 3.0 (ADR-0036) superseded Version 2.0 and keeps it verbatim as Appendix B;
    # Version 4.0 (ADR-0043/ADR-0044) supersedes 3.0 and keeps it verbatim as Appendix C.
    constitution = _text("governance/SCIENTIFIC_CONSTITUTION.md")
    assert constitution.startswith(
        "# Trading Bot — Scientific Constitution\n\n"
        "Version 4.0 — professional multi-signal paper system\n"
    )
    assert "## Appendix C — superseded Version 3.0, preserved verbatim" in constitution
    assert "\nVersion 3.0 — practical economic usefulness\n" in constitution
    assert "## Appendix B — superseded Version 2.0, preserved verbatim" in constitution
    assert "\nVersion 2.0 — prediction-first\n" in constitution
    seeded = subprocess.check_output(
        ["git", "show", "c6c526124945aa1624118bd7ee6aef9ae5c011b2:SCIENTIFIC_CONSTITUTION.md"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).replace("\r\n", "\n")
    assert seeded.rstrip() in constitution
    assert "## Appendix A — superseded Version 1.0, preserved verbatim" in constitution


def test_constitution_carries_every_version_1_rigour_rule_forward() -> None:
    body = _text("governance/SCIENTIFIC_CONSTITUTION.md").split("## Appendix A")[0]
    for rule in (
        "Every material experiment is preregistered before execution.",
        "Failed and negative experiments are preserved.",
        "Results are never rewritten after observation.",
        "Signals and features use only information available at signal time.",
        "Sealed holdout data is inaccessible to research agents.",
        "Standard random K-fold is forbidden for overlapping financial time-series labels.",
        "Trial count and adaptive search must be recorded for multiple-testing analysis.",
        "Paper success is not permission for live capital.",
        "## Selection/evaluation separation",
        "## Future power gate",
    ):
        assert rule in body, rule


def test_the_only_material_rule_replacement_is_the_hit_rate_rule() -> None:
    body = _text("governance/SCIENTIFIC_CONSTITUTION.md").split("## Appendix A")[0]
    assert "Hit rate is secondary to robust net expectancy" not in body
    assert "Directional win rate is a primary human-facing predictive metric." in body
    assert "It must never be interpreted alone." in body


# --- the declared objective --------------------------------------------------------


def test_state_declares_one_prediction_first_objective() -> None:
    objective = STATE["predictive_research_objective"]
    assert STATE["project_phase"] == "PREDICTIVE_RESEARCH"
    assert STATE["primary_research_phase"] == "PREDICTIVE_MODELLING"
    assert objective["authorized_by"] == "OWNER"
    assert objective["constitution_version"] == "2.0"
    assert objective["research_generation"] == "PREDICTIVE_RESEARCH_GENERATION_V1"
    assert objective["prediction_target"] == "r_24h = log(close[t+24h] / close[t])"
    assert objective["primary_horizon"] == "24h"
    assert objective["decision_cadence"] == "1h"
    assert objective["canonical_resolution"] == "1m"


def test_the_objective_matches_the_committed_predictive_experiments() -> None:
    """Whether a predictor exists is a fact about the records, not a claim state may make."""
    objective = STATE["predictive_research_objective"]
    executed = sorted(
        path.parent.name
        for path in (ROOT / "research/experiments").glob("EXP-PRED-*/result.json")
        if not path.parent.name.startswith("EXP-PRED-V2-")
    )
    assert objective["predictor_trained"] is bool(executed)
    assert objective["predictive_results_observed"] is bool(executed)
    assert objective["predictive_experiments_completed"] == len(executed)
    # No win-rate target is declared before evidence establishes what is feasible, and the
    # first observed result did not create one.
    assert objective["win_rate_target_declared"] is False
    # The superseded generation's count is frozen and never absorbs a predictive experiment.
    assert STATE["experiments_completed"] == 26
    assert STATE["champion_status"] == "NONE"
    assert STATE["real_money_authorized"] is False
    assert STATE["sealed_evaluation"]["consumed_btc_queries"] == 0


def test_probability_and_strength_are_distinct_quantities() -> None:
    objective = STATE["predictive_research_objective"]
    assert objective["strength_is_probability"] is False
    assert "PERCENTILE_RANK" in objective["strength_definition"]
    assert "TRAINING_ONLY" in objective["strength_definition"]
    assert objective["probability_definition"].startswith("CALIBRATED_PROBABILITY")


def test_the_primary_metric_is_never_reported_alone() -> None:
    objective = STATE["predictive_research_objective"]
    assert objective["primary_metric"] == "ACTIONABLE_DIRECTIONAL_WIN_RATE"
    assert objective["primary_metric_reported_alone"] is False
    assert set(objective["mandatory_companion_metrics"]) == {
        "PREDICTION_COVERAGE",
        "SAMPLE_SIZE_AND_CHRONOLOGICAL_DISTRIBUTION",
        "CALIBRATION_BRIER_AND_RELIABILITY_TABLE",
        "MAGNITUDE_MAE_SIGNED_24H_RETURN",
        "SIGNED_MAGNITUDE_MATCH_DIAGNOSTIC",
        "DIRECTIONAL_BASELINE_COMPARISON",
        "DEPENDENCE_AWARE_WIN_RATE_UNCERTAINTY_INTERVAL",
        "PERFORMANCE_BY_CHRONOLOGICAL_FOLD",
    }
    assert objective["required_baselines"] == [
        "TRAINING_UP_BASE_RATE",
        "ALWAYS_UP",
        "PREVIOUS_24H_SIGN_PERSISTENCE",
        "ZERO_RETURN_MAGNITUDE",
    ]


def test_economics_are_downstream_and_reference_capital_is_display_only() -> None:
    economic = STATE["predictive_research_objective"]["economic_layer"]
    assert economic["separation"] == (
        "PREDICTION -> DECISION_POLICY -> ECONOMIC_EXECUTION_SIMULATION"
    )
    assert economic["costs_in_primary_prediction_scoring"] is False
    assert economic["costs_mandatory_for_economic_claims"] is True
    assert economic["prediction_quality_depends_on_economics"] is False
    assert economic["reference_capital_role"] == "DISPLAY_SCENARIO_ASSUMPTION_ONLY"
    assert economic["reference_capital_eur"] == 5000


# --- the signed magnitude-match diagnostic -----------------------------------------


def _magnitude_match(predicted: float, actual: float, eps: float = 1e-4) -> float:
    """The frozen formula, implemented here only to prove its declared properties."""
    low, high = sorted((max(abs(predicted), eps), max(abs(actual), eps)))
    agreement = 1 if (predicted > 0) == (actual > 0) else -1
    return 100 * agreement * low / high


@pytest.mark.parametrize(
    ("predicted", "actual", "expected"),
    [
        (0.02, 0.02, 100.0),
        (-0.02, -0.02, 100.0),
        (0.002, 0.02, 10.0),
        (0.02, 0.002, 10.0),
        (-0.002, 0.02, -10.0),
        (0.02, -0.02, -100.0),
    ],
)
def test_magnitude_match_matches_its_declared_properties(
    predicted: float, actual: float, expected: float
) -> None:
    assert _magnitude_match(predicted, actual) == pytest.approx(expected)


def test_magnitude_match_is_symmetric_and_bounded() -> None:
    for predicted, actual in ((0.01, 0.037), (0.004, 0.0009), (-0.05, -0.2)):
        assert _magnitude_match(predicted, actual) == pytest.approx(
            _magnitude_match(actual, predicted)
        )
        assert -100.0 <= _magnitude_match(predicted, actual) <= 100.0


def test_the_declared_diagnostic_record_matches_the_implemented_properties() -> None:
    diagnostic = STATE["predictive_research_objective"]["magnitude_match_diagnostic"]
    assert diagnostic["range"] == [-100, 100]
    assert diagnostic["symmetric"] is True
    assert "floored at 1e-4" in diagnostic["formula"]
    assert "EXCLUDED_AND_COUNTED" in diagnostic["near_zero_rule"]


# --- the superseded generation -----------------------------------------------------


def test_the_superseded_generation_is_preserved_not_rewritten() -> None:
    legacy = STATE["legacy_research_generation"]
    assert legacy["name"] == "COST_EXPECTANCY_RESEARCH_GENERATION_V1"
    assert legacy["disposition"] == "SUPERSEDED_BY_OWNER_PREDICTION_FIRST_OBJECTIVE"
    assert legacy["results_rewritten"] is False
    assert legacy["negative_results_preserved"] is True
    assert legacy["aligned_historical_results_changed"] is False
    assert legacy["aligned_role"] == "HISTORICAL_PAPER_BASELINE_NOT_CHAMPION"
    assert legacy["transfers_as_predictive_evidence"] is False
    assert legacy["experiments_preserved"] == STATE["experiments_completed"] == 26
    assert legacy["champion_status"] == "NONE"
    results = [
        path
        for path in (ROOT / "research/experiments").glob("*/result.json")
        if not path.parent.name.startswith(("EXP-PRED-", "CANDIDATE-"))
    ]
    assert len(results) == 26


def test_the_archived_pre_pivot_head_is_an_ancestor_of_this_branch() -> None:
    legacy = STATE["legacy_research_generation"]
    assert legacy["archive_branch"] == "archive/cost-expectancy-v1"
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", legacy["archive_head"], "HEAD"],
        cwd=ROOT,
        check=True,
    )


# --- the suspended prospective observer --------------------------------------------


def test_main_constructs_no_observer_so_collection_cannot_restart_by_itself() -> None:
    assert AUTOMATIC_COLLECTION_ENABLED is False
    assert AUTOMATIC_COLLECTION_STATUS == "SUSPENDED_BY_OWNER_OBJECTIVE_PIVOT"
    source = _text("backend/app/main.py")
    assert "default_observer() if AUTOMATIC_COLLECTION_ENABLED else None" in source
    from app.main import app

    with_no_observer = create_app()
    for application in (app, with_no_observer):
        paths = {str(getattr(route, "path", "")) for route in application.routes}
        assert "/api/v1/product/prospective-observer" in paths


def test_the_suspended_surface_reports_the_suspension_and_no_counts() -> None:
    from fastapi.testclient import TestClient

    with TestClient(create_app()) as client:
        payload = client.get("/api/v1/product/prospective-observer").json()
    assert payload["automatic_collection"] == "SUSPENDED_BY_OWNER_OBJECTIVE_PIVOT"
    assert payload["status"] == "STOPPED"
    assert payload["real_money"] is False
    assert payload["order_placement"] is False and payload["credentials"] is False


def test_the_observer_implementation_is_suspended_not_deleted() -> None:
    record = STATE["prospective_observer_suspension"]
    assert record["implementation_deleted"] is False
    assert record["runtime_store_deleted"] is False
    for preserved in (
        "backend/app/product/shadow_observer.py",
        "backend/app/product/observer_lease.py",
        "backend/app/product/provenance.py",
        "docs/contracts/FUTURE_SHADOW_PAPER_EVIDENCE_V1_1.md",
    ):
        assert (ROOT / preserved).is_file(), preserved


def test_the_genuine_evidence_is_preserved_verbatim_and_never_backfilled() -> None:
    record = STATE["prospective_observer_suspension"]
    assert record["evidence_backfilled"] is False
    assert record["evidence_rewritten"] is False
    assert record["preserved_evidence"] == PRESERVED_EVIDENCE_PATH
    preserved = json.loads((ROOT / PRESERVED_EVIDENCE_PATH).read_text(encoding="utf-8"))
    assert preserved["version"] == record["evidence_version"]
    assert len(preserved["decisions"]) == record["decision_records"] == 3
    assert len(preserved["audit_chain"]) == record["audit_chain_events"] == 4
    assert preserved["trades"] == []
    statuses = [item["status"] for item in preserved["decisions"]]
    assert statuses.count("OBSERVED_PROSPECTIVE_DECISION") == record["observed_decisions"] == 1
    assert statuses.count("MISSED_PROSPECTIVE_DECISION") == record["missed_decisions"] == 2
    observed = [
        item for item in preserved["decisions"] if item["status"] == "OBSERVED_PROSPECTIVE_DECISION"
    ]
    assert [item["decision"] for item in observed] == ["NO_TRADE"]
    assert observed[0]["decision_boundary"] == "2026-09-16T15:00:00Z"


def test_one_no_trade_observation_supports_no_scientific_conclusion() -> None:
    record = STATE["prospective_observer_suspension"]
    assert record["review_boundary_reached"] is False
    assert record["scientific_conclusion"] == "INSUFFICIENT_PROSPECTIVE_EVIDENCE_NO_CONCLUSION"
    assert record["shadow_trades_completed"] == record["shadow_trades_open"] == 0
    assert record["raw_prospective_long_signals"] == 0
    assert record["champion_status"] == "NONE" and record["real_money"] is False
    assert STATE["forward_evidence"] == "NONE"


def test_the_recorded_disposition_is_derived_from_the_preserved_evidence() -> None:
    subprocess.run(
        [sys.executable, "scripts/finalize_prospective_observer.py", "--check"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    record = STATE["prospective_observer_suspension"]
    for field in (
        "decision_records",
        "genuine_observations",
        "observed_decisions",
        "missed_decisions",
        "observed_decision_outcomes",
        "audit_chain_events",
        "audit_chain_integrity",
        "scientific_conclusion",
    ):
        assert record[field] == DISPOSITION[field], field


def test_runtime_stores_stay_untracked_while_preserved_copies_are_tracked() -> None:
    def tracked(relative: str) -> bool:
        return bool(
            subprocess.check_output(
                ["git", "ls-files", relative], cwd=ROOT, text=True, encoding="utf-8"
            ).strip()
        )

    assert not tracked(EVIDENCE_STORE_PATH)
    assert not tracked(HEALTH_STORE_PATH)
    assert tracked(PRESERVED_EVIDENCE_PATH)
    assert tracked(FINAL_DISPOSITION_PATH)


# --- the canonical contracts -------------------------------------------------------


def test_the_evaluation_contract_freezes_what_it_must_before_any_result() -> None:
    contract = _text(STATE["predictive_research_objective"]["evaluation_contract"])
    for required in (
        "win_rate = correct_directional_predictions / actionable_directional_predictions",
        "coverage = actionable_directional_predictions / eligible_decision_timestamps",
        "Brier score",
        "moving-block bootstrap",
        "NEAR_ZERO_BOTH",
        "NEUTRAL_REALIZED",
        "ABSTAINED_MAGNITUDE",
        "TRAINING_UP_BASE_RATE",
        "ALWAYS_UP",
        "PREVIOUS_24H_SIGN_PERSISTENCE",
        "ZERO_RETURN_MAGNITUDE",
        "PREDICTION LAYER  ->  DECISION / POLICY LAYER  ->  ECONOMIC / EXECUTION SIMULATION",
    ):
        assert required in contract, required


def test_the_source_roadmap_admits_no_family_by_listing_it() -> None:
    roadmap = _text(STATE["predictive_research_objective"]["source_roadmap"])
    assert "it is a map, not a schedule" in roadmap
    assert "Narrative plausibility alone is never evidence" in roadmap
    assert "no partisan interpretation" in roadmap
    assert "Do not ingest all families at once." in roadmap


# Every work package since the rebaseline renames the active task. The identity under test
# is "the active task is the declared successor", not its current title, so any known
# successor is normalized to the rebaseline anchor. Longest first: these names nest.
SUCCESSOR_TASK_TITLES = (
    "RESEARCH-DIRECTOR-CYCLE-QUALITY-ADJUDICATION-V1",
    "SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1",
    "RESEARCH-DIRECTOR-REVIEW-SYSTEM-G1-CHECKPOINT-1",
    "SYSTEM-G1-CHECKPOINT-1-SYNTHETIC-VERTICAL-SLICE",
    "PARKED-NO-ACTIVE-RESEARCH-TASK",
    "FINAL-PARKED-STATE-RECONCILIATION-V1",
    "RESEARCH-DIRECTOR-ADJUDICATION-CANDIDATE-1-DEVELOPMENT-V1",
    "EXECUTE-CANDIDATE-1-DEVELOPMENT-V1",
    "RESEARCH-DIRECTOR-EXECUTION-REVIEW-CANDIDATE-1-DEVELOPMENT-V1",
    "IMPLEMENT-CANDIDATE-1-DEVELOPMENT-V1",
    "RESEARCH-DIRECTOR-PROTOCOL-DESIGN-CANDIDATE-1-V1",
    "STRONG-STOP-PENDING-ASTRA-AFTER-CANDIDATE-1",
    "CANDIDATE-1-FROZEN-ADMISSION-V1",
    "RESEARCH-DIRECTOR-REALLOCATION-AFTER-PUBLIC-TAKER-FLOW-POWER-BLOCK",
    "IMPLEMENT-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1",
    "RESEARCH-DIRECTOR-REVIEW-PREDICTIVE-V2-INTERNAL-STRUCTURE-SELECTIVE-V1",
    "RESEARCH-DIRECTOR-REVIEW-PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1",
    "PREDICTIVE-V2-INTERNAL-STRUCTURE-SELECTIVE-V1",
    "PREDICTIVE-V2-DETERMINISTIC-CALENDAR-V1",
)
REBASELINE_TASK_TITLE = "RESEARCH-DIRECTOR-REVIEW-GENERATION-V2-REBASELINE"


def _normalize_current_task(text: str) -> str:
    for title in SUCCESSOR_TASK_TITLES:
        if title in text:
            return text.replace(title, REBASELINE_TASK_TITLE)
    return text


def test_the_predictive_foundation_checkpoint_completed_and_was_archived() -> None:
    """The rebaseline handed off to the foundation, which has since been executed."""
    # Since ADR-0031..ADR-0033 the pointers follow the reviewed public taker-flow foundation
    # and the active task; they are derived from those records, not pinned here.
    if "predictive_public_taker_flow_1h_incremental" in STATE:
        pointers = expected_state_pointers(ROOT, STATE)
        expected = pointers["next_recommended_work_package"]
        checkpoint = pointers["research_architecture.next_checkpoint"]
    elif "predictive_v2_internal_structure_selective" in STATE:
        expected = checkpoint = (
            "RESEARCH_DIRECTOR_REVIEW_PREDICTIVE_V2_INTERNAL_STRUCTURE_SELECTIVE_V1"
        )
    elif "predictive_v2_deterministic_calendar" in STATE:
        expected = checkpoint = "RESEARCH_DIRECTOR_REVIEW_PREDICTIVE_V2_DETERMINISTIC_CALENDAR_V1"
    else:
        expected = checkpoint = "RESEARCH_DIRECTOR_REVIEW_GENERATION_V2_REBASELINE"
    assert STATE["next_recommended_work_package"] == expected
    assert STATE["research_architecture"]["next_checkpoint"] == checkpoint
    task = _normalize_current_task(_text("tasks/CURRENT_TASK.md"))
    assert task.startswith("# CURRENT TASK — RESEARCH-DIRECTOR-REVIEW-GENERATION-V2-REBASELINE")
    for archived in (
        "tasks/archive/PREDICTIVE-RESEARCH-REBASELINE-V1.md",
        "tasks/archive/PREDICTIVE-BASELINES-V1.md",
        "tasks/archive/PREDICTIVE-INTERNAL-STRUCTURE-V1.md",
        "tasks/archive/PREDICTIVE-INTERNAL-NONLINEAR-V1.md",
        "tasks/archive/PREDICTIVE-STAGE2-SETTLED-FUNDING-V1.md",
        "tasks/archive/PREDICTIVE-STAGE2-OPEN-INTEREST-V1.md",
        "tasks/archive/PREDICTIVE-STAGE3-CROSS-ASSET-BREADTH-V1.md",
        "tasks/archive/PREDICTIVE-STAGE3-MACRO-VINTAGE-V1.md",
        "tasks/archive/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1.md",
        "tasks/archive/PREDICTIVE-GENERATION-V2-SELECTIVE-LONG-REBASELINE-V1.md",
    ):
        assert (ROOT / archived).is_file(), archived
    foundation = _text("tasks/archive/PREDICTIVE-BASELINES-V1.md")
    assert "Do not train a predictor." in foundation
    assert STATE["predictive_baselines"]["status"] == "COMPLETE"
