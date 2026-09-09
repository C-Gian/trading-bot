"""Materialize WP-005 integrity artifacts in the required chronology."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wp005_integrity import (  # noqa: E402
    exact_wp004_replay,
    feature_and_result_reconciliation,
    source_provenance,
)


def write_new(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"immutable artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("audit", "replay"))
    args = parser.parse_args()
    if args.stage == "audit":
        provenance = source_provenance(ROOT)
        write_new(ROOT / "reports/validation/WP-005-SOURCE-PROVENANCE.json", provenance)
        reconciliation = feature_and_result_reconciliation(ROOT)
        write_new(
            ROOT / "research/diagnostics/WP-005/feature-result-reconciliation.json",
            reconciliation,
        )
    else:
        replay = exact_wp004_replay(ROOT)
        write_new(ROOT / "research/diagnostics/WP-005/wp004-integrity-replay.json", replay)


if __name__ == "__main__":
    main()
