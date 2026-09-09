"""One explicit zero-trial source-integrity correction; never edits original preregistrations."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.records import validate_preregistration
from app.research.runner import declared_content_identity, sha256
from app.research.wp004 import (
    SPEC,
    dependency_manifest,
    git,
    validate_historical_identity,
    validate_identity,
)


def main() -> None:
    if git("status", "--porcelain"):
        raise ValueError("commit corrected implementation before v2 preregistration")
    registry_path = ROOT / "research/protocols/WP-004-PREEXECUTION-AMENDMENTS.json"
    if registry_path.exists() or (ROOT / "research/runs/WP-004-ATTEMPT.json").exists():
        raise ValueError("amendment already exists or strategy execution has begun")
    if any((ROOT / f"research/experiments/{eid}/trials.json").exists() for eid in SPEC):
        raise ValueError("observed trials cannot be amended")
    abort_path = "reports/validation/WP-004-PREEXECUTION-ABORT.json"
    abort = json.loads((ROOT / abort_path).read_text())
    if abort["strategy_conditions_computed"] != 0 or abort["profile_trials_attempted"] != 0:
        raise ValueError("only a zero-trial data admission correction is authorized")
    registry = {
        "schema_version": 1,
        "kind": "PRE_EXECUTION_DATA_INTEGRITY_CORRECTION",
        "authority": "decisions/ADR-0005-PREEXECUTION-SOURCE-GRID-QUARANTINE.md",
        "abort_record": abort_path,
        "abort_record_sha256": sha256(ROOT / abort_path),
        "strategy_trials_before_amendment": 0,
        "additional_strategy_variants": 0,
        "additional_profile_trials": 0,
        "amendments": {},
    }
    features_path = ROOT / "research/protocols/CONTINUATION_FEATURES_V2.json"
    for eid in SPEC:
        directory = ROOT / "research/experiments" / eid
        old_path = directory / "preregistration.json"
        previous = validate_preregistration(old_path)
        validate_historical_identity(previous)
        record = deepcopy(previous)
        record["experiment_version"] = 2
        record["created_at_utc"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        space = record["parameter_space"]
        space["implementation_commit"] = git("rev-parse", "HEAD")
        space["dependencies"] = dependency_manifest()
        space["strategy_sha256"] = sha256(ROOT / space["strategy_path"])
        space["feature_definitions"] = json.loads(features_path.read_text())
        space["feature_definitions_sha256"] = sha256(features_path)
        space["source_grid_expected"] = json.loads(
            (ROOT / "reports/validation/WP-004-SOURCE-GRID.json").read_text()
        )
        space["pre_execution_correction"] = {
            "authority": registry["authority"],
            "superseded_path": old_path.relative_to(ROOT).as_posix(),
            "superseded_sha256": sha256(old_path),
            "abort_record": abort_path,
            "strategy_trials_before_amendment": 0,
        }
        record["leakage_controls"].append(space["feature_definitions"]["source_grid_quarantine"])
        for item in space["trial_plan"]:
            item["config_sha256"] = sha256(ROOT / item["config_path"])
        record["code_config_reference"] = declared_content_identity(
            ROOT / space["strategy_path"], space["trial_plan"]
        )
        validate_identity(record)
        new_path = directory / "preregistration.v2.json"
        with new_path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(record, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        validate_preregistration(new_path)
        registry["amendments"][eid] = {
            "superseded_sha256": sha256(old_path),
            "effective_path": new_path.relative_to(ROOT).as_posix(),
            "effective_sha256": sha256(new_path),
            "effective_experiment_version": 2,
            "implementation_commit": space["implementation_commit"],
        }
    with registry_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(registry, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(
        "Three v2 declarations appended; original admissions and 12-profile allocation preserved."
    )


if __name__ == "__main__":
    main()
