"""Run the pre-result macro release-state source audit and write its immutable record.

Provenance, the corrected release-state semantics, the source-cadence integrity of the
release calendar and fold coverage are all decided here, before any target-bearing model
exists. ``--check`` revalidates the committed audit instead of recomputing it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.internal_structure import ExperimentError, canonical_bytes
from app.predictive.macro_release_state_audit import AUDIT_PATH, PASS, run_source_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    path = ROOT / AUDIT_PATH

    if options.check:
        committed = json.loads(path.read_text(encoding="utf-8"))
        if committed["target_bearing_model_fitted"]:
            raise ExperimentError("the source audit claims a model fit it must precede")
        if committed["predecessor_reclassified"]:
            raise ExperimentError("the source audit reclassified the predecessor source block")
        print(
            f"macro release state source audit: {committed['status']} "
            f"folds={(committed['coverage'] or {}).get('admissible_folds')}"
        )
        return

    audit = run_source_audit(ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(audit))
    integrity = audit["source_cadence_integrity"]
    print(f"macro release state source audit: {audit['status']}")
    print(f"  cadence integrity: {'PASS' if integrity['passed'] else 'BLOCKED'}")
    for name, record in integrity["by_series"].items():
        print(
            f"    {name}: max_gap={record['maximum_observation_gap_days']}d "
            f"limit={record['maximum_allowed_gap_days']}d passed={record['passed']}"
        )
    coverage = audit["coverage"]
    if coverage is not None:
        for name, record in coverage["by_fold"].items():
            print(
                f"  {name}: eligible={record['eligible_decision_timestamps']} "
                f"coverage={record['coverage']:.5f} "
                f"history_days={record['causal_feature_valid_history_days']:.0f} "
                f"included={record['included']}"
            )
        print(
            f"  admissible folds={coverage['admissible_folds']} "
            f"pooled={coverage['pooled_source_feature_coverage']:.5f}"
        )
    if audit["status"] != PASS:
        print("  gates blocked: no target-bearing model may be fitted")


if __name__ == "__main__":
    main()
