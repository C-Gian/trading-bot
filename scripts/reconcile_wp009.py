"""Run the independent WP-009 point-in-time oracle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.exogenous_oracle import REPORT_PATH, reconcile


def main() -> None:
    report = reconcile(ROOT)
    path = ROOT / REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if report["status"] != "PASS":
        raise SystemExit("WP-009 independent as-of reconciliation failed")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
