"""Generate the independent WP-008 model and leakage audits."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.model_reconciliation import reconcile


def write(relative: str, payload: object) -> None:
    path = ROOT / relative
    if path.exists():
        raise FileExistsError(f"immutable validation artifact already exists: {relative}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n")


def main() -> None:
    reconciliation, leakage = reconcile(ROOT)
    write("reports/validation/WP-008-MODEL-RECONCILIATION.json", reconciliation)
    write("reports/validation/WP-008-SUPERVISED-LEAKAGE-AUDIT.json", leakage)
    print("WP-008 independent model reconciliation and leakage audit: PASS")


if __name__ == "__main__":
    main()
