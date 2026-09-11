"""Build EXOGENOUS_CONTEXT_V1 without loading market data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.exogenous_context import MANIFEST_PATH, build


def main() -> None:
    manifest = build(ROOT)
    path = ROOT / MANIFEST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
