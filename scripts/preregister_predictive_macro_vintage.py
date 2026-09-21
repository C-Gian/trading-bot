"""Freeze the blocked macro-vintage family after its source-only audit."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.internal_structure import canonical_bytes
from app.predictive.macro_vintage import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    SEARCH_PLAN_PATH,
    admission,
    admission_identity,
    preregistration,
    preregistration_path,
    search_plan,
)


def write(relative: str, payload: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(payload))


def main() -> None:
    write(SEARCH_PLAN_PATH, search_plan())
    for model_version in CONFIGURATION_ORDER:
        write(preregistration_path(model_version), preregistration(model_version, ROOT))
    write(ADMISSION_PATH, admission(ROOT))
    print(f"macro vintage frozen source-block: identity={admission_identity(ROOT)}")


if __name__ == "__main__":
    main()
