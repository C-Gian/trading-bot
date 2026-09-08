from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[3]


class RecordValidationError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RecordValidationError(f"record does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_schema(record: dict[str, Any], schema_name: str) -> None:
    schema = _load(ROOT / "contracts" / schema_name)
    try:
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
            record
        )
    except jsonschema.ValidationError as exc:
        raise RecordValidationError(exc.message) from exc


def validate_preregistration(path: Path) -> dict[str, Any]:
    record = _load(path)
    _validate_schema(record, "experiment_preregistration.schema.json")
    if record["dataset"]["maximum_timestamp"] > "2024-12-31T23:59:00Z":
        raise RecordValidationError("dataset exceeds development cutoff")
    return record


def validate_result(result_path: Path, preregistration_path: Path) -> dict[str, Any]:
    result = _load(result_path)
    prereg = validate_preregistration(preregistration_path)
    _validate_schema(result, "experiment_result.schema.json")
    pairs = (
        ("experiment_id", "experiment_id"),
        ("experiment_version", "experiment_version"),
        ("preregistration_created_at_utc", "created_at_utc"),
        ("code_config_reference", "code_config_reference"),
    )
    if result["preregistration_reference"] != prereg["experiment_id"]:
        raise RecordValidationError("preregistration reference mismatch")
    for result_key, prereg_key in pairs:
        if result[result_key] != prereg[prereg_key]:
            raise RecordValidationError(f"immutable identity mismatch: {result_key}")
    if (
        result["dataset"]["manifest_id"] != prereg["dataset"]["manifest_id"]
        or result["dataset"]["content_hash"] != prereg["dataset"]["content_hash"]
    ):
        raise RecordValidationError("dataset identity mismatch")
    created = datetime.fromisoformat(prereg["created_at_utc"])
    completed = datetime.fromisoformat(result["completed_at_utc"])
    if completed < created:
        raise RecordValidationError("result predates preregistration")
    accounting = result["trial_accounting"]
    if (
        accounting["declared_budget"] != prereg["trial_budget"]
        or accounting["executed_trials"] > prereg["trial_budget"]
    ):
        raise RecordValidationError("trial budget mismatch or exceeded")
    if not set(result["seed_reference"]).issubset(prereg["seeds"]):
        raise RecordValidationError("seed identity mismatch")
    if set(result["secondary_results"]) != set(prereg["metrics"]["secondary"]):
        raise RecordValidationError("secondary result declarations mismatch")
    return result
