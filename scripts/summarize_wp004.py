"""Materialize deterministic evidence-only comparisons and human research views."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.checkpoint_views import build_comparison, memory_views


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    comparison_path = ROOT / "reports/research/WP-004-COMPARISON.json"
    content = json.dumps(build_comparison(), sort_keys=True, indent=2, allow_nan=False) + "\n"
    if comparison_path.exists():
        if comparison_path.read_text(encoding="utf-8") != content:
            raise ValueError("immutable comparison differs from saved evidence")
    elif options.check:
        raise FileNotFoundError(comparison_path)
    else:
        with comparison_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    lessons = ROOT / "research/memory/WP-004-LESSONS.json"
    if lessons.exists():
        for name, view in memory_views().items():
            path = ROOT / "research/memory" / name
            if options.check:
                if path.read_text(encoding="utf-8") != view:
                    raise ValueError(f"stale generated view: {name}")
            else:
                path.write_text(view, encoding="utf-8", newline="\n")
    print("Evidence-only comparison and available memory views: PASS")


if __name__ == "__main__":
    main()
