from app.research.exogenous import ALFRED_SERIES, GDELT_CHANNELS, hours
from app.research.registry import cumulative_accounting, directions


def test_wp009_fixed_scope_and_non_trial_accounting() -> None:
    assert len(GDELT_CHANNELS) == 5
    assert len(ALFRED_SERIES) == 8
    assert len(hours()) == 64656
    wp009 = [item for item in directions() if item["work_package"] == "WP-009"]
    assert len(wp009) == 1
    assert wp009[0]["strategy_experiments"] == wp009[0]["model_fits"] == 0
    # WP-009 itself consumed no strategy trial. Later work through preregistered WP-017
    # advanced cumulative totals; the WP-009 scope assertions above remain unchanged.
    totals = cumulative_accounting()
    assert totals["adaptive_decisions"] == 14
    assert totals["result_dependent_forks"] == 11
    assert totals["configuration_variants"] == 29
    assert totals["profile_trials"] == 133
    assert totals["supervised_model_fits"] == 228
