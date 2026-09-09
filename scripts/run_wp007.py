"""Execute only the committed WP-007 declaration; no optimization or data acquisition.

Every gate — order-flow integrity, oracle reconciliation, allocation, novelty admission,
family registry, ledger, preregistration chronology — runs before a single market array
is loaded.
"""

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

from app.research.continuation_lab import PROFILES, ResearchInputs
from app.research.evaluation_protocol import load_protocol, terminal_classification
from app.research.flow import FEATURE_VERSION, flow_source
from app.research.flow_lab import FlowLab
from app.research.runner import (
    deterministic_run_identity,
    finalize_result,
    run_declared_trials,
    sha256,
)
from app.research.wp007 import ATTEMPT_PATH, OUTCOMES_PATH, ROOT_FAMILY, SPEC, preflight

MANIFEST = "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"


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


def outcome_for(experiment_id: str, result: dict[str, Any], result_path: Path) -> dict[str, Any]:
    classification = result["secondary_results"]["terminal_classification"]
    uncertain = classification == "INCONCLUSIVE"
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "result_path": result_path.relative_to(ROOT).as_posix(),
        "result_sha256": sha256(result_path),
        "terminal_classification": classification,
        "conclusion": (
            f"Frozen annual development evaluation of the aggressive buy-flow transition:"
            f" {classification}; no strategy approval, no sealed query, no Champion."
        ),
        "falsified": (
            "Evidence sufficiency was not met; no economic falsification is claimed."
            if uncertain
            else "The frozen net-profitability/stability claim failed its predeclared hurdles."
            if classification.startswith("REJECT")
            else "No falsification of the frozen development hurdles; this is exposed development"
            " evidence, not independent forward evidence."
        ),
        "not_falsified": (
            "Other flow definitions, other thresholds, other context durations, other barriers,"
            " other horizons, cross-venue flow and all prospective behaviour remain untested by"
            " this declaration."
        ),
        "evidence_facts": [
            {"json_pointer": "/primary_result", "expected_value": result["primary_result"]},
            {
                "json_pointer": "/secondary_results/terminal_classification",
                "expected_value": classification,
            },
        ],
        "failure_modes": [classification],
        "legitimate_revisit": (
            "Retain this evidence. No threshold drift away from the 0.5 accounting balance point,"
            " no context-duration search, no barrier or horizon change, and no gate chosen after"
            " seeing these numbers; require a new diagnostic or structural prediction and an"
            " explicit cumulative Research Director allocation."
        ),
    }


def main() -> None:
    gate = preflight()
    # Hash verification and data loading happen only after every admission gate passes.
    inputs = ResearchInputs.load(ROOT)
    features = flow_source(ROOT)
    protocol = load_protocol()
    lab = FlowLab(inputs, features, protocol)
    started = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    atomic_json(
        ROOT / ATTEMPT_PATH,
        {
            **gate,
            "started_at_utc": started,
            "root_family": ROOT_FAMILY,
            "trial_ids": [
                f"{variant}:{profile}" for variant in SPEC.values() for profile in PROFILES
            ],
        },
    )
    for experiment_id, variant in SPEC.items():
        directory = ROOT / "research/experiments" / experiment_id
        prereg_path = directory / "preregistration.json"
        prereg = json.loads(prereg_path.read_text(encoding="utf-8"))

        def adapter(config, trial_id, eid=experiment_id):
            print(f"Executing declared profile {eid} / {trial_id}", flush=True)
            return lab.run_trial(config, trial_id)

        trials = run_declared_trials(prereg_path, ROOT / MANIFEST, adapter)
        atomic_json(directory / "trials.json", trials)
        if any(trial["status"] != "COMPLETED" for trial in trials):
            raise RuntimeError("A declared execution failed; immutable failure artifact retained")
        profiles = {trial["profile"]: trial["summary"] for trial in trials}
        classification = terminal_classification(
            profiles["DEFAULT"], profiles["ZERO"], profiles["DOUBLE"], protocol
        )
        secondary = {
            "profiles": profiles,
            "terminal_classification": classification,
            "execution_provenance": {
                **gate,
                "trial_artifact_sha256": sha256(directory / "trials.json"),
                "feature_version": FEATURE_VERSION,
                "fold_executions": 24,
                "trial_count": 4,
                "structural_variants": 1,
            },
        }
        result = {
            "schema_version": 2,
            "experiment_id": experiment_id,
            "experiment_version": prereg["experiment_version"],
            "preregistration_reference": experiment_id,
            "preregistration_created_at_utc": prereg["created_at_utc"],
            "completed_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "status": "COMPLETED",
            "code_config_reference": prereg["code_config_reference"],
            "dataset": {key: prereg["dataset"][key] for key in ("manifest_id", "content_hash")},
            "seed_reference": [0],
            "primary_result": profiles["DEFAULT"]["metrics"]["net_expectancy_r"],
            "secondary_results": secondary,
            "artifacts": [(directory / "trials.json").relative_to(ROOT).as_posix()],
            "validation_outcome": "PASS",
            "interpretation": (
                "DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE. Exposed chronological"
                f" validation of the newly admitted {ROOT_FAMILY} root; {variant} is one of exactly"
                " two authorized variants. Exchange-reported taker share is a venue-level proxy,"
                " not market-wide order flow and not evidence of causality."
            ),
            "trial_accounting": {"declared_budget": 4, "executed_trials": 4},
            "run_identity_hash": deterministic_run_identity(
                prereg,
                gate["execution_commit"],
                {"reference": prereg["code_config_reference"]},
                {
                    "engine": "BACKTEST_ENGINE_V2",
                    "execution": "EXECUTION_MODEL_V2",
                    "cost": "BTCUSDT_SPOT_COST_V1",
                },
            ),
        }
        result_path = directory / "result.json"
        finalize_result(result, prereg_path, result_path)
        with (ROOT / OUTCOMES_PATH).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(
                    outcome_for(experiment_id, result, result_path),
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            )
    print("Both bounded WP-007 variants finalized; every negative result is retained.", flush=True)


if __name__ == "__main__":
    main()
