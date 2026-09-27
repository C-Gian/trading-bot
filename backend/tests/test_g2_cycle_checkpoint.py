"""G2 Cycle Causality Checkpoint V1 section 13: the thirteen method tests on the G2 adapter.

The full-size white-noise/coherent/additive gates run in `scripts/build_g2_validation.py`; here the
same functions run with their frozen fixtures, and the gate paths are checked per path against the
frozen G1 quality-gate artifact (identical implementation => identical occupancy).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.g1 import cycle_quality_gate as gate
from app.g1.cycle import SCALES
from app.g2 import cycle_checkpoint as checkpoint

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "test",
    [
        checkpoint.t01_parity,
        checkpoint.t05_linear_trend,
        checkpoint.t06_isolated_jump,
        checkpoint.t07_varying_frequency,
        checkpoint.t08_prefix_invariance,
        checkpoint.t09_gap_reset,
        checkpoint.t10_projection_amplitude,
        checkpoint.t11_period_stability,
        checkpoint.t12_turn_confirmation,
        checkpoint.t13_replay_speed_identity,
    ],
)
def test_checkpoint_method_test(test):
    result = test()
    assert result["pass"], json.dumps(result, default=str)[:2000]


def test_additive_noise_fixture_is_finite_and_labelled():
    result = checkpoint.t04_additive_noise(paths=4)
    assert result["pass"] and result["abstained_bars_total"] > 0
    for scale in result["scales"].values():
        assert scale["finite"] and scale["explicit_quality_label_every_bar"]


def test_gate_paths_reproduce_the_frozen_g1_gate_artifact_exactly():
    artifact = json.loads(
        (ROOT / "reports/research/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.json").read_text(
            encoding="utf-8"
        )
    )
    for i, scale in enumerate(SCALES):
        recorded = artifact["scales"][i]
        assert recorded["nominal_scale"] == scale.nominal
        for p in range(2):
            rows = checkpoint.feed(i, gate.noise_series(i, scale, p))
            occupancy = checkpoint.occupancy(scale, rows, gate.EVALUATED_BARS)
            assert occupancy == recorded["paths"]["white_noise"][p]["usable_occupancy"]
            rows = checkpoint.feed(i, gate.cycle_series(i, scale, p, False))
            occupancy = checkpoint.occupancy(scale, rows, gate.EVALUATED_BARS)
            assert occupancy == recorded["paths"]["clean_cycle"][p]["usable_occupancy"]
