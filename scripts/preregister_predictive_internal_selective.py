"""Freeze the V2 internal-structure family before any outer prediction is produced."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.internal_selective import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    PREREGISTRATION_PATHS,
    RESULT_PATHS,
    SEARCH_PLAN_PATH,
    InternalSelectiveExperimentError,
    admission,
    admission_identity,
    canonical_bytes,
    preregistration,
    search_plan,
)


def write(relative: str, payload: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(payload))


def main() -> None:
    if any((ROOT / RESULT_PATHS[model]).exists() for model in CONFIGURATION_ORDER):
        raise InternalSelectiveExperimentError(
            "refusing to rewrite preregistration after a result exists"
        )
    write(SEARCH_PLAN_PATH, search_plan())
    for model in CONFIGURATION_ORDER:
        write(PREREGISTRATION_PATHS[model], preregistration(model))
    record = admission(ROOT)
    write(ADMISSION_PATH, record)
    print(
        "predictive V2 internal structure frozen: "
        f"status={record['status']} identity={admission_identity(ROOT)}"
    )


if __name__ == "__main__":
    main()
