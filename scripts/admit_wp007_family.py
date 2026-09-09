"""Submit AGGRESSIVE_BUY_FLOW_TRANSITION_V1 to the governed novelty gate.

Runs before any market result, against both the frozen V1 reference signatures and
every SEARCH_MEMORY_V2-era admitted behaviour. A DUPLICATE, PARAMETER_VARIANT,
NEAR_DUPLICATE or conflicting-root classification for the primary variant is preserved
as an immutable rejection and blocks execution; the classifier is never weakened, the
family is never renamed, and no condition is added to force novelty.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wp007 import (
    ADMISSION_PATH,
    REJECTION_PATH,
    ROOT_FAMILY,
    NoveltyRejected,
    novelty_decision,
    substrate_gate,
    validate_admission,
    validate_allocation,
    validate_family_record,
)


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
    substrate = substrate_gate()
    validate_allocation()
    try:
        decision = novelty_decision()
    except NoveltyRejected as exc:
        write(
            REJECTION_PATH,
            {
                "schema_version": 1,
                "version": "SEARCH_MEMORY_V2",
                "work_package": "WP-007",
                "proposed_root_family": ROOT_FAMILY,
                "admitted": False,
                "rejection": str(exc),
                "recorded_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "consequence": (
                    "No market result may be produced for this family. The rejection is preserved,"
                    " the classifier is not weakened, nothing is renamed, and no condition is added"
                    " to force novelty. The feature substrate work stands."
                ),
            },
        )
        raise SystemExit(f"Novelty gate rejected the proposal: {exc}") from exc
    write(ADMISSION_PATH, decision)
    validate_family_record()
    validate_admission()
    print(
        f"Order-flow substrate {substrate['substrate_manifest_id']} admitted; novelty gate: "
        f"{decision['family_classification']}; {len(decision['variants'])} variants under "
        f"{ROOT_FAMILY}."
    )


if __name__ == "__main__":
    main()
