"""Training-only data access and gates for the append-only P2 Cycle Null V2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .cycle_structure import (
    FIDELITY_REPLICATES,
    PASS,
    REDESIGN,
    FoldDesign,
    evaluate_fidelity,
    fidelity_criteria,
    fidelity_statistics,
)
from .cycle_structure_lab import CycleGrids, build_designs, load_grids, training_observations
from .cycle_structure_v2 import (
    BLOCK_EXPECTED_OBSERVATIONS_V2,
    MINIMUM_LAG_540_SURVIVAL,
    NULL_METHOD_V2,
    NULL_V2_ID,
    STREAM_FIDELITY_V2,
    SUPPORT_LAGS,
    DonorTopology,
    JointLongBlockDesign,
    block_length_distribution,
    build_donor_topology,
    exact_same_block_survival,
    simulate_joint_paths_v2,
)

ROOT = Path(__file__).resolve().parents[3]
V1_PREREGISTRATION = "reports/power/P2-CYCLE-NULL-FIDELITY-PREREGISTRATION-V1.json"
V2_PREREGISTRATION = "reports/power/P2-CYCLE-NULL-V2-PREREGISTRATION.json"
FIDELITY_BATCH_V2 = 111


def normalized_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_donors(grids: CycleGrids) -> tuple[DonorTopology, ...]:
    """Build one raw-return donor topology from each embargoed training prefix."""
    donors = []
    for fold in grids.folds:
        values, eligible = grids.training_segment(fold)
        donors.append(build_donor_topology(fold.fold_id, values, eligible, fold.train_stop))
    return tuple(donors)


def build_joint_design_v2(
    grids: CycleGrids, donors: tuple[DonorTopology, ...]
) -> JointLongBlockDesign:
    """Bind causal stage pools to one complete nested-prefix simulated chronology."""
    bounds = tuple(fold.train_stop for fold in grids.folds)
    if len(donors) != len(bounds):
        raise ValueError("every fold must provide exactly one causal donor topology")
    # The first training prefix is the in-sample calibration stage.  Thereafter each
    # stage uses only the most recent donor prefix already available at its boundary.
    return JointLongBlockDesign(
        lattice=grids.lattice,
        folds=grids.folds,
        donors=donors,
        stage_bounds=(0, *bounds, grids.lattice.slot_count),
        stage_donors=(0, *range(len(donors))),
    )


def _v2_preregistration(root: Path) -> dict[str, Any]:
    record = json.loads((root / V2_PREREGISTRATION).read_text(encoding="utf-8"))
    v1 = json.loads((root / V1_PREREGISTRATION).read_text(encoding="utf-8"))
    if record["criteria"] != v1["criteria"] or record["criteria"] != fidelity_criteria():
        raise ValueError("Null V2 fidelity thresholds differ from immutable Null V1")
    if record["immutable_v1_criterion_artifact"]["sha256"] != normalized_sha256(
        root / V1_PREREGISTRATION
    ):
        raise ValueError("immutable Null V1 criterion hash mismatch")
    if record["null_method"] != NULL_METHOD_V2:
        raise ValueError("Null V2 method differs from its preregistration")
    if record["expected_block_observations"] != BLOCK_EXPECTED_OBSERVATIONS_V2:
        raise ValueError("Null V2 block length differs from its preregistration")
    if record["alternative_block_lengths_tested"]:
        raise ValueError("alternative Null V2 block lengths are forbidden")
    return record


def block_support_report(
    grids: CycleGrids, donors: tuple[DonorTopology, ...], root: Path = ROOT
) -> dict[str, Any]:
    """Measure actual training donor topology before any V2 fidelity simulation."""
    _v2_preregistration(root)
    folds = []
    for donor in donors:
        survival = {
            str(lag): round(exact_same_block_survival(donor, lag), 10) for lag in SUPPORT_LAGS
        }
        folds.append(
            {
                "fold_id": donor.fold_id,
                "contiguous_segment_count": int(donor.segment_lengths.size),
                "contiguous_segment_lengths": donor.segment_lengths.astype(int).tolist(),
                "minimum_segment_length": int(donor.segment_lengths.min()),
                "maximum_segment_length": int(donor.segment_lengths.max()),
                "admissible_donor_starts": int(donor.admissible_starts.size),
                "realized_block_length_distribution": block_length_distribution(donor),
                "same_block_survival_probability": survival,
                "lag540_minimum_required": MINIMUM_LAG_540_SURVIVAL,
                "lag540_pass": survival["540"] >= MINIMUM_LAG_540_SURVIVAL,
            }
        )
    status = PASS if all(item["lag540_pass"] for item in folds) else REDESIGN
    artifact = {
        "schema_version": 1,
        "artifact_id": "P2-CYCLE-NULL-V2-BLOCK-SUPPORT",
        "null_id": NULL_V2_ID,
        "null_method": NULL_METHOD_V2,
        "expected_block_observations": BLOCK_EXPECTED_OBSERVATIONS_V2,
        "canonical_gaps_interpolated": False,
        "donor_blocks_cross_canonical_gaps": False,
        "forced_gap_termination": True,
        "alternative_block_lengths_tested": False,
        "training_only": True,
        "support_measured_before_fidelity": True,
        "fidelity_executed_at_measurement_time": False,
        "survival_lags": list(SUPPORT_LAGS),
        "minimum_lag540_survival_every_fold": MINIMUM_LAG_540_SURVIVAL,
        "folds": folds,
        "preregistration": {
            "artifact": V2_PREREGISTRATION,
            "artifact_sha256": normalized_sha256(root / V2_PREREGISTRATION),
            "method_frozen_before_measurement": True,
        },
        "BLOCK_SUPPORT_STATUS": status,
        "ACTUAL_MARKET_PRIMARY_RESULT_OBSERVED": False,
    }
    return artifact


def fidelity_report_v2(
    grids: CycleGrids, joint: JointLongBlockDesign, block_support: dict[str, Any], root: Path = ROOT
) -> dict[str, Any]:
    """Run unchanged V1 fidelity statistics only after V2 block support passes."""
    preregistration = _v2_preregistration(root)
    if block_support["BLOCK_SUPPORT_STATUS"] != PASS:
        raise ValueError("Null V2 fidelity is blocked by failed donor support")
    observed = {
        fold.fold_id: fidelity_statistics(training_observations(grids, fold))
        for fold in grids.folds
    }
    replicated: dict[str, dict[str, list[float]]] = {
        fold_id: {name: [] for name in values} for fold_id, values in observed.items()
    }
    eligible = grids.lattice.eligible
    for first in range(0, FIDELITY_REPLICATES, FIDELITY_BATCH_V2):
        count = min(FIDELITY_BATCH_V2, FIDELITY_REPLICATES - first)
        values = simulate_joint_paths_v2(joint, STREAM_FIDELITY_V2, first, count)
        for fold in grids.folds:
            segment = values[: fold.train_stop][eligible[: fold.train_stop]]
            for column in range(count):
                for name, value in fidelity_statistics(segment[:, column]).items():
                    replicated[fold.fold_id][name].append(value)
    artifact = evaluate_fidelity(observed, replicated, preregistration["criteria"])
    artifact["artifact_id"] = "P2-CYCLE-NULL-V2-FIDELITY"
    artifact["null_id"] = NULL_V2_ID
    artifact["null_method"] = NULL_METHOD_V2
    artifact["expected_block_observations"] = BLOCK_EXPECTED_OBSERVATIONS_V2
    artifact["raw_returns_resampled_directly"] = True
    artifact["ar_garch_har_figarch_used"] = False
    artifact["alternative_block_lengths_tested"] = False
    artifact["block_support_artifact_sha256"] = normalized_sha256(
        root / "reports/power/P2-CYCLE-NULL-V2-BLOCK-SUPPORT.json"
    )
    artifact["preregistration"] = {
        "artifact": V2_PREREGISTRATION,
        "artifact_sha256": normalized_sha256(root / V2_PREREGISTRATION),
        "thresholds_fixed_before_calculation": True,
        "thresholds_unchanged_from_v1": True,
    }
    artifact["training_segments"] = {
        fold.fold_id: int(eligible[: fold.train_stop].sum()) for fold in grids.folds
    }
    artifact["NULL_V2_FIDELITY_STATUS"] = artifact.pop("NULL_FIDELITY_STATUS")
    return artifact


__all__ = [
    "CycleGrids",
    "FoldDesign",
    "block_support_report",
    "build_designs",
    "build_donors",
    "build_joint_design_v2",
    "fidelity_report_v2",
    "load_grids",
    "normalized_sha256",
]
