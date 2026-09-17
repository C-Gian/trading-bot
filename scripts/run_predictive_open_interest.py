"""Execute both frozen `PREDICTIVE-STAGE2-OPEN-INTEREST-V1` configurations exactly once.

The pre-execution admission artifact must already be committed and must still match the
frozen search plan, both preregistrations, the predictive contract, the passed source audit,
the canonical source identity and the implementation. ``--check`` validates the committed
artifacts instead of recomputing them; ``--data`` additionally replays them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.internal_structure import ExperimentError, canonical_bytes
from app.predictive.open_interest import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    REPORT_JSON_PATH,
    REPORT_MARKDOWN_PATH,
    admission,
    result_path,
    run_experiment,
    trials_path,
)
from app.predictive.open_interest_report import (
    configuration_result_document,
    markdown_bytes,
    report_bytes,
    trials_document,
    validate_open_interest,
)


def write(relative: str, payload: bytes) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def execute() -> dict:
    admission_path = ROOT / ADMISSION_PATH
    if not admission_path.is_file():
        raise ExperimentError("the pre-execution admission artifact must exist before the run")
    if json.loads(admission_path.read_text(encoding="utf-8")) != admission(ROOT):
        raise ExperimentError("the admission artifact no longer matches the frozen files")
    result = run_experiment(ROOT)
    write(REPORT_JSON_PATH, report_bytes(result))
    write(REPORT_MARKDOWN_PATH, markdown_bytes(result))
    for model_version in CONFIGURATION_ORDER:
        write(
            result_path(model_version),
            canonical_bytes(configuration_result_document(result, model_version)),
        )
        write(trials_path(model_version), canonical_bytes(trials_document(result, model_version)))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--data", action="store_true", help="replay against the market data")
    options = parser.parse_args()
    if options.check:
        findings = validate_open_interest(ROOT, data_available=options.data)
        print(
            f"predictive stage 2 open interest: {findings['status']} "
            f"replayed={findings['data_replayed']} "
            f"family={findings['family_disposition']} "
            f"folds={findings['included_folds']}"
        )
        for model_version, classification in findings["classifications"].items():
            print(f"  {model_version}: {classification}")
        return
    result = execute()
    print(
        "predictive stage 2 open interest written: "
        f"{result['family_disposition']['disposition']} "
        f"folds={result['folds']['included_folds']}"
    )
    for model_version in CONFIGURATION_ORDER:
        configuration = result["configurations"][model_version]
        pooled = configuration["candidate"]["pooled_directional"]
        primary = configuration["primary_comparison"]
        print(
            f"  {model_version}: win_rate={pooled['win_rate']} "
            f"coverage={pooled['coverage']} delta={primary['pooled_delta']} "
            f"interval={primary['paired_interval']['interval']} "
            f"classification={configuration['terminal_classification']}"
        )


if __name__ == "__main__":
    main()
