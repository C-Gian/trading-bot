"""Version the WP-006 preregistrations prospectively before any market result exists.

The original documents are preserved unchanged. The correction adds no variant, no
profile, no seed and no numeric search; it only rebinds the frozen executable-spec
identity to the corrected validator. Zero strategy trials and zero results preceded it.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.records import validate_preregistration
from app.research.runner import declared_content_identity, sha256
from app.research.search_memory_v2 import bind_executable_spec, derived_fingerprint
from app.research.wp006 import (
    AMENDMENT_PATH,
    SPEC,
    dependency_manifest,
    executable_spec,
    git,
    read_json,
    validate_identity,
)

REASON = (
    "The original preregistrations embedded the typed executable spec as JSON while the "
    "identity validator compared it against the in-memory dataclass form, so tuple and list "
    "serialization differed and the binding could never verify. The validator now compares "
    "through one canonical JSON round trip and also pins the structural and dependency hashes. "
    "Correcting the validator changed its own file hash, so the frozen dependency manifest had "
    "to be re-frozen; the scientific declaration itself is unchanged."
)
CORRECTION_RECORD = "reports/validation/WP-006-PREEXECUTION-CORRECTION.json"


def write(relative: str, payload: dict) -> Path:
    path = ROOT / relative
    if path.exists():
        raise FileExistsError(f"immutable record already exists: {relative}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return path


def main() -> None:
    if git("status", "--porcelain") or git("branch", "--show-current") != "main":
        raise ValueError("commit the corrected validator on main before versioning")
    for experiment_id in SPEC:
        directory = ROOT / "research/experiments" / experiment_id
        if any((directory / name).exists() for name in ("result.json", "trials.json")):
            raise FileExistsError("a WP-006 result already exists; prospective versioning is over")
    amendments = {}
    for experiment_id, variant in SPEC.items():
        directory = ROOT / "research/experiments" / experiment_id
        superseded = directory / "preregistration.json"
        original = read_json(superseded)
        spec = executable_spec(variant)
        binding = bind_executable_spec(spec, declared_fingerprint=derived_fingerprint(spec))
        space = dict(original["parameter_space"])
        space.update(
            executable_spec=json.loads(json.dumps(spec.to_dict())),
            executable_spec_fingerprint=json.loads(json.dumps(derived_fingerprint(spec))),
            executable_spec_hash=binding.executable_spec_hash,
            behavior_hash=binding.behavior_hash,
            structural_hash=binding.structural_hash,
            dependency_hash=binding.dependency_hash,
            dependencies=dependency_manifest(),
            implementation_commit=git("rev-parse", "HEAD"),
            superseded_preregistration_sha256=sha256(superseded),
            supersession_reason=REASON,
        )
        strategy = ROOT / space["strategy_path"]
        effective = {
            **original,
            "experiment_version": 2,
            "created_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "parameter_space": space,
            "code_config_reference": declared_content_identity(strategy, space["trial_plan"]),
        }
        validate_identity(effective)
        path = write(f"research/experiments/{experiment_id}/preregistration.v2.json", effective)
        validate_preregistration(path)
        amendments[experiment_id] = {
            "superseded_path": superseded.relative_to(ROOT).as_posix(),
            "superseded_sha256": sha256(superseded),
            "effective_path": path.relative_to(ROOT).as_posix(),
            "effective_sha256": sha256(path),
        }
    registry = {
        "schema_version": 1,
        "kind": "PRE_EXECUTION_IDENTITY_BINDING_CORRECTION",
        "work_package": "WP-006",
        "reason": REASON,
        "strategy_trials_before_amendment": 0,
        "results_observed_before_amendment": 0,
        "additional_strategy_variants": 0,
        "additional_profile_trials": 0,
        "additional_numeric_parameter_variants": 0,
        "hypothesis_changed": False,
        "primary_metric_changed": False,
        "primary_variant_changed": False,
        "evaluation_protocol_changed": False,
        "correction_record": CORRECTION_RECORD,
        "amendments": amendments,
    }
    write(AMENDMENT_PATH, registry)
    write(
        CORRECTION_RECORD,
        {
            "schema_version": 1,
            "work_package": "WP-006",
            "status": "PRE_EXECUTION_CORRECTION",
            "detected_before_any_market_result": True,
            "strategy_trials_executed": 0,
            "result_artifacts_finalized": 0,
            "reason": REASON,
            "superseded_documents_preserved": True,
            "registry": AMENDMENT_PATH,
            "recorded_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )
    print("Both WP-006 preregistrations versioned prospectively; originals preserved.")


if __name__ == "__main__":
    main()
