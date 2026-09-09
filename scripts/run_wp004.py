"""Execute only the committed WP-004 declaration; no optimization or data acquisition."""

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

from app.research.continuation_lab import ContinuationLab, ResearchInputs
from app.research.evaluation_protocol import load_protocol, terminal_classification
from app.research.runner import (
    deterministic_run_identity,
    finalize_result,
    run_declared_trials,
    sha256,
)
from app.research.search_memory import load_memory, render_failure_memory, render_research_map
from app.research.wp004 import SPEC, preflight


def atomic_json(path: Path, payload: Any) -> None:
    if path.exists():
        raise FileExistsError(f"immutable artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
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
        "conclusion": f"Frozen annual development evaluation: {classification}; no strategy approval.",
        "falsified": "Evidence sufficiency not met; no economic falsification claimed."
        if uncertain
        else "The frozen net-profitability/stability claim failed its predeclared hurdles."
        if classification.startswith("REJECT")
        else "No falsification of the frozen development hurdles; this is not independent forward evidence.",
        "not_falsified": "All continuation mechanisms, other exits, and prospective behavior remain untested by this declaration.",
        "evidence_facts": [
            {"json_pointer": "/primary_result", "expected_value": result["primary_result"]},
            {
                "json_pointer": "/secondary_results/terminal_classification",
                "expected_value": classification,
            },
        ],
        "failure_modes": [classification],
        "legitimate_revisit": "Retain WP-003 and WP-004 evidence. No exact replay, threshold drift or recycled WP-003 clue alone; require a new diagnostic/structural prediction and explicit cumulative allocation.",
    }


def main() -> None:
    gate = preflight()
    # Hash verification and data loading happen only after all admissions and Git gates pass.
    inputs = ResearchInputs.load(ROOT)
    protocol = load_protocol()
    lab = ContinuationLab(inputs, protocol)
    started = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    atomic_json(
        ROOT / "research/runs/WP-004-ATTEMPT.json",
        {
            **gate,
            "started_at_utc": started,
            "trial_ids": [
                f"{variant}:{profile}"
                for variant, _ in SPEC.values()
                for profile in ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
            ],
        },
    )
    for experiment_id in SPEC:
        directory = ROOT / "research/experiments" / experiment_id
        prereg_path = directory / "preregistration.json"
        prereg = json.loads(prereg_path.read_text())

        def adapter(config, trial_id, eid=experiment_id):
            print(f"Executing declared profile {eid} / {trial_id}", flush=True)
            return lab.run_trial(config, trial_id)

        trials = run_declared_trials(
            prereg_path, ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json", adapter
        )
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
                "feature_version": "CONTINUATION_FEATURES_V1",
                "fold_executions": 24,
                "trial_count": 4,
                "structural_variants": 1,
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
            "primary_result": profiles["DEFAULT"]["metrics"]["net_expectancy_r"],
            "secondary_results": secondary,
            "artifacts": [(directory / "trials.json").relative_to(ROOT).as_posix()],
            "validation_outcome": "PASS",
            "interpretation": "DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE. Exposed chronological validation; adaptive descendant of WP-003 breakout.",
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
        with (ROOT / "research/memory/OUTCOMES.jsonl").open(
            "a", encoding="utf-8", newline="\n"
        ) as handle:
            handle.write(
                json.dumps(
                    outcome_for(experiment_id, result, result_path),
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            )
    memory = load_memory()
    (ROOT / "research/memory/RESEARCH_MAP.md").write_text(
        render_research_map(memory), encoding="utf-8"
    )
    (ROOT / "research/memory/FAILURE_MEMORY.md").write_text(
        render_failure_memory(memory), encoding="utf-8"
    )
    print("All three bounded WP-004 variants finalized; scientific results retained.", flush=True)


if __name__ == "__main__":
    main()
