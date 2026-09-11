"""Validate the completed WP-009 exogenous foundation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wp009_validation import validate_wp009


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-data", action="store_true")
    options = parser.parse_args()
    print(json.dumps(validate_wp009(ROOT, data_available=not options.no_data), indent=2))


if __name__ == "__main__":
    main()
