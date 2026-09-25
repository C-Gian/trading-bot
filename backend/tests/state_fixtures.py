"""Shared state fixtures for tests of preserved pre-park product mechanics.

ADR-0042 parks alpha research, and the live state makes every action surface fail closed. Tests
that still exercise the preserved ALIGNED analysis / paper / runner mechanics run against a copy
of the live state whose `current_project_status.disposition` is not parked.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def unparked_state_path() -> Path:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    state["current_project_status"]["disposition"] = "ACTIVE_ALLOCATION"
    directory = Path(tempfile.gettempdir()) / "trading-bot-tests"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"unparked-state-{os.getpid()}.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    return path
