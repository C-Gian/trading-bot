"""WP-007 checkpoint projections and immutable chronology validate without rerunning markets."""

from app.research.registry import cumulative_accounting
from app.research.sealed_eligibility import build_eligibility_table
from app.research.wp007 import SPEC, validate_admission
from app.research.wp007_validation import validate_wp007
from app.research.wp007_views import build_wp007_comparison


def test_repository_checkpoint_validates():
    result = validate_wp007()
    assert result["status"] == "PASS"
    assert result["family_terminal_classification"] == "REJECT_COST_DOMINATED"
    assert result["classifications"] == {
        "FLOW_CORE": "REJECT_COST_DOMINATED",
        "FLOW_PRICE_RESPONSE": "REJECT_COST_DOMINATED",
    }
    assert result["sealed"] == {"assessed": 15, "eligible": 0, "queries": 0}


def test_results_answer_the_preregistered_cost_and_timing_questions():
    comparison = build_wp007_comparison()
    core = comparison["variants"]["FLOW_CORE"]
    price = comparison["variants"]["FLOW_PRICE_RESPONSE"]
    assert core["zero_cost_net_expectancy_r"] > 0 > core["default_net_expectancy_r"]
    assert core["double_cost_net_expectancy_r"] < core["default_net_expectancy_r"]
    assert core["delay_net_expectancy_r"] < 0
    assert price["trade_count"] < core["trade_count"]
    assert price["default_net_expectancy_r"] > core["default_net_expectancy_r"]
    assert comparison["paired_comparison"] is False


def test_admission_reproduces_after_its_own_ledger_exists():
    admission = validate_admission()
    assert admission["family_classification"] == "NEW_FAMILY"
    assert admission["market_results_observed_at_admission"] == 0
    assert {item["experiment_id"] for item in admission["variants"]} == set(SPEC)


def test_cumulative_search_accounting_is_exact():
    totals = cumulative_accounting()
    assert totals["material_economic_hypotheses"] == 6
    assert totals["configuration_variants"] == 15
    assert totals["profile_trials"] == 77
    assert totals["supervised_model_fits"] == 12
    assert totals["numeric_parameter_variants"] == 0
    assert totals["adaptive_decisions"] == totals["result_dependent_forks"] == 5


def test_both_order_flow_candidates_are_sealed_ineligible():
    rows = {item["experiment_id"]: item for item in build_eligibility_table()["candidates"]}
    for experiment_id in SPEC:
        assert rows[experiment_id]["sealed_eligibility"] == "NOT_ELIGIBLE_REJECTED"
        assert rows[experiment_id]["sealed_allocation"] is None
