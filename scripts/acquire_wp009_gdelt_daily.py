"""Acquire and build the GDELT_NEWS_CONTEXT_V1_1 daily pilot interval.

The pilot is the deterministic 2017-08-17 .. 2017-12-31 window for all five frozen
channels and both frozen modes (10 requests). Acquisition is resumable from cache,
idempotent, hash-verified and bounded on HTTP errors; a persistent credential-free
throttle stops the run and preserves every successful cache entry.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.exogenous import ExogenousDataError
from app.research.gdelt_daily import (
    PILOT_ACQUISITION_PATH,
    PILOT_INTEGRITY_PATH,
    PILOT_MANIFEST_PATH,
    acquire,
    build,
)


def write_json(relative: str, payload: object) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-only", action="store_true")
    options = parser.parse_args()

    progress = {"status": "VERIFIED_CACHE_BUILD_ONLY"} if options.build_only else acquire(ROOT)
    write_json(PILOT_ACQUISITION_PATH, progress)
    try:
        manifest, integrity = build(ROOT)
    except ExogenousDataError as exc:
        print(json.dumps({"acquisition": progress, "build": str(exc)}, indent=2))
        return 1
    write_json(PILOT_MANIFEST_PATH, manifest)
    write_json(PILOT_INTEGRITY_PATH, integrity)
    print(
        json.dumps(
            {
                "acquisition": progress,
                "integrity": {key: integrity[key] for key in ("status", "daily_rows", "days")},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
