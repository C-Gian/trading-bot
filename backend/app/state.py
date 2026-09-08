from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[2]


class StateRepository:
    def __init__(self, state_path: Path | None = None, schema_path: Path | None = None):
        self.state_path = state_path or ROOT / "state/current_state.json"
        self.schema_path = schema_path or ROOT / "contracts/project_state.schema.json"

    def load(self) -> dict[str, Any]:
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
            state
        )
        return state
