"""Run the pre-result open-interest source audit and write its immutable record.

Provenance, point-in-time semantics, cadence and fold coverage are decided here, before any
target-bearing model exists. ``--check`` revalidates the committed audit instead of
recomputing it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.internal_structure import ExperimentError, canonical_bytes
from app.predictive.open_interest_audit import AUDIT_PATH, PASS, run_source_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    path = ROOT / AUDIT_PATH

    if options.check:
        committed = json.loads(path.read_text(encoding="utf-8"))
        if committed["target_bearing_model_fitted"]:
            raise ExperimentError("the source audit claims a model fit it must precede")
        print(
            f"open interest source audit: {committed['status']} "
            f"folds={(committed['coverage'] or {}).get('admissible_folds')}"
        )
        return

    audit = run_source_audit(ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(audit))
    coverage = audit["coverage"]
    print(f"open interest source audit: {audit['status']}")
    if coverage is not None:
        for name, record in coverage["by_fold"].items():
            print(
                f"  {name}: eligible={record['eligible_decision_timestamps']} "
                f"coverage={record['coverage']:.5f} "
                f"history_days={record['prior_source_history_days']:.0f} "
                f"included={record['included']}"
            )
        print(
            f"  admissible folds={coverage['admissible_folds']} "
            f"timestamps={coverage['admissible_eligible_timestamps']}"
        )
    if audit["status"] != PASS:
        print("  gates blocked: no target-bearing model may be fitted")


if __name__ == "__main__":
    main()
