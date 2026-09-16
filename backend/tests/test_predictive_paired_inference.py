"""Proofs for the paired, fold-stratified moving-block bootstrap.

The fixtures are built so the answers are hand-computable: when a fold's timeline is exactly
one block long there is only one legal block start, so every replicate reproduces the fold
exactly and the interval collapses onto the observed delta. If blocks could cross a fold
boundary, or if abstentions were compressed into adjacency, those fixtures would not hold.
"""

from __future__ import annotations

import pytest
from app.predictive.labels import HOUR_SECONDS
from app.predictive.paired_inference import (
    PAIRED_ALPHA,
    PAIRED_BLOCK_LENGTH_HOURS,
    PAIRED_REPLICATES,
    PAIRED_SEED,
    PairedInferenceError,
    PairedRecord,
    block_sums,
    build_paired_fold,
    observed_delta,
    paired_delta_interval,
)


def hours(index: int) -> int:
    return index * HOUR_SECONDS


def constant_fold(name: str, candidate: bool, baseline: bool, span: int = 48):
    """A fold whose timeline is exactly `span` hours with a record in every slot."""
    eligible = [hours(index) for index in range(span)]
    records = [
        PairedRecord(open_time=moment, candidate_correct=candidate, baseline_correct=baseline)
        for moment in eligible
    ]
    return build_paired_fold(name, eligible, records)


def shifted_fold(name: str, start: int, candidate: bool, baseline: bool, span: int = 48):
    eligible = [hours(start + index) for index in range(span)]
    records = [
        PairedRecord(open_time=moment, candidate_correct=candidate, baseline_correct=baseline)
        for moment in eligible
    ]
    return build_paired_fold(name, eligible, records)


def test_the_frozen_inference_constants_are_what_the_design_declares():
    assert PAIRED_BLOCK_LENGTH_HOURS == 48
    assert PAIRED_REPLICATES == 10_000
    assert PAIRED_SEED == 20260916
    assert PAIRED_ALPHA == 0.025


def test_block_sums_are_hand_computable():
    import numpy as np

    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    full, partial, draws, block = block_sums(values, 2)
    # Five hours in blocks of two: three blocks, the last truncated to one hour.
    assert block == 2 and draws == 3
    assert list(full) == [3.0, 5.0, 7.0, 9.0]
    assert list(partial) == [1.0, 2.0, 3.0, 4.0]


def test_a_block_longer_than_the_timeline_collapses_to_the_whole_timeline():
    import numpy as np

    full, partial, draws, block = block_sums(np.array([1.0, 2.0, 3.0]), 48)
    assert block == 3 and draws == 1
    assert list(full) == [6.0] and list(partial) == [6.0]


def test_observed_delta_is_the_paired_difference_on_identical_records():
    fold = build_paired_fold(
        "2019",
        [hours(index) for index in range(4)],
        [
            PairedRecord(hours(0), True, True),
            PairedRecord(hours(1), True, False),
            PairedRecord(hours(2), False, True),
            PairedRecord(hours(3), False, False),
        ],
    )
    summary = observed_delta([fold])
    assert summary["paired_records"] == 4
    assert summary["candidate_win_rate"] == 0.5
    assert summary["matched_baseline_win_rate"] == 0.5
    assert summary["delta"] == 0.0


def test_the_timeline_keeps_gaps_instead_of_compressing_abstentions():
    # Eleven eligible hours, only two of which carry an actionable record.
    eligible = [hours(index) for index in range(11)]
    records = [PairedRecord(hours(0), True, False), PairedRecord(hours(10), True, False)]
    fold = build_paired_fold("2019", eligible, records)
    assert fold.span_hours == 11
    summary = paired_delta_interval([fold], block_length=11, replicates=200)
    geometry = summary["fold_geometry"]["2019"]
    assert geometry["timeline_hours"] == 11
    assert geometry["records"] == 2
    # One legal block start on an 11-hour timeline, so every replicate is the fold itself.
    assert geometry["block_start_positions"] == 1
    assert summary["interval"] == [1.0, 1.0]
    assert summary["delta"] == 1.0


def test_two_single_block_folds_reproduce_the_pooled_delta_exactly():
    """If a block could straddle the boundary, this fixture would not be degenerate."""
    winner = constant_fold("2019", candidate=True, baseline=False)
    loser = shifted_fold("2020", 1000, candidate=False, baseline=True)
    summary = paired_delta_interval([winner, loser], replicates=500)
    # 48 records right and 48 records wrong against the mirror-image control.
    assert summary["paired_records"] == 96
    assert summary["candidate_win_rate"] == 0.5
    assert summary["matched_baseline_win_rate"] == 0.5
    assert summary["delta"] == 0.0
    assert summary["interval"] == [0.0, 0.0]
    assert summary["blocks_cross_fold_boundaries"] is False


def test_each_fold_contributes_exactly_its_own_timeline_length():
    winner = constant_fold("2019", candidate=True, baseline=False, span=48)
    loser = shifted_fold("2020", 5000, candidate=False, baseline=True, span=96)
    summary = paired_delta_interval([winner, loser], replicates=300)
    geometry = summary["fold_geometry"]
    assert geometry["2019"]["timeline_hours"] == 48
    assert geometry["2019"]["blocks_per_replicate"] == 1
    assert geometry["2020"]["timeline_hours"] == 96
    assert geometry["2020"]["blocks_per_replicate"] == 2
    # 48 correct records always, 96 incorrect records always: the delta is fixed at -1/3.
    assert summary["delta"] == pytest.approx(48 / 144 - 96 / 144)
    assert summary["interval"] == pytest.approx([-1 / 3, -1 / 3])


def test_the_interval_is_deterministic_under_the_frozen_seed_and_moves_with_another():
    import random

    generator = random.Random(11)
    eligible = [hours(index) for index in range(480)]
    records = [
        PairedRecord(moment, generator.random() < 0.55, generator.random() < 0.52)
        for moment in eligible
    ]
    fold = build_paired_fold("2019", eligible, records)
    first = paired_delta_interval([fold], replicates=2000)
    second = paired_delta_interval([fold], replicates=2000)
    assert first["interval"] == second["interval"]
    other = paired_delta_interval([fold], replicates=2000, seed=PAIRED_SEED + 1)
    assert other["interval"] != first["interval"]
    assert first["interval"][0] <= first["delta"] <= first["interval"][1]


def test_a_wider_alpha_never_produces_a_wider_interval():
    import random

    generator = random.Random(3)
    eligible = [hours(index) for index in range(720)]
    records = [
        PairedRecord(moment, generator.random() < 0.6, generator.random() < 0.5)
        for moment in eligible
    ]
    fold = build_paired_fold("2019", eligible, records)
    tight = paired_delta_interval([fold], replicates=2000, alpha=0.20)
    wide = paired_delta_interval([fold], replicates=2000, alpha=PAIRED_ALPHA)
    assert wide["interval"][0] <= tight["interval"][0]
    assert wide["interval"][1] >= tight["interval"][1]
    assert wide["interval_mass"] == 0.975


def test_the_interval_detects_a_real_paired_advantage():
    import random

    generator = random.Random(5)
    eligible = [hours(index) for index in range(4320)]
    records = []
    for moment in eligible:
        baseline = generator.random() < 0.52
        candidate = baseline if generator.random() < 0.9 else True
        records.append(PairedRecord(moment, candidate, baseline))
    fold = build_paired_fold("2019", eligible, records)
    summary = paired_delta_interval([fold], replicates=2000)
    assert summary["delta"] > 0.0
    assert summary["interval_lower_bound_above_zero"] is True
    assert summary["interval"][0] > 0.0


def test_the_builder_refuses_records_outside_its_own_fold():
    eligible = [hours(index) for index in range(10)]
    stray = [PairedRecord(hours(50), True, False)]
    with pytest.raises(PairedInferenceError, match="outside the fold timeline"):
        build_paired_fold("2019", eligible, stray)
    with pytest.raises(PairedInferenceError, match="no eligible decision instant"):
        build_paired_fold("2019", [], [])
    duplicated = [PairedRecord(hours(1), True, False), PairedRecord(hours(1), False, True)]
    with pytest.raises(PairedInferenceError, match="duplicate decision instants"):
        build_paired_fold("2019", eligible, duplicated)


def test_an_off_grid_record_is_rejected_rather_than_snapped():
    eligible = [hours(index) for index in range(10)]
    off_grid = [PairedRecord(hours(1) + 60, True, False)]
    with pytest.raises(PairedInferenceError, match="hourly grid"):
        build_paired_fold("2019", eligible, off_grid)
