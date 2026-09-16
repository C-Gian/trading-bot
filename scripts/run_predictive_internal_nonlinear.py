"""Execute the reserved `PREDICTIVE-INTERNAL-NONLINEAR-V1` configuration exactly once.

The pre-execution admission artifact must already be committed and must still match the
frozen records, the Research Director's coverage ruling and the implementation, so the
design provably precedes the first outer-evaluation number. ``--check`` validates the
committed artifacts instead of recomputing them; ``--data`` additionally replays them
against the installed market data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.internal_nonlinear import (
    ADMISSION_PATH,
    REPORT_JSON_PATH,
    REPORT_MARKDOWN_PATH,
    RESULT_PATH,
    admission,
    run_experiment,
)
from app.predictive.internal_nonlinear_report import (
    markdown_bytes,
    report_bytes,
    validate_internal_nonlinear,
)
from app.predictive.internal_structure import ExperimentError


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
    payload = report_bytes(result)
    write(RESULT_PATH, payload)
    write(REPORT_JSON_PATH, payload)
    write(REPORT_MARKDOWN_PATH, markdown_bytes(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--data", action="store_true", help="replay against the market data")
    options = parser.parse_args()
    if options.check:
        findings = validate_internal_nonlinear(ROOT, data_available=options.data)
        print(
            f"predictive internal nonlinear: {findings['status']} "
            f"replayed={findings['data_replayed']} "
            f"classification={findings['terminal_classification']} "
            f"family={findings['stage1_family_status']}"
        )
        return
    result = execute()
    pooled = result["candidate"]["pooled_directional"]
    comparison = result["primary_comparison"]
    print(
        f"predictive internal nonlinear written: "
        f"win_rate={pooled['win_rate']} coverage={pooled['coverage']} "
        f"delta={comparison['pooled']['delta']} "
        f"interval={comparison['paired_interval']['interval']} "
        f"classification={result['terminal_classification']}"
    )


if __name__ == "__main__":
    main()
