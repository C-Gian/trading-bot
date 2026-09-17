"""Freeze the open-interest search plan, both preregistrations and the admission.

This runs after the source audit has passed and before any Stage-2 open-interest
outer-evaluation number exists. It refuses to run again once either result is observed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.internal_structure import ExperimentError, canonical_bytes
from app.predictive.open_interest import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    SEARCH_PLAN_PATH,
    admission,
    admission_identity,
    preregistration,
    preregistration_path,
    result_path,
    search_plan,
)


def write(relative: str, payload: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(payload))


def main() -> None:
    if any((ROOT / result_path(name)).exists() for name in CONFIGURATION_ORDER):
        raise ExperimentError("refusing to rewrite frozen records after a result was observed")
    write(SEARCH_PLAN_PATH, search_plan())
    for model_version in CONFIGURATION_ORDER:
        write(preregistration_path(model_version), preregistration(model_version, ROOT))
    record = admission(ROOT)
    write(ADMISSION_PATH, record)
    print(
        f"predictive stage 2 open interest frozen: status={record['status']} "
        f"folds={record['included_folds']} identity={admission_identity(ROOT)}"
    )


if __name__ == "__main__":
    main()
