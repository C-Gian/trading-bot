"""Record the post-result residual source finding for the macro release-state checkpoint.

Additive and deterministic. It rewrites no frozen record, re-executes no configuration and
reads no BTC outcome. ``--check`` revalidates the committed record's invariants instead of
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
from app.predictive.macro_release_state_residual import (
    DISPOSITION,
    FINDING_ID,
    RESIDUAL_PATH,
    residual_finding,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    path = ROOT / RESIDUAL_PATH

    if options.check:
        committed = json.loads(path.read_text(encoding="utf-8"))
        if committed["finding_id"] != FINDING_ID or committed["disposition"] != DISPOSITION:
            raise ExperimentError("the residual finding identity changed")
        if committed["interpretation"]["result_rewritten"]:
            raise ExperimentError("the residual finding claims the result was rewritten")
        if committed["boundaries"]["btc_outcomes_read"]:
            raise ExperimentError("the residual finding claims it read a BTC outcome")
        print(
            f"macro release state residual: {committed['finding_id']} "
            f"rows={committed['defect']['substrate_rows']} "
            f"evaluation_share={committed['exposure']['evaluation_share_affected']:.5f}"
        )
        return

    record = residual_finding(ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(record))
    exposure = record["exposure"]
    print(f"macro release state residual: {record['finding_id']} ({record['disposition']})")
    print(
        f"  substrate rows={record['defect']['substrate_rows']} "
        f"series={record['defect']['affected_series']} "
        f"max_lead_days={record['defect']['maximum_lead_days']}"
    )
    print(
        f"  evaluation {exposure['evaluation_instants_affected']}/"
        f"{exposure['evaluation_decision_instants']} "
        f"({exposure['evaluation_share_affected']:.5f}); training "
        f"{exposure['training_instants_affected']}/"
        f"{exposure['training_decision_instants']} "
        f"({exposure['training_share_affected']:.5f})"
    )


if __name__ == "__main__":
    main()
