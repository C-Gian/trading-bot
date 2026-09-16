"""Freeze the Stage-1 search plan, the preregistration and the pre-execution admission.

This runs before any outer-evaluation candidate number exists and refuses to run again once
a result has been observed, so the frozen records can never be rewritten to fit an outcome.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.internal_structure import (
    ADMISSION_PATH,
    PREREGISTRATION_PATH,
    RESULT_PATH,
    SEARCH_PLAN_PATH,
    ExperimentError,
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
    if (ROOT / RESULT_PATH).exists():
        raise ExperimentError("refusing to rewrite frozen records after a result was observed")
    write(SEARCH_PLAN_PATH, search_plan())
    write(PREREGISTRATION_PATH, preregistration())
    record = admission(ROOT)
    write(ADMISSION_PATH, record)
    print(
        f"predictive internal structure frozen: status={record['status']} "
        f"identity={admission_identity(ROOT)}"
    )


if __name__ == "__main__":
    main()
