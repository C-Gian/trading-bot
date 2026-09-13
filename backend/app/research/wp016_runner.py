"""Fixed owner-initiated adapter for the preregistered WP-016 experiment.

Importing this module does not execute research. Runtime artifacts are written only
below the caller-provided gitignored run directory; canonical state is read-only.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .artifacts import write_parquet
from .continuation_lab import PROFILES, ResearchInputs
from .evaluation_protocol import terminal_classification
from .funding import MANIFEST_PATH as FUNDING_MANIFEST_PATH
from .funding import load_funding_context
from .local_runner import RunContext
from .supervised import load_feature_source
from .wikimedia import MANIFEST_PATH as ATTENTION_MANIFEST_PATH
from .wikimedia import load_attention_context
from .wp016 import (
    CONTROL_VARIANT,
    PRIMARY_VARIANT,
    VARIANTS,
    dependency_manifest,
    load_protocol,
    load_walk_forward,
    preflight,
)
from .wp016_lab import PREDICTION_SCHEMA, TRIAL_SCHEMA, AttentionContextLab, parquet_rows

EVIDENCE_TYPE = "NEW_PREREGISTERED_DEVELOPMENT_EXPERIMENT_RESULT_PENDING_REVIEW"
REQUIRED_DATASETS = (
    "data/canonical/BTCUSDT-1m.parquet",
    "data/derived/BTCUSDT-1h.parquet",
    "data/derived/BTCUSDT-4h.parquet",
    "data/derived/BTCUSDT-1h-orderflow-v1.parquet",
    "data/derived/BTCUSDT-4h-orderflow-v1.parquet",
    "data/derived/BTCUSDT-USDM-settled-funding-v1.parquet",
    "data/derived/WIKIMEDIA-enwiki-Bitcoin-pageviews-daily-v1.parquet",
    "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
    "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json",
    FUNDING_MANIFEST_PATH,
    ATTENTION_MANIFEST_PATH,
)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProgressAttentionContextLab(AttentionContextLab):
    """Reports deterministic progress only after a real fold fit completes."""

    dependencies: list[dict[str, str]]

    def __init__(self, *args: Any, progress: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._progress = progress

    def fit_fold(self, variant: str, fold: dict[str, Any]) -> Any:
        fitted = super().fit_fold(variant, fold)
        year = str(fold["fold_id"]).removeprefix("DEV-")
        position = list(range(2020, 2025)).index(int(year))
        base, step, label = (
            (12, 7, "primario") if variant == PRIMARY_VARIANT else (48, 6, "controllo")
        )
        self._progress(f"FOLD_{year}", base + position * step, f"Fold {label} {year} completato")
        return fitted


def _comparison(results: dict[str, Any], protocol: dict[str, Any], walk: dict[str, Any]) -> dict:
    output: dict[str, Any] = {
        "schema_version": 1,
        "work_package": "WP-016-OWNER-INITIATED-RUN",
        "protocol_id": protocol["protocol_id"],
        "model_version": protocol["model_version"],
        "primary_variant": PRIMARY_VARIANT,
        "control_variant": CONTROL_VARIANT,
        "configurations": {},
    }
    for variant in VARIANTS:
        summaries = {
            profile: results[variant]["profiles"][profile]["summary"] for profile in PROFILES
        }
        output["configurations"][variant] = {
            "primary_result": summaries["DEFAULT"]["metrics"]["net_expectancy_r"],
            "terminal_classification": terminal_classification(
                summaries["DEFAULT"], summaries["ZERO"], summaries["DOUBLE"], walk
            ),
            "profiles": {
                profile: {
                    "metrics": summaries[profile]["metrics"],
                    "stability": summaries[profile]["stability"],
                    "diagnostics": summaries[profile]["diagnostics"],
                    "folds": summaries[profile]["folds"],
                }
                for profile in PROFILES
            },
            "prediction_diagnostics": results[variant]["prediction_diagnostics"],
            "model_fits": results[variant]["model_fits"],
        }
    primary = output["configurations"][PRIMARY_VARIANT]
    control = output["configurations"][CONTROL_VARIANT]
    output["primary_vs_control"] = {
        "default_net_expectancy_difference_r": primary["primary_result"]
        - control["primary_result"],
        "eligible_universe_matched": True,
        "executed_trade_sets_paired": False,
    }
    return output


def _reconcile(
    context: RunContext,
    trials: Path,
    predictions: Path,
    comparison: Path,
    models: Path,
) -> dict:
    output = context.run_dir / "artifacts/reconciliation.json"
    command = [
        sys.executable,
        str(context.root / "scripts/reconcile_wp016.py"),
        "--trials-path",
        str(trials),
        "--predictions-path",
        str(predictions),
        "--comparison-path",
        str(comparison),
        "--models-path",
        str(models),
        "--output-path",
        str(output),
    ]
    completed = subprocess.run(
        command, cwd=context.root, check=False, capture_output=True, text=True, shell=False
    )
    log = context.run_dir / "artifacts/reconciliation.log"
    log.write_text(completed.stdout + completed.stderr, encoding="utf-8", newline="\n")
    if completed.returncode != 0 or not output.is_file():
        raise RuntimeError("independent WP-016 reconciliation failed; see local run log")
    result = json.loads(output.read_text(encoding="utf-8"))
    if result.get("status") != "PASS" or result.get("independent_of_primary_runner") is not True:
        raise RuntimeError("independent WP-016 reconciliation did not pass")
    return result


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )
    return completed.stdout.strip()


def run_wp016_attention(context: RunContext) -> dict[str, Any]:
    """Run the one frozen experiment only after an explicit owner API request."""
    state_path = context.root / "state/current_state.json"
    state_before = state_path.read_bytes()
    context.progress("VALIDATING_INPUTS", 7, "Controllo preregistrazione e identità dati")
    gate = preflight(context.root)
    if gate["market_results_observed"] != 0 or gate["model_fits_executed"] != 0:
        raise RuntimeError("WP-016 preparation gate is not result-free")
    protocol, walk = load_protocol(context.root), load_walk_forward(context.root)
    funding_manifest = json.loads((context.root / FUNDING_MANIFEST_PATH).read_text("utf-8"))
    attention_manifest = json.loads((context.root / ATTENTION_MANIFEST_PATH).read_text("utf-8"))

    lab = ProgressAttentionContextLab(
        ResearchInputs.load(context.root),
        load_feature_source(context.root),
        load_funding_context(context.root),
        load_attention_context(context.root),
        walk,
        progress=context.progress,
    )
    lab.dependencies = dependency_manifest(context.root)
    results: dict[str, Any] = {}
    trial_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        results[variant] = lab.run_configuration(variant)
        prediction_rows.extend(results[variant]["prediction_records"])
        for profile in PROFILES:
            trial_rows.extend(parquet_rows(results[variant]["profiles"][profile]))

    context.progress("COST_STRESS", 79, "Profili ZERO, DEFAULT, DOUBLE e DELAY completati")
    artifact_dir = context.run_dir / "artifacts"
    trials_path = artifact_dir / "WP-016-attention-trials.parquet"
    predictions_path = artifact_dir / "WP-016-attention-predictions.parquet"
    comparison_path = artifact_dir / "WP-016-comparison.json"
    models_path = artifact_dir / "WP-016-fold-models.json"
    write_parquet(
        trials_path,
        trial_rows,
        schema=TRIAL_SCHEMA,
        sort_key=["variant", "profile", "signal_us"],
        root=context.run_dir,
    )
    write_parquet(
        predictions_path,
        prediction_rows,
        schema=PREDICTION_SCHEMA,
        sort_key=["variant", "fold_id", "signal_us"],
        root=context.run_dir,
    )
    comparison = _comparison(results, protocol, walk)
    _write_json(comparison_path, comparison)
    _write_json(
        models_path,
        {
            "schema_version": 1,
            "fold_models": {variant: results[variant]["folds"] for variant in VARIANTS},
        },
    )

    context.progress("RECONCILIATION", 87, "Ricostruzione indipendente in corso")
    reconciliation = _reconcile(
        context, trials_path, predictions_path, comparison_path, models_path
    )
    context.progress("FINALIZING", 96, "Preparazione del riepilogo per review")
    if state_path.read_bytes() != state_before:
        raise RuntimeError("canonical scientific state changed during owner-initiated run")

    primary = comparison["configurations"][PRIMARY_VARIANT]
    control = comparison["configurations"][CONTROL_VARIANT]
    profiles = primary["profiles"]
    default = profiles["DEFAULT"]
    metrics, stability = default["metrics"], default["stability"]
    return {
        "candidate_id": context.candidate.candidate_id,
        "run_id": context.run_id,
        "status": "COMPLETED",
        "classification": primary["terminal_classification"],
        "verdict": "RISULTATO DI SVILUPPO PRONTO PER REVIEW",
        "default_expectancy_r": metrics["net_expectancy_r"],
        "zero_cost_expectancy_r": profiles["ZERO"]["metrics"]["net_expectancy_r"],
        "double_cost_expectancy_r": profiles["DOUBLE"]["metrics"]["net_expectancy_r"],
        "delay_expectancy_r": profiles["DELAY_1H"]["metrics"]["net_expectancy_r"],
        "trade_count": metrics["trade_count"],
        "nonnegative_folds": stability["nonnegative_fold_count"],
        "fold_count": stability["populated_fold_count"],
        "minimum_fold_trades": default["diagnostics"]["minimum_fold_trades"],
        "control_default_expectancy_r": control["primary_result"],
        "primary_minus_control_r": comparison["primary_vs_control"][
            "default_net_expectancy_difference_r"
        ],
        "oos_correlation": primary["prediction_diagnostics"]["pooled_prediction_label_pearson"],
        "reconciliation_status": reconciliation["status"],
        "scientific_evidence_type": EVIDENCE_TYPE,
        "code_head": _git_head(context.root),
        "dataset_identities": {
            "spot_manifest_id": "BTCUSDT-SPOT-1M-DEV-v1",
            "funding_manifest_id": funding_manifest["manifest_id"],
            "funding_logical_sha256": funding_manifest["canonical"]["logical_sha256"],
            "attention_manifest_id": attention_manifest["manifest_id"],
            "attention_logical_sha256": attention_manifest["canonical"]["logical_sha256"],
        },
        "fold_summary": [
            {
                "fold_id": item["fold_id"],
                "expectancy_r": item["metrics"]["net_expectancy_r"],
                "trades": item["metrics"]["trade_count"],
            }
            for item in default["folds"]
        ],
        "cost_stress": {
            profile: profiles[profile]["metrics"]["net_expectancy_r"] for profile in PROFILES
        },
        "warnings": [
            "NEW PREREGISTERED DEVELOPMENT EXPERIMENT",
            "OWNER INITIATED LOCAL EXECUTION",
            "NOT SEALED EVIDENCE",
            "REQUIRES RESEARCH DIRECTOR REVIEW",
        ],
        "new_experiment": True,
        "runtime_artifact_hashes": {
            "trials_sha256": _sha256(trials_path),
            "predictions_sha256": _sha256(predictions_path),
            "comparison_sha256": _sha256(comparison_path),
            "fold_models_sha256": _sha256(models_path),
            "reconciliation_sha256": _sha256(context.run_dir / "artifacts/reconciliation.json"),
        },
    }


__all__ = ["EVIDENCE_TYPE", "REQUIRED_DATASETS", "run_wp016_attention"]
