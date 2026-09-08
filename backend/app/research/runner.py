from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .records import RecordValidationError, validate_preregistration, validate_result


def deterministic_run_identity(
    prereg: dict[str, Any],
    code_commit: str,
    configuration: dict[str, Any],
    engine_versions: dict[str, str],
) -> str:
    identity = {
        "code_commit": code_commit,
        "dataset": prereg["dataset"],
        "experiment_id": prereg["experiment_id"],
        "experiment_version": prereg["experiment_version"],
        "code_config_reference": prereg["code_config_reference"],
        "seeds": prereg["seeds"],
        "configuration": configuration,
        "models": engine_versions,
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def finalize_result(result: dict[str, Any], preregistration_path: Path, result_path: Path) -> None:
    if result_path.exists():
        raise FileExistsError("finalized result is immutable")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=result_path.parent, delete=False, suffix=".staging"
    ) as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
        staging = Path(handle.name)
    try:
        validate_result(staging, preregistration_path)
        if result_path.exists():
            raise FileExistsError("finalized result is immutable")
        result_path.hardlink_to(staging)
    finally:
        staging.unlink(missing_ok=True)


def run_fixture(
    preregistration_path: Path,
    result_path: Path,
    dataset_manifest_path: Path,
    code_commit: str,
    configuration: dict[str, Any],
    engine_versions: dict[str, str],
    completed_at_utc: str,
    trial_count: int,
    adapter: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    prereg = validate_preregistration(preregistration_path)
    if prereg["status"] not in {"PREREGISTERED", "RUNNING"}:
        raise RecordValidationError("invalid experiment lineage")
    if prereg["code_config_reference"] != configuration.get("reference"):
        raise RecordValidationError("code/config identity mismatch")
    manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    if (
        manifest["manifest_id"] != prereg["dataset"]["manifest_id"]
        or manifest["content_hash"]["value"] != prereg["dataset"]["content_hash"]
    ):
        raise RecordValidationError("manifest identity mismatch")
    if manifest["coverage"]["end"] > "2024-12-31T23:59:00Z":
        raise RecordValidationError("manifest exceeds development cutoff")
    if trial_count > prereg["trial_budget"]:
        raise RecordValidationError("trial budget exceeded")
    output = adapter(configuration)
    result = {
        "schema_version": 2,
        "experiment_id": prereg["experiment_id"],
        "experiment_version": prereg["experiment_version"],
        "preregistration_reference": prereg["experiment_id"],
        "preregistration_created_at_utc": prereg["created_at_utc"],
        "completed_at_utc": completed_at_utc,
        "status": "COMPLETED",
        "code_config_reference": prereg["code_config_reference"],
        "dataset": {
            "manifest_id": prereg["dataset"]["manifest_id"],
            "content_hash": prereg["dataset"]["content_hash"],
        },
        "seed_reference": prereg["seeds"],
        "primary_result": output["primary_result"],
        "secondary_results": output["secondary_results"],
        "artifacts": output.get("artifacts", []),
        "validation_outcome": "PASS",
        "interpretation": "Synthetic fixture validation only; not trading evidence.",
        "trial_accounting": {
            "declared_budget": prereg["trial_budget"],
            "executed_trials": trial_count,
        },
        "run_identity_hash": deterministic_run_identity(
            prereg, code_commit, configuration, engine_versions
        ),
    }
    finalize_result(result, preregistration_path, result_path)
    return result
