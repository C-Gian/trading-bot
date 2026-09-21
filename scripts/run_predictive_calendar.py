"""Execute or validate the frozen V2 deterministic-calendar family."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.calendar import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    REPORT_JSON_PATH,
    REPORT_MARKDOWN_PATH,
    RESULT_PATHS,
    TRIAL_PATHS,
    CalendarExperimentError,
    admission,
    canonical_bytes,
    family_summary,
    run_family,
)
from app.predictive.calendar_report import markdown_bytes, validate_calendar


def write(relative: str, payload: bytes) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def execute() -> dict:
    path = ROOT / ADMISSION_PATH
    if not path.is_file():
        raise CalendarExperimentError("the pre-result admission artifact does not exist")
    if json.loads(path.read_text(encoding="utf-8")) != admission(ROOT):
        raise CalendarExperimentError("the admission no longer matches the frozen files")
    outputs = run_family(ROOT)
    results = {}
    for model in CONFIGURATION_ORDER:
        result, trials = outputs[model]
        write(RESULT_PATHS[model], canonical_bytes(result))
        write(TRIAL_PATHS[model], canonical_bytes(trials))
        results[model] = result
    report = family_summary(results)
    write(REPORT_JSON_PATH, canonical_bytes(report))
    write(REPORT_MARKDOWN_PATH, markdown_bytes(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--data", action="store_true")
    options = parser.parse_args()
    if options.check:
        finding = validate_calendar(ROOT, data_available=options.data)
        print(
            "predictive V2 calendar: "
            f"{finding['status']} replayed={finding['data_replayed']} "
            f"disposition={finding['family_disposition']}"
        )
        return
    report = execute()
    print(
        "predictive V2 calendar written: "
        f"disposition={report['family_disposition']} fits={report['model_fits']}"
    )


if __name__ == "__main__":
    main()
