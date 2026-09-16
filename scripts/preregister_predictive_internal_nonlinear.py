"""Freeze the reserved configuration's preregistration, coverage ruling and admission.

This runs before any HGBR outer-evaluation number exists and refuses to run again once a
result has been observed, so the frozen records and the Research Director's coverage ruling
can never be rewritten to fit an outcome.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.internal_nonlinear import (
    ADMISSION_PATH,
    PREREGISTRATION_PATH,
    RESULT_PATH,
    admission,
    admission_identity,
    preregistration,
)
from app.predictive.internal_structure import ExperimentError, canonical_bytes


def write(relative: str, payload: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(payload))


def main() -> None:
    if (ROOT / RESULT_PATH).exists():
        raise ExperimentError("refusing to rewrite frozen records after a result was observed")
    write(PREREGISTRATION_PATH, preregistration())
    record = admission(ROOT)
    write(ADMISSION_PATH, record)
    print(
        f"predictive internal nonlinear frozen: status={record['status']} "
        f"option={record['coverage_policy_decision']['option_taken']} "
        f"identity={admission_identity(ROOT)}"
    )


if __name__ == "__main__":
    main()
