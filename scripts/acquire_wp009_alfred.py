"""Acquire and build the frozen WP-009 ALFRED macro context."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.alfred import INTEGRITY_PATH, MANIFEST_PATH, acquire, build


def write_json(relative: str, payload: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-only", action="store_true")
    options = parser.parse_args()
    progress = {"mode": "VERIFIED_CACHE_BUILD_ONLY"} if options.build_only else acquire(ROOT)
    manifest, integrity = build(ROOT)
    write_json(MANIFEST_PATH, manifest)
    write_json(INTEGRITY_PATH, integrity)
    print(json.dumps({"acquisition": progress, "integrity": integrity}, indent=2))


if __name__ == "__main__":
    main()
