from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.baselines import FixedBaselineLab
from app.research.runner import (
    deterministic_run_identity,
    finalize_result,
    run_declared_trials,
)

MANIFEST = ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
EXPERIMENTS = (
    "EXP-BASE-001-BUYHOLD",
    "EXP-CTRL-002-RANDOM",
    "EXP-BASE-003-TREND",
    "EXP-BASE-004-BREAKOUT",
    "EXP-CTRL-005-TREND-DELAY-1H",
    "EXP-CTRL-006-NO-TRADE",
)
VERSIONS = {
    "engine": "BACKTEST_ENGINE_V2",
    "execution": "EXECUTION_MODEL_V2",
    "cost": "BTCUSDT_SPOT_COST_V1",
}


def atomic_json(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"immutable artifact exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
        staging = Path(handle.name)
    try:
        os.link(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def aggregate(experiment_id: str, trials: list[dict[str, Any]]) -> tuple[Any, dict[str, Any]]:
    completed = [trial for trial in trials if trial["status"] == "COMPLETED"]
    if len(completed) != len(trials):
        raise RuntimeError("a declared trial failed; preserve trials and stop")
    if experiment_id == "EXP-BASE-001-BUYHOLD":
        metrics = completed[0]["metrics"]
        return metrics["net_total_return"], {
            key: value for key, value in metrics.items() if key != "net_total_return"
        }
    if experiment_id == "EXP-CTRL-002-RANDOM":
        values = np.asarray(
            [trial["metrics"]["net_expectancy_r"] for trial in completed], dtype=float
        )
        return round(float(np.median(values)), 10), {
            "mean_expectancy_r": round(float(np.mean(values)), 10),
            "minimum_expectancy_r": round(float(np.min(values)), 10),
            "maximum_expectancy_r": round(float(np.max(values)), 10),
            "q10_expectancy_r": round(float(np.quantile(values, 0.1, method="linear")), 10),
            "q90_expectancy_r": round(float(np.quantile(values, 0.9, method="linear")), 10),
            "trade_count_distribution": [trial["metrics"]["trade_count"] for trial in completed],
            "unresolved_distribution": [
                trial["metrics"]["unresolved_trades"] for trial in completed
            ],
            "invalid_distribution": [trial["metrics"]["invalid_attempts"] for trial in completed],
        }
    if experiment_id in {"EXP-BASE-003-TREND", "EXP-BASE-004-BREAKOUT"}:
        by_profile = {trial["profile"]: trial["metrics"] for trial in completed}
        return by_profile["DEFAULT"]["net_expectancy_r"], {
            "default_metrics": by_profile["DEFAULT"],
            "zero_cost_metrics": by_profile["ZERO"],
            "double_cost_metrics": by_profile["DOUBLE"],
        }
    metrics = completed[0]["metrics"]
    return metrics["net_expectancy_r"], metrics


def main() -> None:
    gate = json.loads((ROOT / "reports/validation/PRE-EXPERIMENT-GATE-V1.json").read_text())
    if gate["status"] != "PASS":
        raise RuntimeError("pre-experiment gate is not PASS")
    directories = [ROOT / "research/experiments" / experiment_id for experiment_id in EXPERIMENTS]
    if any((directory / "result.json").exists() for directory in directories):
        raise FileExistsError("a finalized result already exists")
    if not all((directory / "preregistration.json").is_file() for directory in directories):
        raise RuntimeError("all six preregistrations must exist before execution")
    lab = FixedBaselineLab()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    completed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    for directory in directories:
        prereg_path = directory / "preregistration.json"
        prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
        trials = run_declared_trials(prereg_path, MANIFEST, lab.run_trial)
        atomic_json(directory / "trials.json", trials)
        primary, secondary = aggregate(prereg["experiment_id"], trials)
        result = {
            "schema_version": 2,
            "experiment_id": prereg["experiment_id"],
            "experiment_version": 1,
            "preregistration_reference": prereg["experiment_id"],
            "preregistration_created_at_utc": prereg["created_at_utc"],
            "completed_at_utc": completed_at,
            "status": "COMPLETED",
            "code_config_reference": prereg["code_config_reference"],
            "dataset": {
                "manifest_id": prereg["dataset"]["manifest_id"],
                "content_hash": prereg["dataset"]["content_hash"],
            },
            "seed_reference": prereg["seeds"],
            "primary_result": primary,
            "secondary_results": secondary,
            "artifacts": [str((directory / "trials.json").relative_to(ROOT)).replace("\\", "/")],
            "validation_outcome": "PASS",
            "interpretation": "Development backtest evidence for a preregistered reference, fixed baseline, or negative control; not approved strategy performance.",
            "trial_accounting": {
                "declared_budget": prereg["trial_budget"],
                "executed_trials": len(trials),
            },
            "run_identity_hash": deterministic_run_identity(
                prereg, commit, {"reference": prereg["code_config_reference"]}, VERSIONS
            ),
        }
        finalize_result(result, prereg_path, directory / "result.json")
    print("Six preregistered baseline/control experiments finalized: PASS")


if __name__ == "__main__":
    main()
