"""Acquire and canonicalize official Wikimedia Bitcoin daily pageviews through 2024."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wikimedia import acquire, build


def main() -> int:
    acquisition = acquire(ROOT)
    manifest = build(ROOT)
    print(
        json.dumps(
            {
                "acquisition": acquisition,
                "manifest_id": manifest["manifest_id"],
                "records": manifest["records"],
                "coverage": manifest["coverage"],
                "post_cutoff_rows": manifest["integrity"]["post_cutoff_rows"],
                "canonical_sha256": manifest["canonical"]["file_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
