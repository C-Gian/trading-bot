"""Create or check the immutable pre-result macro-vintage source audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.internal_structure import canonical_bytes
from app.predictive.macro_vintage_audit import AUDIT_PATH, PASS, run_source_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    path = ROOT / AUDIT_PATH
    if options.check:
        committed = json.loads(path.read_text(encoding="utf-8"))
        if committed["target_bearing_model_fitted"]:
            raise RuntimeError("the source audit must precede every target-bearing fit")
        print(
            f"macro vintage source audit: {committed['status']} "
            f"folds={committed['coverage']['admissible_folds']}"
        )
        return
    audit = run_source_audit(ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(audit))
    print(f"macro vintage source audit: {audit['status']}")
    for name, record in audit["coverage"]["by_fold"].items():
        print(
            f"  {name}: coverage={record['coverage']:.6f} "
            f"history_days={record['causal_feature_valid_history_days']:.1f} "
            f"included={record['included']}"
        )
    print(
        f"  pooled={audit['coverage']['pooled_source_feature_coverage']:.6f} "
        f"folds={audit['coverage']['admissible_folds']}"
    )
    if audit["status"] != PASS:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
