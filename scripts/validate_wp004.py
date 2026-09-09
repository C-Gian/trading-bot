"""Audit saved WP-004 evidence without loading market data or rerunning a strategy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wp004_validation import validate_checkpoint


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-result-commit", action="store_true")
    options = parser.parse_args()
    print(
        json.dumps(
            validate_checkpoint(require_committed_results=not options.before_result_commit),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
