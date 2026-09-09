"""Submit PERSISTENT_TREND_PULLBACK_RECOVERY_V1 to the governed novelty gate.

Runs before any market result. A DUPLICATE, PARAMETER_VARIANT, NEAR_DUPLICATE or
conflicting-root classification is preserved as an immutable rejection and blocks
execution; the classifier is never weakened and the family is never renamed.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wp006 import (
    ADMISSION_PATH,
    NoveltyRejected,
    novelty_decision,
    validate_admission,
    validate_allocation,
    validate_registry,
)

REJECTION_PATH = "research/memory/WP006-NOVELTY-REJECTION.json"


def write(relative: str, payload: dict) -> Path:
    path = ROOT / relative
    if path.exists():
        raise FileExistsError(f"immutable governance record already exists: {relative}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return path


def main() -> None:
    validate_allocation()
    try:
        decision = novelty_decision()
    except NoveltyRejected as exc:
        write(
            REJECTION_PATH,
            {
                "schema_version": 1,
                "version": "SEARCH_MEMORY_V2",
                "work_package": "WP-006",
                "proposed_root_family": "FAM-PULLBACK-RECOVERY",
                "admitted": False,
                "rejection": str(exc),
                "recorded_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "consequence": "No market result may be produced for this family. The rejection is preserved and the classifier is not weakened.",
            },
        )
        raise SystemExit(f"Novelty gate rejected the proposal: {exc}") from exc
    write(ADMISSION_PATH, decision)
    validate_registry()
    validate_admission()
    print(
        f"Novelty gate: {decision['family_classification']}; "
        f"{len(decision['variants'])} variants admitted under FAM-PULLBACK-RECOVERY."
    )


if __name__ == "__main__":
    main()
