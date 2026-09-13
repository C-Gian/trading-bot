from app.research.exogenous import ALFRED_SERIES, GDELT_CHANNELS, hours
from app.research.registry import cumulative_accounting, directions


def test_wp009_fixed_scope_and_non_trial_accounting() -> None:
    assert len(GDELT_CHANNELS) == 5
    assert len(ALFRED_SERIES) == 8
    assert len(hours()) == 64656
    wp009 = [item for item in directions() if item["work_package"] == "WP-009"]
    assert len(wp009) == 1
    assert wp009[0]["strategy_experiments"] == wp009[0]["model_fits"] == 0
    # WP-009 itself consumed no strategy trial. WP-011 through WP-014 later advanced these
    # cumulative totals; the WP-009 scope assertions above are what this test guards.
    totals = cumulative_accounting()
    assert totals["adaptive_decisions"] == totals["result_dependent_forks"] == 10
    assert totals["configuration_variants"] == 23
    assert totals["profile_trials"] == 109
    assert totals["supervised_model_fits"] == 198
