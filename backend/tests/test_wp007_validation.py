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
    # WP-017 brought the cumulative assessment count to 26; none is eligible or queried.
    assert result["sealed"] == {"assessed": 26, "eligible": 0, "queries": 0}


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
    # WP-011 through preregistered WP-017 each added one hypothesis, two configurations,
    # and eight profiles.
    assert totals["material_economic_hypotheses"] == 6 + 1 + 1 + 1 + 1 + 1 + 1 + 1
    assert totals["configuration_variants"] == 15 + 2 + 2 + 2 + 2 + 2 + 2 + 2
    assert totals["profile_trials"] == 77 + 8 + 8 + 8 + 8 + 8 + 8 + 8
    # WP-016 and WP-017 each prospectively reserve ten fits; none has executed yet.
    assert totals["supervised_model_fits"] == 12 + 144 + 18 + 12 + 12 + 10 + 10 + 10
    assert totals["wp012_variants_reserved"] == 2
    assert totals["wp012_profiles_reserved"] == 8
    assert totals["wp013_variants_reserved"] == 2
    assert totals["wp013_profiles_reserved"] == 8
    assert totals["wp014_variants_reserved"] == 2
    assert totals["wp014_profiles_reserved"] == 8
    assert totals["wp015_variants_reserved"] == 2
    assert totals["wp015_profiles_reserved"] == 8
    assert totals["wp016_variants_reserved"] == 2
    assert totals["wp016_profiles_reserved"] == 8
    assert totals["wp017_variants_reserved"] == 2
    assert totals["wp017_profiles_reserved"] == 8
    assert totals["numeric_parameter_variants"] == 0
    assert totals["adaptive_decisions"] == 15
    assert totals["result_dependent_forks"] == 12


def test_both_order_flow_candidates_are_sealed_ineligible():
    rows = {item["experiment_id"]: item for item in build_eligibility_table()["candidates"]}
    for experiment_id in SPEC:
        assert rows[experiment_id]["sealed_eligibility"] == "NOT_ELIGIBLE_REJECTED"
        assert rows[experiment_id]["sealed_allocation"] is None
