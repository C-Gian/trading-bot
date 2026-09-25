"""Shared state fixtures for tests of preserved pre-park product mechanics.

The live state has no validated strategy, so every action surface fails closed (System G1
Checkpoint 1 guard, superseding the ADR-0042 PARKED check). Tests that still exercise the preserved
ALIGNED analysis / paper / runner mechanics run against a copy of the live state that carries an
explicit *test-fixture* validated-strategy identity and legacy-runner authorization. That copy is
validated against a copy of the schema that admits those two fixture-only values; the canonical
schema keeps both closed for the live state.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_STRATEGY = "TEST_FIXTURE_PRESERVED_ALIGNED_MECHANICS"


def _directory() -> Path:
    directory = Path(tempfile.gettempdir()) / "trading-bot-tests"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def unparked_state_path() -> Path:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    current = state["current_project_status"]
    current["disposition"] = "ACTIVE_ALLOCATION"
    current["validated_strategy"] = FIXTURE_STRATEGY
    current["legacy_research_runner_authorized"] = True
    path = _directory() / f"unparked-state-{os.getpid()}.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


def fixture_schema_path() -> Path:
    schema = json.loads((ROOT / "contracts/project_state.schema.json").read_text(encoding="utf-8"))
    properties = schema["properties"]["current_project_status"]["properties"]
    properties["validated_strategy"] = {"type": ["null", "string"]}
    properties["legacy_research_runner_authorized"] = {"type": "boolean"}
    path = _directory() / f"fixture-schema-{os.getpid()}.json"
    path.write_text(json.dumps(schema), encoding="utf-8")
    return path


def preserved_mechanics() -> dict[str, Any]:
    """`create_app` keyword arguments for the preserved-mechanics fixture state."""
    return {"state_path": unparked_state_path(), "state_schema_path": fixture_schema_path()}
