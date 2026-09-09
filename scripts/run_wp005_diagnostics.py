"""Execute only the committed WP-005 matched-control diagnostic declaration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.wp005_diagnostics import build_diagnostics


def main() -> None:
    directory = ROOT / "research/diagnostics/WP-005"
    outputs = build_diagnostics(ROOT)
    targets = {name: directory / name for name in outputs}
    existing = [str(path) for path in targets.values() if path.exists()]
    if existing:
        raise FileExistsError(f"immutable diagnostic artifacts already exist: {existing}")
    for name, value in outputs.items():
        targets[name].write_text(
            json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
