"""Execute only the committed WP-008 OLS preregistrations."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.artifacts import write_parquet
from app.research.continuation_lab import PROFILES, ResearchInputs
from app.research.evaluation_protocol import load_protocol, terminal_classification
from app.research.linear_lab import TRIAL_SCHEMA, LinearChallengerLab, parquet_rows
from app.research.runner import deterministic_run_identity, finalize_result, sha256
from app.research.supervised import FEATURE_VERSION, LABEL_VERSION, load_feature_source
from app.research.wp008 import (
    ATTEMPT_PATH,
    OUTCOMES_PATH,
    ROOT_FAMILY,
    SPEC,
    config_path,
    preflight,
    read_json,
)


def atomic_json(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"immutable artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as handle:
        json.dump(payload, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def compact_profiles(profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        profile: {
            "profile": record["profile"],
            "variant": record["variant"],
            "fold_diagnostics": record["fold_diagnostics"],
            "summary": record["summary"],
        }
        for profile, record in profiles.items()
    }


def outcome(experiment_id: str, result: dict[str, Any], result_path: Path) -> dict[str, Any]:
    classification = result["secondary_results"]["terminal_classification"]
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "result_path": result_path.relative_to(ROOT).as_posix(),
        "result_sha256": sha256(result_path),
        "terminal_classification": classification,
        "conclusion": f"Frozen leakage-safe linear walk-forward evaluation: {classification}; no sealed query, Champion, or paper action.",
        "falsified": (
            "Evidence sufficiency was not met; no economic falsification is claimed."
            if classification == "INCONCLUSIVE"
            else "The fixed supervised net-profitability/stability claim failed its predeclared hurdles."
            if classification.startswith("REJECT")
            else "No falsification of exposed development hurdles; this is not independent forward evidence."
        ),
        "not_falsified": "Different labels, features, models, regularization, thresholds, interactions, exits, horizons, assets, and prospective evidence remain untested.",
        "evidence_facts": [
            {"json_pointer": "/primary_result", "expected_value": result["primary_result"]},
            {
                "json_pointer": "/secondary_results/terminal_classification",
                "expected_value": classification,
            },
        ],
        "failure_modes": [classification],
        "legitimate_revisit": "Only under a new explicit cumulative Research Director allocation; do not tune this exposed family after results.",
    }


def main() -> None:
    gate = preflight(ROOT)
    inputs = ResearchInputs.load(ROOT)
    features = load_feature_source(ROOT)
    protocol = load_protocol()
    lab = LinearChallengerLab(inputs, features, protocol)
    atomic_json(
        ROOT / ATTEMPT_PATH,
        {
            **gate,
            "started_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "root_family": ROOT_FAMILY,
            "feature_version": FEATURE_VERSION,
            "label_version": LABEL_VERSION,
            "trial_ids": [
                f"{variant}:{profile}" for variant in SPEC.values() for profile in PROFILES
            ],
        },
    )
    computed = {}
    for experiment_id, variant in SPEC.items():
        print(f"Fitting six declared historical models for {variant}", flush=True)
        computed[experiment_id] = lab.run_configuration(read_json(ROOT / config_path(variant)))
    outcomes = []
    for experiment_id, variant in SPEC.items():
        directory = ROOT / "research/experiments" / experiment_id
        prereg_path = directory / "preregistration.json"
        prereg = read_json(prereg_path)
        execution = computed[experiment_id]
        profiles = execution["profiles"]
        summaries = {name: item["summary"] for name, item in profiles.items()}
        classification = terminal_classification(
            summaries["DEFAULT"], summaries["ZERO"], summaries["DOUBLE"], protocol
        )
        trial_path = directory / "trials.parquet"
        artifact_manifest = write_parquet(
            trial_path,
            [row for profile in PROFILES for row in parquet_rows(profiles[profile])],
            schema=TRIAL_SCHEMA,
            sort_key=("profile", "fold_id", "signal_us"),
            root=ROOT,
        )
        fold_models = [item["model"] | {"fold_id": item["fold_id"]} for item in execution["fits"]]
        training_manifests = [item["training_manifest"] for item in execution["fits"]]
        prediction_diagnostics = [item["validation_diagnostics"] for item in execution["fits"]]
        atomic_json(directory / "artifact-manifest.json", artifact_manifest)
        atomic_json(directory / "training-manifests.json", training_manifests)
        atomic_json(directory / "fold-models.json", fold_models)
        secondary = {
            "profiles": compact_profiles(profiles),
            "terminal_classification": classification,
            "fold_models": fold_models,
            "training_manifests": training_manifests,
            "prediction_diagnostics": prediction_diagnostics,
            "artifact_manifest": artifact_manifest,
            "execution_provenance": {
                **gate,
                "artifact_storage_version": "RESEARCH_ARTIFACT_STORAGE_V1",
                "feature_version": FEATURE_VERSION,
                "label_version": LABEL_VERSION,
                "model_fits": 6,
                "trial_count": 4,
                "stress_profile_refits": 0,
                "feature_searches": 0,
                "hyperparameter_searches": 0,
                "threshold_searches": 0,
            },
        }
        result = {
            "schema_version": 2,
            "experiment_id": experiment_id,
            "experiment_version": 1,
            "preregistration_reference": experiment_id,
            "preregistration_created_at_utc": prereg["created_at_utc"],
            "completed_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "status": "COMPLETED",
            "code_config_reference": prereg["code_config_reference"],
            "dataset": {key: prereg["dataset"][key] for key in ("manifest_id", "content_hash")},
            "seed_reference": [0],
            "primary_result": summaries["DEFAULT"]["metrics"]["net_expectancy_r"],
            "secondary_results": secondary,
            "artifacts": [
                trial_path.relative_to(ROOT).as_posix(),
                (directory / "artifact-manifest.json").relative_to(ROOT).as_posix(),
                (directory / "training-manifests.json").relative_to(ROOT).as_posix(),
                (directory / "fold-models.json").relative_to(ROOT).as_posix(),
            ],
            "validation_outcome": "PASS",
            "interpretation": "EXPOSED DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE. Fixed OLS with training-only scaling and labels; no tuning or validation refit.",
            "trial_accounting": {"declared_budget": 4, "executed_trials": 4},
            "run_identity_hash": deterministic_run_identity(
                prereg,
                gate["execution_commit"],
                {"reference": prereg["code_config_reference"]},
                {
                    "engine": "BACKTEST_ENGINE_V2",
                    "execution": "EXECUTION_MODEL_V2",
                    "cost": "BTCUSDT_SPOT_COST_V1",
                    "model": "NUMPY_FLOAT64_ORDINARY_LEAST_SQUARES_WITH_INTERCEPT",
                },
            ),
        }
        result_path = directory / "result.json"
        finalize_result(result, prereg_path, result_path)
        outcomes.append(outcome(experiment_id, result, result_path))
    outcome_path = ROOT / OUTCOMES_PATH
    if outcome_path.exists():
        raise FileExistsError("immutable WP-008 outcome ledger already exists")
    outcome_path.parent.mkdir(parents=True, exist_ok=True)
    outcome_path.write_text(
        "".join(
            json.dumps(item, separators=(",", ":"), allow_nan=False) + "\n" for item in outcomes
        )
    )
    print("All eight fixed WP-008 profiles finalized; every result retained.", flush=True)


if __name__ == "__main__":
    main()
