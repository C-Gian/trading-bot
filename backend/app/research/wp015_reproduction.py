"""Fixed local reproduction adapter for the already-exposed WP-015 result.

This module does not finalize experiments or update project state.  Every generated
artifact is written below the caller-provided, gitignored runtime directory.
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
from .funding import MANIFEST_PATH, load_funding_context
from .local_runner import RunContext
from .supervised import load_feature_source
from .wp015 import (
    CONTROL_VARIANT,
    PREDICTION_TOLERANCE,
    PRIMARY_VARIANT,
    VARIANTS,
    dependency_manifest,
    load_protocol,
    load_walk_forward,
    validate_admission,
    validate_allocation,
    validate_preregistrations,
)
from .wp015_lab import (
    PREDICTION_SCHEMA,
    TRIAL_SCHEMA,
    FundingContextLab,
    parquet_rows,
)

REQUIRED_DATASETS = (
    "data/canonical/BTCUSDT-1m.parquet",
    "data/derived/BTCUSDT-1h.parquet",
    "data/derived/BTCUSDT-4h.parquet",
    "data/derived/BTCUSDT-1h-orderflow-v1.parquet",
    "data/derived/BTCUSDT-4h-orderflow-v1.parquet",
    "data/derived/BTCUSDT-USDM-settled-funding-v1.parquet",
    "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
    "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json",
    "data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json",
    "data/raw/funding/binance-usdm/BTCUSDT/page-0001-00b33292b02f2ad6.json",
    "data/raw/funding/binance-usdm/BTCUSDT/page-0002-a5ba7929e65b7d33.json",
    "data/raw/funding/binance-usdm/BTCUSDT/page-0003-cdcc7512d3b47cc3.json",
    "data/raw/funding/binance-usdm/BTCUSDT/page-0004-cd25f8d1e43463eb.json",
    "data/raw/funding/binance-usdm/BTCUSDT/page-0005-2796aa02b3ee64c7.json",
    "data/raw/funding/binance-usdm/BTCUSDT/page-0006-1b344dd6a17bf0a7.json",
    "data/raw/funding/binance-usdm/BTCUSDT/page-0007-af8642be5fe1a107.json",
)
EVIDENCE_TYPE = "REPRODUCTION_OF_ALREADY_EXPOSED_DEVELOPMENT_RESULT"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProgressFundingContextLab(FundingContextLab):
    """Reports a fold only after the frozen primary fold fit has completed."""

    dependencies: list[dict[str, str]]

    def __init__(self, *args: Any, progress: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._progress = progress

    def fit_fold(self, variant: str, fold: dict[str, Any]) -> Any:
        fitted = super().fit_fold(variant, fold)
        year = str(fold["fold_id"]).removeprefix("DEV-")
        position = list(range(2020, 2025)).index(int(year))
        if variant == PRIMARY_VARIANT:
            self._progress(
                f"FOLD_{year}",
                12 + position * 8,
                f"Fold primario {year} completato",
            )
        else:
            self._progress(
                f"FOLD_{year}",
                50 + position * 6,
                f"Fold di controllo {year} completato",
            )
        return fitted


def _comparison(results: dict[str, Any], protocol: dict[str, Any], walk: dict[str, Any]) -> dict:
    output: dict[str, Any] = {
        "schema_version": 1,
        "work_package": "WP-015-LOCAL-REPRODUCTION",
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
        "default_net_expectancy_difference_r": (
            primary["primary_result"] - control["primary_result"]
        ),
        "eligible_universe_matched": True,
        "executed_trade_sets_paired": False,
    }
    return output


def _reconcile(
    context: RunContext, trials: Path, predictions: Path, comparison: Path
) -> dict[str, Any]:
    output = context.run_dir / "artifacts/reconciliation.json"
    command = [
        sys.executable,
        str(context.root / "scripts/reconcile_wp015.py"),
        "--trials-path",
        str(trials),
        "--predictions-path",
        str(predictions),
        "--comparison-path",
        str(comparison),
        "--output-path",
        str(output),
    ]
    completed = subprocess.run(
        command,
        cwd=context.root,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    (context.run_dir / "artifacts/reconciliation.log").write_text(
        completed.stdout + completed.stderr,
        encoding="utf-8",
        newline="\n",
    )
    if completed.returncode != 0 or not output.is_file():
        raise RuntimeError("independent WP-015 reconciliation failed; see local run log")
    result = json.loads(output.read_text(encoding="utf-8"))
    if result.get("status") != "PASS" or result.get("independent_of_primary_runner") is not True:
        raise RuntimeError("independent WP-015 reconciliation did not pass")
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


def _assert_known_result_match(root: Path, reproduced: dict[str, Any]) -> str:
    path = root / "reports/research/WP-015-COMPARISON.json"
    known = json.loads(path.read_text(encoding="utf-8"))
    for variant in VARIANTS:
        actual = reproduced["configurations"][variant]
        expected = known["configurations"][variant]
        if abs(actual["primary_result"] - expected["primary_result"]) > PREDICTION_TOLERANCE:
            raise RuntimeError(f"{variant} does not reproduce the committed primary result")
        for profile in PROFILES:
            actual_profile = actual["profiles"][profile]
            expected_profile = expected["profiles"][profile]
            for metric in ("net_expectancy_r", "cumulative_net_r"):
                gap = abs(actual_profile["metrics"][metric] - expected_profile["metrics"][metric])
                if gap > PREDICTION_TOLERANCE:
                    raise RuntimeError(
                        f"{variant}/{profile}/{metric} differs from committed WP-015"
                    )
            if (
                actual_profile["metrics"]["trade_count"]
                != expected_profile["metrics"]["trade_count"]
            ):
                raise RuntimeError(f"{variant}/{profile} trade count differs from WP-015")
    return _sha256(path)


def _reproduction_preflight(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate the frozen gate while permitting its already-finalized result records."""
    protocol = load_protocol(root)
    walk = load_walk_forward(root)
    validate_admission(root)
    validate_allocation(root)
    validate_preregistrations(root)
    for relative in (
        "reports/validation/WP-015-FUNDING-INTEGRITY.json",
        "reports/validation/WP-015-FUNDING-ASOF-AUDIT.json",
        "reports/validation/WP-015-MODEL-RECONCILIATION.json",
    ):
        document = json.loads((root / relative).read_text(encoding="utf-8"))
        if document.get("status") != "PASS":
            raise RuntimeError(f"frozen WP-015 validation is not PASS: {relative}")
    return protocol, walk


def run_wp015_reproduction(context: RunContext) -> dict[str, Any]:
    """Recompute the fixed primary/control and independently reconcile runtime outputs."""
    state_path = context.root / "state/current_state.json"
    state_before = state_path.read_bytes()
    context.progress("VALIDATING_INPUTS", 7, "Controllo preregistrazione e identità dati")
    protocol, walk = _reproduction_preflight(context.root)
    funding_manifest = json.loads((context.root / MANIFEST_PATH).read_text(encoding="utf-8"))

    lab = ProgressFundingContextLab(
        ResearchInputs.load(context.root),
        load_feature_source(context.root),
        load_funding_context(context.root),
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

    context.progress("COST_STRESS", 80, "Profili ZERO, DEFAULT, DOUBLE e DELAY completati")
    artifact_dir = context.run_dir / "artifacts"
    trials_path = artifact_dir / "WP-015-funding-trials.parquet"
    predictions_path = artifact_dir / "WP-015-funding-predictions.parquet"
    comparison_path = artifact_dir / "WP-015-comparison.json"
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

    context.progress("RECONCILIATION", 86, "Ricostruzione indipendente in corso")
    reconciliation = _reconcile(context, trials_path, predictions_path, comparison_path)
    committed_result_hash = _assert_known_result_match(context.root, comparison)
    context.progress("FINALIZING", 96, "Preparazione del riepilogo per review")

    primary = comparison["configurations"][PRIMARY_VARIANT]
    control = comparison["configurations"][CONTROL_VARIANT]
    profiles = primary["profiles"]
    default = profiles["DEFAULT"]
    metrics = default["metrics"]
    stability = default["stability"]
    fold_summary = [
        {
            "fold_id": item["fold_id"],
            "expectancy_r": item["metrics"]["net_expectancy_r"],
            "trades": item["metrics"]["trade_count"],
        }
        for item in default["folds"]
    ]
    dataset_identities = {
        "spot_manifest_id": "BTCUSDT-SPOT-1M-DEV-v1",
        "spot_content_sha256": "02168b73d8513d825978cdde3cc133e466b4aebcc0aaa48fecfb473de6e3acb2",
        "funding_manifest_id": funding_manifest["manifest_id"],
        "funding_canonical_sha256": funding_manifest["canonical"]["file_sha256"],
        "funding_manifest_sha256": _sha256(context.root / MANIFEST_PATH),
    }
    if state_path.read_bytes() != state_before:
        raise RuntimeError("canonical scientific state changed during local reproduction")
    return {
        "candidate_id": context.candidate.candidate_id,
        "run_id": context.run_id,
        "status": "COMPLETED",
        "classification": primary["terminal_classification"],
        "verdict": "RIPRODUZIONE CONCILIATA" if reconciliation["status"] == "PASS" else "FALLITA",
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
        "dataset_identities": dataset_identities,
        "fold_summary": fold_summary,
        "cost_stress": {
            "ZERO": profiles["ZERO"]["metrics"]["net_expectancy_r"],
            "DEFAULT": metrics["net_expectancy_r"],
            "DOUBLE": profiles["DOUBLE"]["metrics"]["net_expectancy_r"],
            "DELAY_1H": profiles["DELAY_1H"]["metrics"]["net_expectancy_r"],
        },
        "warnings": [
            "REPRODUCTION ONLY",
            "NOT A NEW EXPERIMENT",
            "DOES NOT CHANGE SCIENTIFIC COUNTERS",
            "DOES NOT CREATE SEALED EVIDENCE",
        ],
        "runtime_artifact_hashes": {
            "trials_sha256": _sha256(trials_path),
            "predictions_sha256": _sha256(predictions_path),
            "comparison_sha256": _sha256(comparison_path),
            "committed_wp015_comparison_sha256": committed_result_hash,
        },
    }


__all__ = ["EVIDENCE_TYPE", "REQUIRED_DATASETS", "run_wp015_reproduction"]
