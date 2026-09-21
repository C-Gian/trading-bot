"""Hand-worked proofs for the frozen Generation V2 selective LONG scorer.

Every fixture is synthetic, so these run without the installed market data. They pin the
behaviour the contract promises *before* any Generation V2 candidate exists: what counts as an
action, what counts as a win, which failure modes the coverage and count floors are supposed to
catch, and that enrichment is measured against the ambient fold rather than against 50%.
"""

from __future__ import annotations

import pytest
from app.predictive import DOWN, NEUTRAL, UP
from app.predictive.selective_long import (
    ACTION_THRESHOLD,
    GATE_NAMES,
    LONG,
    MAGNITUDE_STATUS,
    NO_TRADE,
    SELECTIVE_BLOCK_LENGTH_HOURS,
    SELECTIVE_REPLICATES,
    SelectiveRecord,
    SelectiveScoringError,
    action_for,
    advancement_gate,
    build_selective_fold,
    enrichment_interval,
    frozen_semantics,
    pooled_summary,
    required_non_negative_folds,
)

HOUR = 3600
START = 1_577_836_800  # 2020-01-01T00:00:00Z
SEED = 20260921


def fold(name: str, rows: list[tuple[str, float | None]], start: int = START):
    """One record per consecutive hour, in the order given."""
    records = [
        SelectiveRecord(open_time=start + index * HOUR, truth=truth, p_up=p_up)
        for index, (truth, p_up) in enumerate(rows)
    ]
    return build_selective_fold(name, [record.open_time for record in records], records)


def repeat(pattern: list[tuple[str, float | None]], times: int):
    return [item for _ in range(times) for item in pattern]


def summarize(folds, training=0.5):
    return pooled_summary(folds, {item.name: training for item in folds})


# --- the frozen action policy ------------------------------------------------------


def test_the_action_threshold_is_exactly_0_60_and_ties_act_long():
    assert ACTION_THRESHOLD == 0.60
    assert action_for(0.60) == LONG
    assert action_for(0.61) == LONG
    assert action_for(1.0) == LONG


def test_a_probability_below_the_threshold_is_no_trade():
    assert action_for(0.5999999) == NO_TRADE
    assert action_for(0.5) == NO_TRADE
    assert action_for(0.0) == NO_TRADE


def test_a_probability_outside_the_unit_interval_is_refused():
    with pytest.raises(SelectiveScoringError):
        action_for(1.5)
    with pytest.raises(SelectiveScoringError):
        SelectiveRecord(open_time=START, truth=UP, p_up=-0.1)


def test_a_feature_invalid_row_has_no_action_and_leaves_every_rate_alone():
    one = fold("f", [(UP, 0.9), (DOWN, None), (UP, None)])
    summary = summarize([one])
    assert summary["eligible_decision_timestamps"] == 3
    assert summary["feature_valid_timestamps"] == 1
    assert summary["feature_invalid_timestamps"] == 2
    assert summary["long_actions"] == 1
    assert summary["action_coverage"] == 1.0
    assert summary["selective_long_win_rate"] == 1.0
    # The control still sees all three directionally scorable rows.
    assert summary["directionally_scorable_timestamps"] == 3
    assert summary["full_fold_up_rate"] == pytest.approx(2 / 3)


# --- truth accounting --------------------------------------------------------------


def test_an_exact_zero_truth_is_counted_but_is_never_a_win():
    one = fold("f", [(UP, 0.9), (NEUTRAL, 0.9), (DOWN, 0.9)])
    summary = summarize([one])
    assert summary["neutral_truths"] == 1
    assert summary["long_actions"] == 3
    assert summary["long_actions_on_neutral_truth"] == 1
    assert summary["actionable_long_predictions"] == 2
    assert summary["selective_long_wins"] == 1
    assert summary["selective_long_win_rate"] == 0.5
    assert summary["directionally_scorable_timestamps"] == 2
    assert summary["full_fold_up_rate"] == 0.5
    assert summary["enrichment"] == 0.0


def test_action_coverage_is_long_actions_over_feature_valid_timestamps():
    one = fold("f", [(UP, 0.9), (DOWN, 0.1), (UP, 0.1), (DOWN, None)])
    summary = summarize([one])
    assert summary["feature_valid_timestamps"] == 3
    assert summary["long_actions"] == 1
    assert summary["no_trade_actions"] == 2
    assert summary["action_coverage"] == pytest.approx(1 / 3)


# --- the scenarios the gate exists to separate -------------------------------------


def gate_for(folds, training=0.5, seed=SEED, replicates=2000):
    summary = summarize(folds, training)
    interval = enrichment_interval(folds, seed=seed, replicates=replicates)
    return summary, interval, advancement_gate(summary, interval)


def test_a_perfect_selective_predictor_passes_every_condition():
    # 1200 hours per fold; the model acts on 20% of them, is always right, and says so:
    # claiming 0.9 while winning 1.0 would itself fail the action-calibration condition.
    pattern = [(UP, 0.98), (DOWN, 0.2), (UP, 0.2), (DOWN, 0.2), (DOWN, 0.2)]
    folds = [fold(name, repeat(pattern, 240)) for name in ("2020", "2021", "2022")]
    summary, _, gate = gate_for(folds)
    assert summary["selective_long_win_rate"] == 1.0
    assert summary["action_coverage"] == pytest.approx(0.2)
    assert summary["full_fold_up_rate"] == pytest.approx(0.4)
    assert summary["enrichment"] == pytest.approx(0.6)
    assert gate["failed_conditions"] == []
    assert gate["advances"] is True


def test_an_always_wrong_selector_fails_the_directional_conditions():
    pattern = [(DOWN, 0.9), (UP, 0.2), (UP, 0.2), (UP, 0.2), (UP, 0.2)]
    folds = [fold(name, repeat(pattern, 240)) for name in ("2020", "2021", "2022")]
    summary, _, gate = gate_for(folds)
    assert summary["selective_long_win_rate"] == 0.0
    assert gate["advances"] is False
    for name in (GATE_NAMES[4], GATE_NAMES[5], GATE_NAMES[6], GATE_NAMES[7]):
        assert name in gate["failed_conditions"], name


def test_one_perfect_action_fails_the_sample_and_coverage_floors():
    pattern = [(DOWN, 0.2)] * 400
    rows = [(UP, 0.95), *pattern]
    folds = [fold(name, list(rows)) for name in ("2020", "2021", "2022")]
    summary = summarize(folds)
    interval = enrichment_interval(folds, seed=SEED, replicates=2000)
    gate = advancement_gate(summary, interval)
    assert summary["selective_long_win_rate"] == 1.0  # flawless, and meaningless
    assert summary["actionable_long_predictions"] == 3
    assert gate["advances"] is False
    assert GATE_NAMES[0] in gate["failed_conditions"]
    assert GATE_NAMES[2] in gate["failed_conditions"]
    assert GATE_NAMES[3] in gate["failed_conditions"]


def test_one_percent_pooled_coverage_fails_the_two_percent_gate():
    # Exactly one action per 100 hours: 1% coverage, with a flawless win rate.
    pattern = [(UP, 0.9)] + [(DOWN, 0.2)] * 99
    folds = [fold(name, repeat(pattern, 10)) for name in ("2020", "2021", "2022")]
    summary, _, gate = gate_for(folds)
    assert summary["action_coverage"] == pytest.approx(0.01)
    assert summary["actionable_long_predictions"] == 30
    assert GATE_NAMES[0] in gate["failed_conditions"]
    assert gate["advances"] is False


def test_sixty_percent_hit_rate_against_a_sixty_percent_fold_shows_no_enrichment():
    # The model acts on a 60/40 slice of a fold that is itself 60/40. Winning 60% of the
    # time here is the market, not the model.
    pattern = [
        (UP, 0.9),
        (UP, 0.9),
        (UP, 0.9),
        (DOWN, 0.9),
        (DOWN, 0.9),
        (UP, 0.2),
        (UP, 0.2),
        (UP, 0.2),
        (DOWN, 0.2),
        (DOWN, 0.2),
    ]
    folds = [fold(name, repeat(pattern, 120)) for name in ("2020", "2021", "2022")]
    summary, _, gate = gate_for(folds)
    assert summary["selective_long_win_rate"] == pytest.approx(0.6)
    assert summary["full_fold_up_rate"] == pytest.approx(0.6)
    assert summary["enrichment"] == pytest.approx(0.0)
    assert GATE_NAMES[4] not in gate["failed_conditions"]  # the win rate alone is fine
    assert GATE_NAMES[5] in gate["failed_conditions"]  # the enrichment is not
    assert GATE_NAMES[6] in gate["failed_conditions"]
    assert gate["advances"] is False


def test_sixty_five_percent_against_a_fifty_five_percent_fold_passes_the_effect_pieces():
    # Acted slice: 13 UP / 7 DOWN = 0.65. Untouched slice: 9 UP / 11 DOWN = 0.45.
    # Whole fold: 22 UP / 18 DOWN = 0.55. Enrichment +0.10.
    acted = [(UP, 0.65)] * 13 + [(DOWN, 0.65)] * 7
    ignored = [(UP, 0.2)] * 9 + [(DOWN, 0.2)] * 11
    folds = [fold(name, repeat(acted + ignored, 30)) for name in ("2020", "2021", "2022")]
    summary, _, gate = gate_for(folds)
    assert summary["selective_long_win_rate"] == pytest.approx(0.65)
    assert summary["full_fold_up_rate"] == pytest.approx(0.55)
    assert summary["enrichment"] == pytest.approx(0.10)
    assert summary["action_coverage"] == pytest.approx(0.5)
    for name in (
        GATE_NAMES[0],
        GATE_NAMES[1],
        GATE_NAMES[2],
        GATE_NAMES[3],
        GATE_NAMES[4],
        GATE_NAMES[5],
        GATE_NAMES[6],
        GATE_NAMES[7],
        GATE_NAMES[9],
    ):
        assert name not in gate["failed_conditions"], name


def test_overconfident_probabilities_fail_the_action_calibration_gate():
    # The same 65%-versus-55% enrichment, but the model claims 0.90 on every action.
    acted = [(UP, 0.90)] * 13 + [(DOWN, 0.90)] * 7
    ignored = [(UP, 0.2)] * 9 + [(DOWN, 0.2)] * 11
    folds = [fold(name, repeat(acted + ignored, 30)) for name in ("2020", "2021", "2022")]
    summary, _, gate = gate_for(folds)
    assert summary["mean_predicted_p_up_on_actions"] == pytest.approx(0.90)
    assert summary["selective_long_win_rate"] == pytest.approx(0.65)
    assert summary["action_calibration_gap"] == pytest.approx(0.25)
    assert GATE_NAMES[9] in gate["failed_conditions"]
    assert GATE_NAMES[5] not in gate["failed_conditions"]  # the enrichment still holds
    assert gate["advances"] is False


def test_a_worse_than_base_rate_full_probability_brier_fails_condition_nine():
    # An enriching but badly scaled model: every probability is extreme, so the
    # full-probability Brier is worse than a constant training base rate of 0.55.
    acted = [(UP, 1.0)] * 13 + [(DOWN, 1.0)] * 7
    ignored = [(UP, 0.0)] * 9 + [(DOWN, 0.0)] * 11
    folds = [fold(name, repeat(acted + ignored, 30)) for name in ("2020", "2021", "2022")]
    summary, _, gate = gate_for(folds, training=0.55)
    assert summary["full_probability_brier"] == pytest.approx(0.4)
    assert summary["matched_training_up_base_rate_brier"] == pytest.approx(0.2475)
    assert GATE_NAMES[8] in gate["failed_conditions"]


# --- pooling, fold rules and the interval -------------------------------------------


def test_the_two_thirds_fold_rule_follows_the_included_fold_count():
    assert required_non_negative_folds(3) == 2
    assert required_non_negative_folds(5) == 4
    assert required_non_negative_folds(6) == 4


def test_a_single_negative_fold_out_of_three_still_satisfies_two_thirds():
    good = repeat([(UP, 0.9)] * 3 + [(DOWN, 0.9)] + [(DOWN, 0.2)] * 6, 60)
    bad = repeat([(DOWN, 0.9)] * 3 + [(UP, 0.9)] + [(UP, 0.2)] * 6, 60)
    folds = [fold("2020", good), fold("2021", good), fold("2022", bad)]
    _, _, gate = gate_for(folds)
    assert gate["non_negative_enrichment_folds"] == 2
    assert gate["required_non_negative_folds"] == 2
    assert GATE_NAMES[7] not in gate["failed_conditions"]


def test_pooled_rates_are_recomputed_from_counts_and_never_averaged():
    # A large fold at 0.5 and a tiny fold at 1.0 must not pool to 0.75.
    big = fold("2020", repeat([(UP, 0.9), (DOWN, 0.9)], 100))
    small = fold("2021", [(UP, 0.9), (UP, 0.9)])
    summary = summarize([big, small])
    assert summary["by_fold"]["2020"]["selective_long_win_rate"] == pytest.approx(0.5)
    assert summary["by_fold"]["2021"]["selective_long_win_rate"] == pytest.approx(1.0)
    assert summary["selective_long_win_rate"] == pytest.approx(102 / 202)


def test_the_bootstrap_is_deterministic_for_a_fixed_seed():
    # Deliberately heterogeneous along the timeline: a perfectly periodic fixture would give
    # every resample the same rates and hide a seed that was being ignored.
    early = repeat([(UP, 0.9), (DOWN, 0.2), (UP, 0.2), (DOWN, 0.2), (DOWN, 0.2)], 60)
    late = repeat([(DOWN, 0.9), (UP, 0.2), (DOWN, 0.2), (UP, 0.2), (UP, 0.2)], 40)
    folds = [fold(name, early + late) for name in ("2020", "2021")]
    first = enrichment_interval(folds, seed=SEED, replicates=1000)
    second = enrichment_interval(folds, seed=SEED, replicates=1000)
    third = enrichment_interval(folds, seed=SEED + 1, replicates=1000)
    assert first["interval"] == second["interval"]
    assert first["interval"] != third["interval"]
    assert first["block_length_hours"] == SELECTIVE_BLOCK_LENGTH_HOURS
    assert first["blocks_cross_fold_boundaries"] is False
    assert first["recomputes_control_on_every_replicate"] is True


def test_replicates_without_an_actionable_long_are_discarded_and_counted():
    # Two actions in an 800-hour fold: many 48h-block resamples contain none of them.
    rows = [(DOWN, 0.2)] * 800
    rows[10] = (UP, 0.9)
    rows[11] = (UP, 0.9)
    one = fold("2020", rows)
    interval = enrichment_interval([one], seed=SEED, replicates=1000)
    assert interval["discarded_replicates_without_an_actionable_long"] > 0
    assert (
        interval["retained_replicates"]
        + (interval["discarded_replicates_without_an_actionable_long"])
        == 1000
    )
    assert interval["resample_support"] == "UNSTABLE_RESAMPLE_SUPPORT"
    assert interval["interval_lower_bound_above_zero"] is False


def test_an_unstable_interval_fails_the_interval_condition_closed():
    rows = [(DOWN, 0.2)] * 800
    rows[10] = (UP, 0.9)
    rows[11] = (UP, 0.9)
    folds = [fold(name, list(rows)) for name in ("2020", "2021", "2022")]
    summary = summarize(folds)
    interval = enrichment_interval(folds, seed=SEED, replicates=1000)
    gate = advancement_gate(summary, interval)
    assert interval["resample_support"] == "UNSTABLE_RESAMPLE_SUPPORT"
    assert GATE_NAMES[6] in gate["failed_conditions"]


def test_the_interval_refuses_a_fold_set_with_no_actionable_long_at_all():
    one = fold("2020", repeat([(DOWN, 0.2), (UP, 0.2)], 100))
    with pytest.raises(SelectiveScoringError):
        enrichment_interval([one], seed=SEED, replicates=100)


# --- the freeze itself ---------------------------------------------------------------


def test_the_frozen_semantics_match_the_contract_thresholds():
    semantics = frozen_semantics()
    assert semantics["generation"] == "PREDICTIVE_RESEARCH_GENERATION_V2"
    assert semantics["action_threshold"] == 0.60
    assert semantics["action_threshold_tunable_on_development"] is False
    assert semantics["short_authorized"] is False
    assert semantics["primary_metric"] == "SELECTIVE_LONG_WIN_RATE"
    assert semantics["primary_control"] == "FULL_FOLD_UP_RATE"
    assert semantics["primary_control_uses_candidate_action_selection"] is False
    assert semantics["primary_control_visible_to_fitting_or_calibration"] is False
    assert semantics["thresholds_weakenable_after_a_result"] is False
    assert semantics["gate_names"] == list(GATE_NAMES) and len(GATE_NAMES) == 10
    assert semantics["inference"]["replicates"] == SELECTIVE_REPLICATES == 10_000
    assert semantics["inference"]["block_length_hours"] == 48
    assert semantics["inference"]["seed"] == "DECLARED_PER_FAMILY_BEFORE_EXECUTION"
    assert semantics["magnitude_declared"] is False
    assert semantics["magnitude_status"] == MAGNITUDE_STATUS
    assert semantics["real_money"] is False and semantics["sealed_queries"] == 0


def test_a_fold_refuses_an_off_grid_or_duplicated_record():
    records = [SelectiveRecord(open_time=START, truth=UP, p_up=0.9)]
    with pytest.raises(SelectiveScoringError):
        build_selective_fold("f", [START], [*records, records[0]])
    with pytest.raises(SelectiveScoringError):
        build_selective_fold(
            "f", [START], [SelectiveRecord(open_time=START + 61, truth=UP, p_up=0.9)]
        )
