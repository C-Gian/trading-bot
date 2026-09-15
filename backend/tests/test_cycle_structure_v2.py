"""Synthetic-only guards for the append-only P2 Cycle Null V2 redesign.

These tests intentionally never load BTC market data or invoke the V2 lab loaders.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from app.research.cycle_structure import (
    FORBIDDEN_ARTIFACT_KEYS,
    PASS,
    REDESIGN,
    CycleFold,
    CycleLattice,
    PrepModeViolation,
    assert_no_result_leakage,
    fidelity_criteria,
    project,
)
from app.research.cycle_structure_v2 import (
    BLOCK_EXPECTED_OBSERVATIONS_V2,
    BLOCK_LENGTHS_TESTED_V2,
    MINIMUM_LAG_540_SURVIVAL,
    SUPPORT_LAGS,
    DonorTopology,
    JointLongBlockDesign,
    build_donor_topology,
    evaluate_power_gate_v2,
    simulate_joint_paths_v2,
    stationary_raw_return_draw,
)
from app.research.cycle_structure_v2_lab import block_support_report, fidelity_report_v2

ROOT = Path(__file__).resolve().parents[2]
POWER = ROOT / "reports" / "power"
PROTOCOL = ROOT / "research" / "protocols" / "P2-CYCLE-NULL-V2.json"
V2_PREREGISTRATION = POWER / "P2-CYCLE-NULL-V2-PREREGISTRATION.json"
V1_PREREGISTRATION = POWER / "P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json"
V2_MODULE = ROOT / "backend" / "app" / "research" / "cycle_structure_v2.py"
V2_LAB = ROOT / "backend" / "app" / "research" / "cycle_structure_v2_lab.py"
AUDIT = ROOT / "scripts" / "audit_p2_cycle_null_v2.py"
STATE = ROOT / "state" / "current_state.json"
LEDGER = ROOT / "reports" / "statistics" / "MATERIAL-HYPOTHESIS-LEDGER-V1.json"

V1_FROZEN_HASHES = {
    "P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json": (
        "7bc16573c460fb6949b6dffbd8968fabf842d7f5c0a763ec63fc14e1ba5f151a"
    ),
    "P2-CYCLE-NULL-FIDELITY-V1.json": (
        "846abb4344aff653051810dfa2f1bfc535a8423f18f459dab674a3bc94492d02"
    ),
    "P2-CYCLE-COMPUTE-BENCHMARK-V1.json": (
        "81c2c1df0b831ea50269b188dc0bb38a5e672c40d66cee8b7d0e324d068a4d9c"
    ),
    "P2-CYCLE-FOUNDATION-POWER-GATE-V1.json": (
        "664da38072570c24aca09971e9a7c4db91ef4144d52c4795dca2a4f5b27320cb"
    ),
    "P2-CYCLE-FOUNDATION-POWER-GATE-V1.md": (
        "f9d3af4ce7f6da84d0076e13c60e62688f2bebd35a459179854aec082901869f"
    ),
}


class _NoRestartGenerator:
    """A deterministic RNG facade that exposes a gap-boundary termination."""

    def __init__(self) -> None:
        self._starts = iter((2, 4, 0))

    def choice(self, _starts: np.ndarray) -> int:
        return next(self._starts)

    def random(self) -> float:
        return 1.0


def _topology(size: int = 16, gaps: tuple[int, ...] = (3,)) -> DonorTopology:
    values = np.arange(size, dtype=float) / 10.0
    eligible = np.ones(size, dtype=bool)
    eligible[list(gaps)] = False
    values[~eligible] = 0.0
    return build_donor_topology("SYNTHETIC", values, eligible, size)


def _support(status: str = PASS) -> dict[str, str]:
    return {"BLOCK_SUPPORT_STATUS": status}


def _fidelity(status: str = PASS) -> dict[str, str]:
    return {"NULL_V2_FIDELITY_STATUS": status}


def _joint(status: str = PASS) -> dict[str, str]:
    return {"JOINT_REPLICATION_STATUS": status}


def _compute(status: str = PASS) -> dict[str, str]:
    return {"COMPUTATIONAL_STATUS": status}


def _detectability(power: float = 0.8) -> dict[str, object]:
    return {
        "cells": [
            {"period_days": period, "snr": 0.5, "power": power} for period in (3, 7, 14, 30, 60)
        ]
    }


def test_v1_artifacts_are_byte_identical_to_their_frozen_sha256() -> None:
    for name, expected in V1_FROZEN_HASHES.items():
        assert hashlib.sha256((POWER / name).read_bytes()).hexdigest() == expected


def test_v2_method_is_fixed_raw_return_bootstrap_without_model_family_or_alternatives() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    preregistration = json.loads(V2_PREREGISTRATION.read_text(encoding="utf-8"))
    assert BLOCK_EXPECTED_OBSERVATIONS_V2 == 1080
    assert BLOCK_LENGTHS_TESTED_V2 == (1080,)
    for record in (protocol["null_v2"], preregistration):
        assert record["expected_block_observations"] == 1080
        assert record["alternative_block_lengths_tested"] is False
        assert record["ar_garch_har_figarch_used"] is False
    assert protocol["null_v2"]["mean_model"] is None
    assert protocol["null_v2"]["volatility_model"] is None
    source = V2_MODULE.read_text(encoding="utf-8") + V2_LAB.read_text(encoding="utf-8")
    names = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    for forbidden in ("fit_sieve", "SieveModel", "GARCH", "FIGARCH", "HAR"):
        assert forbidden not in names


def test_gap_safe_draw_preserves_raw_values_and_never_bridges_a_gap() -> None:
    topology = _topology()
    values, indices, block_ids, forced = stationary_raw_return_draw(
        _NoRestartGenerator(), topology, 4
    )
    assert forced.tolist() == [False, True, False, False]
    assert indices.tolist() == [2, 4, 5, 6]
    assert np.array_equal(values, topology.values[indices])
    assert set(values).issubset(set(topology.values[topology.eligible]))
    assert not np.any(np.isclose(values, 0.3))  # the missing raw value was not interpolated
    for block in np.unique(block_ids):
        within = indices[block_ids == block]
        assert np.array_equal(np.diff(within), np.ones(max(0, within.size - 1), dtype=int))
        assert np.array_equal(values[block_ids == block], topology.values[within])


def test_block_support_is_measured_before_fidelity_and_requires_lag540_survival() -> None:
    passing = build_donor_topology(
        "LONG", np.arange(4000, dtype=float), np.ones(4000, dtype=bool), 4000
    )
    report = block_support_report(None, (passing,), ROOT)
    assert report["support_measured_before_fidelity"] is True
    assert report["fidelity_executed_at_measurement_time"] is False
    assert report["survival_lags"] == list(SUPPORT_LAGS)
    assert report["folds"][0]["lag540_pass"] is True
    assert report["BLOCK_SUPPORT_STATUS"] == PASS

    failing = _topology(540, ())
    blocked = block_support_report(None, (failing,), ROOT)
    assert blocked["folds"][0]["lag540_pass"] is False
    assert blocked["BLOCK_SUPPORT_STATUS"] == REDESIGN
    assert MINIMUM_LAG_540_SURVIVAL == 0.50
    with pytest.raises(ValueError, match="blocked by failed donor support"):
        fidelity_report_v2(None, None, blocked, ROOT)


def test_v2_thresholds_exactly_reuse_immutable_v1_criteria() -> None:
    v1 = json.loads(V1_PREREGISTRATION.read_text(encoding="utf-8"))
    v2 = json.loads(V2_PREREGISTRATION.read_text(encoding="utf-8"))
    assert v2["thresholds_unchanged_from_v1"] is True
    assert v2["criteria"] == v1["criteria"] == fidelity_criteria()
    assert (
        v2["immutable_v1_criterion_artifact"]["sha256"]
        == hashlib.sha256(V1_PREREGISTRATION.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    )


def test_joint_path_is_one_causal_chronology_with_shared_nested_slots() -> None:
    lattice = CycleLattice(0, 12, np.ones(12, dtype=bool))
    folds = (
        CycleFold("F1", train_stop=4, validation_start=4, validation_stop=8),
        CycleFold("F2", train_stop=8, validation_start=8, validation_stop=12),
    )
    first = build_donor_topology("F1", np.arange(4, dtype=float), np.ones(4, dtype=bool), 4)
    second = build_donor_topology("F2", np.arange(8, dtype=float), np.ones(8, dtype=bool), 8)
    design = JointLongBlockDesign(lattice, folds, (first, second), (0, 4, 8, 12), (0, 0, 1))
    paths = simulate_joint_paths_v2(design, 99, 0, 2)
    assert paths.shape == (12, 2)
    assert design.stage_donors == (0, 0, 1)
    assert design.donor_pool_by_stage[1]["donor_training_stop"] == 4
    assert design.donor_pool_by_stage[2]["donor_training_stop"] == 8
    assert "IDENTICAL_GENERATED_SLOTS" in design.shared_history_handling
    assert "NOT_INDEPENDENT" in design.cross_fold_dependence_handling
    with pytest.raises(PrepModeViolation, match="contains its future"):
        JointLongBlockDesign(lattice, folds, (first, second), (0, 4, 8, 12), (0, 1, 1))


def test_validation_accessor_refuses_real_arrays_and_outcome_keys_are_rejected() -> None:
    with pytest.raises(PrepModeViolation, match="simulated paths only"):
        project(None, np.zeros((2, 1)))
    for key in FORBIDDEN_ARTIFACT_KEYS:
        with pytest.raises(PrepModeViolation, match="forbidden P2 outcome key"):
            assert_no_result_leakage({key: 0.0})


@pytest.mark.parametrize("failed_gate", ("support", "fidelity", "joint", "compute"))
def test_detectability_is_impossible_until_every_prerequisite_passes(failed_gate: str) -> None:
    support = _support(REDESIGN if failed_gate == "support" else PASS)
    fidelity = _fidelity(REDESIGN if failed_gate == "fidelity" else PASS)
    joint = _joint(REDESIGN if failed_gate == "joint" else PASS)
    compute = _compute(REDESIGN if failed_gate == "compute" else PASS)
    gate = evaluate_power_gate_v2(support, fidelity, joint, compute, None)
    assert gate["P2_POWER_GATE_STATUS"] == REDESIGN
    assert gate["detectability"] is None
    with pytest.raises(PrepModeViolation, match="detectability cannot exist"):
        evaluate_power_gate_v2(support, fidelity, joint, compute, _detectability())


def test_detectability_is_accepted_only_after_all_four_v2_gates_pass() -> None:
    gate = evaluate_power_gate_v2(_support(), _fidelity(), _joint(), _compute(), _detectability())
    assert gate["prerequisites_pass"] is True
    assert gate["P2_POWER_GATE_STATUS"] == "READY_FOR_PREREGISTRATION"
    assert gate["detectability"] is not None


def test_v2_protocol_and_accounting_keep_market_results_and_safety_unobserved() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert protocol["fidelity"]["replicates"] == 999
    assert protocol["compute"]["null_replicates"] == 4999
    assert protocol["compute"]["synthetic_replicates_per_cell"] == 2000
    assert protocol["leakage"]["sealed_queries"] == 0
    assert protocol["material_market_experiment_executed"] is False
    assert protocol["real_money"] is False
    assert state["experiments_completed"] == 26
    assert state["adaptive_search"]["sealed_queries"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False
    assert ledger["counts"]["MATERIAL_ECONOMIC_HYPOTHESIS"] == 12
    audit_source = AUDIT.read_text(encoding="utf-8")
    for inaccessible in (
        "actual selected BTC period: NOT_COMPUTED",
        "actual validation powers: NOT_COMPUTED",
        "actual pooled primary statistic: NOT_COMPUTED",
        "actual structural p-value: NOT_COMPUTED",
        "actual cycle classification: NOT_EMITTED",
    ):
        assert inaccessible in audit_source
