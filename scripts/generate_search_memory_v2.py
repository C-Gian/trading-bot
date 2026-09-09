"""Generate frozen legacy duplicate/reference signatures without market access."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.search_memory_v2 import generate_legacy_signatures  # noqa: E402


def main() -> None:
    target = ROOT / "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json"
    if target.exists():
        raise FileExistsError("legacy V2 signatures are immutable")
    target.write_text(
        json.dumps(generate_legacy_signatures(ROOT), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
