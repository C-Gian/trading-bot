"""Acquire and canonicalize only official CFTC TFF data for WP-017 preparation."""

from __future__ import annotations

import json
from pathlib import Path

from app.research.cftc import INTEGRITY_PATH, MANIFEST_PATH, acquire, build

ROOT = Path(__file__).resolve().parents[1]


def _write_json(relative: str, payload: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    acquisition = acquire(ROOT)
    manifest, integrity = build(ROOT)
    _write_json(MANIFEST_PATH, manifest)
    _write_json(INTEGRITY_PATH, integrity)
    print(json.dumps({"acquisition": acquisition, "integrity": integrity}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
