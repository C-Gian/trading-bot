"""Version WP-007 preregistrations after a zero-result preflight correction.

The original declarations remain immutable. The correction excludes WP-007's own
admission-ledger records when reproducing the prior-corpus novelty decision and changes
no strategy behaviour, hypothesis, profile, parameter, metric, or protocol.
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
from app.research.wp007 import (
    AMENDMENT_PATH,
    SPEC,
    dependency_manifest,
    executable_spec,
    git,
    read_json,
    validate_admission,
    validate_identity,
)

REASON = (
    "After the original preregistrations and append-only admission ledger were committed, the "
    "clean-tree preflight novelty reproducer compared each WP-007 behaviour against that same "
    "WP-007 ledger and therefore rejected its own already-governed admission as a duplicate. "
    "The reproducer now excludes the exact WP-007 experiment IDs so it evaluates the same prior "
    "corpus used by the committed admission gate. No scientific declaration or executable "
    "strategy behaviour changed."
)
CORRECTION_RECORD = "reports/validation/WP-007-PREFLIGHT-CORRECTION.json"


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
        raise ValueError("commit the corrected preflight on main before versioning")
    validate_admission()
    for experiment_id in SPEC:
        directory = ROOT / "research/experiments" / experiment_id
        if any((directory / name).exists() for name in ("result.json", "trials.json")):
            raise FileExistsError("a WP-007 result exists; prospective correction is forbidden")
    amendments = {}
    created = datetime.now(UTC).isoformat().replace("+00:00", "Z")
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
            "created_at_utc": created,
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
        "kind": "PRE_EXECUTION_NOVELTY_SELF_REFERENCE_CORRECTION",
        "work_package": "WP-007",
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
        "novelty_admission_changed": False,
        "correction_record": CORRECTION_RECORD,
        "amendments": amendments,
    }
    write(AMENDMENT_PATH, registry)
    write(
        CORRECTION_RECORD,
        {
            "schema_version": 1,
            "work_package": "WP-007",
            "status": "PRE_EXECUTION_CORRECTION",
            "detected_before_any_market_result": True,
            "strategy_trials_executed": 0,
            "result_artifacts_finalized": 0,
            "reason": REASON,
            "superseded_documents_preserved": True,
            "registry": AMENDMENT_PATH,
            "scientific_scope_changed": False,
            "recorded_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        },
    )
    print("Both WP-007 preregistrations versioned prospectively; originals preserved.")


if __name__ == "__main__":
    main()
