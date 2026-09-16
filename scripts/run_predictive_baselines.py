"""Compute the frozen `PREDICTIVE-BASELINES-V1` reference report.

No model is fitted, no parameter is searched, no external or post-cutoff data is read.
``--check`` validates the committed report instead of rewriting it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.report import (
    REPORT_PATH,
    build_report,
    load_report,
    report_bytes,
    validate_report,
)


def write(root: Path) -> dict:
    report = build_report(root)
    path = root / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(report_bytes(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--data", action="store_true", help="replay the report against the data")
    options = parser.parse_args()
    if options.check:
        findings = validate_report(ROOT, data_available=options.data)
        report = load_report(ROOT)
        print(
            f"predictive baselines: {findings['status']} "
            f"replayed={findings['data_replayed']} "
            f"eligible={report['folds']['eligible_decision_timestamps']}"
        )
        return
    report = write(ROOT)
    labels = report["labels"]
    print(
        f"predictive baselines written: grid={labels['grid_decision_instants']} "
        f"admissible={labels['admissible_labels']} "
        f"eligible={report['folds']['eligible_decision_timestamps']}"
    )
    for name, record in report["baselines"].items():
        pooled = record["pooled"]
        print(
            f"  {name}: win_rate={pooled['win_rate']} coverage={pooled['coverage']} "
            f"mae_pp={pooled['magnitude_mae_percentage_points']}"
        )


if __name__ == "__main__":
    main()
