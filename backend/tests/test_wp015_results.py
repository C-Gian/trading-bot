"""WP-015 completed result, reconciliation, diagnostics, and safety invariants."""

import json
from pathlib import Path

from app.predictive.taker_flow_validation import expected_state_pointers
from app.research.records import validate_result

ROOT = Path(__file__).resolve().parents[2]
PRIMARY = "INTERNAL_PLUS_FUNDING_HGBR"
CONTROL = "INTERNAL_HGBR_MATCHED_FUNDING"


def read_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_wp015_matched_results_and_funding_diagnostics() -> None:
    comparison = read_json("reports/research/WP-015-COMPARISON.json")
    primary = comparison["configurations"][PRIMARY]
    control = comparison["configurations"][CONTROL]
    assert primary["terminal_classification"] == "REJECT_COST_DOMINATED"
    assert control["terminal_classification"] == "REJECT"
    assert comparison["primary_vs_control"]["eligible_universe_matched"] is True
    assert comparison["primary_vs_control"]["executed_trade_sets_paired"] is False
    assert primary["primary_result"] == -0.0814500414
    assert control["primary_result"] == -0.1236220929
    assert comparison["primary_vs_control"]["default_net_expectancy_difference_r"] == (
        0.04217205149999999
    )
    default = primary["profiles"]["DEFAULT"]
    assert default["metrics"]["trade_count"] == 716
    assert default["stability"]["nonnegative_fold_count"] == 0
    assert default["diagnostics"]["minimum_fold_trades"] == 68
    assert primary["prediction_diagnostics"]["prediction_positive_hours"] == 4444
    assert primary["prediction_diagnostics"]["pooled_prediction_label_pearson"] == (
        -0.025554931116266017
    )

    diagnostics = read_json("reports/research/WP-015-FUNDING-DIAGNOSTICS.json")
    assert diagnostics["funding_observations_acquired"] == 5819
    assert diagnostics["hourly_eligible_coverage"] == 41143
    assert diagnostics["used_to_adapt_experiment"] is False
    assert (
        diagnostics["default_trade_outcomes_by_funding_sign"]["ZERO"]["valid_resolved_trades"] == 0
    )


def test_wp015_independent_reconciliation_is_exact() -> None:
    report = read_json("reports/validation/WP-015-MODEL-RECONCILIATION.json")
    assert report["status"] == "PASS"
    assert report["independent_of_primary_runner"] is True
    assert report["prediction_tolerance"] == 1e-10
    assert report["maximum_prediction_absolute_difference"] == 0.0
    assert report["model_refits"] == 10
    assert set(report["checks"].values()) == {"PASS"}
    assert not report["mismatches"]


# Every work package since the rebaseline renames the active task. The identity under test
# is "the active task is the declared successor", not its current title, so any known
# successor is normalized to the rebaseline anchor. Longest first: these names nest.
SUCCESSOR_TASK_TITLES = (
    "RESEARCH-DIRECTOR-G1-INCOMPLETE-BAR-FIX-REVIEW-V1",
    "FIX-SYSTEM-G1-INCOMPLETE-BAR-RECURSIVE-STATE-V1",
    "RESEARCH-DIRECTOR-G1-DEVELOPMENT-EXECUTION-REVIEW-V1",
    "IMPLEMENT-SYSTEM-G1-DEVELOPMENT-V1",
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


def test_wp015_records_and_state_are_safe() -> None:
    experiments = (
        "EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR",
        "EXP-ML-025-INTERNAL-HGBR-MATCHED-FUNDING",
    )
    for experiment in experiments:
        directory = ROOT / "research/experiments" / experiment
        result = validate_result(directory / "result.json", directory / "preregistration.json")
        assert result["status"] == "COMPLETED"
        assert result["validation_outcome"] == "PASS"
        assert result["trial_accounting"] == {"declared_budget": 4, "executed_trials": 4}
        assert result["secondary_results"]["independent_reconciliation"] == "PASS"

    state = read_json("state/current_state.json")
    assert state["experiments_completed"] == 26
    assert (
        state["latest_reviewed_checkpoint"]
        == (expected_state_pointers(ROOT, state)["latest_reviewed_checkpoint"])
    )
    assert (
        state["latest_executor_checkpoint"]
        == (expected_state_pointers(ROOT, state)["latest_executor_checkpoint"])
    )
    challenger = state["funding_context_challenger"]
    assert challenger["actual_model_fits"] == challenger["reserved_model_fits"] == 10
    assert challenger["model_reconciliation"] == "PASS"
    assert challenger["futures_execution"] is False
    assert challenger["sealed_eligibility"] == "NOT_ELIGIBLE_REJECTED"
    assert state["exogenous_acquisition_pause"]["pause_reason"] == ("PAUSED_FOR_PRODUCT_PRIORITY")
    assert state["paper_trades_completed"] == 0
    assert state["champion_status"] == "NONE"
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["real_money_authorized"] is False
    archived = (ROOT / "tasks/archive/WP-015.md").read_text(encoding="utf-8")
    current = (ROOT / "tasks/CURRENT_TASK.md").read_text(encoding="utf-8")
    current = _normalize_current_task(current)
    assert "# CURRENT TASK — WP-015" in archived
    assert "# CURRENT TASK — RESEARCH-DIRECTOR-REVIEW-GENERATION-V2-REBASELINE" in current
    assert (ROOT / "tasks/archive/PROSPECTIVE-EVIDENCE-COLLECTION-V1_1.md").is_file()
    assert (ROOT / "tasks/archive/PREDICTIVE-RESEARCH-REBASELINE-V1.md").is_file()
    assert (ROOT / "tasks/archive/PREDICTIVE-BASELINES-V1.md").is_file()
    assert (ROOT / "tasks/archive/PROSPECTIVE-RUNTIME-ARTIFACT-PROVENANCE-FIX-V1_1.md").is_file()
    assert (
        ROOT / "tasks/archive/"
        "P1A-POWER-BLOCK-REVIEW-RESEARCH-ARCHITECTURE-SYNTHESIS-V1-P2-CYCLE-FOUNDATION-DESIGN.md"
    ).is_file()
    assert (ROOT / "tasks/archive/P0.1-DETECTABILITY-INFERENCE-AND-CI-PORTABILITY-FIX.md").is_file()
    assert (ROOT / "tasks/archive/WP-017-CFTC-LEVERAGED-POSITIONING-PREP.md").is_file()
    assert (ROOT / "tasks/archive/WP-016-PREP.md").is_file()
