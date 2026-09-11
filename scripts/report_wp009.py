"""Materialize deterministic WP-009 coverage and foundation reports."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.exogenous_reporting import write_reports

if __name__ == "__main__":
    write_reports(ROOT)
    print("WP-009 coverage and foundation reports written")
