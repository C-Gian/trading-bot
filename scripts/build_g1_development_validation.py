"""Write the System G1 Development V1 implementation-validation record (identities only).

Records protocol/decision/code/configuration/source identity hashes for the frozen implementation.
It reads manifest metadata only; no market observation or G1 outcome is read. `scripts/check.py`
re-derives every identity and fails if any frozen file changes without regenerating this record.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.g1 import batch
from app.g1.canonical import digest, to_plain
from app.g1.development import COST_STRESS, DELAY_STRESS_ADDITIONAL_MINUTES
from app.g1.forecaster import ESTIMATOR_VERSION, PROBABILITY_STATUS, SHRINKAGE_PRIOR
from app.g1.ledger import RiskPolicy
from app.g1.playbooks import CONFIGS, CONFIGURATIONS
from app.g1.sources import binding_identity

OUTPUT = "reports/validation/SYSTEM-G1-DEVELOPMENT-IMPLEMENTATION-V1.json"
DECISION = "decisions/ADR-0046-ACCEPT-G1-CYCLE-QUALITY-AND-ACTIVATE-CYCLE-COMPONENT.md"
SYNTHETIC_TESTS = {
    "backend/tests/test_g1_dev_cycle_and_indicators.py": 19,
    "backend/tests/test_g1_dev_playbooks.py": 23,
    "backend/tests/test_g1_dev_forecaster_scoring.py": 14,
    "backend/tests/test_g1_dev_engine_and_guard.py": 13,
    "backend/tests/test_g1_incomplete_bar_fix.py": 8,
    "backend/tests/test_g1_api_and_isolation.py": 7,
    "backend/tests/test_g1_cycle_quality_gate.py": 9,
    "backend/tests/test_g1_pipeline_and_cycle.py": 15,
    "backend/tests/test_g1_records_and_aggregation.py": 9,
    "backend/tests/test_g1_replay.py": 7,
    "backend/tests/test_g1_ledger.py": 17,
    "backend/tests/test_fail_closed_action_surface.py": 8,
    "frontend/src/Replay.test.tsx": 6,
}


def record() -> dict:
    configurations = {c: dataclasses.asdict(CONFIGS[c]) for c in CONFIGURATIONS}
    return {
        "checkpoint": "IMPLEMENT-SYSTEM-G1-DEVELOPMENT-V1",
        "classification": (
            "SYSTEM_G1_DEVELOPMENT_IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_REVIEW"
        ),
        "protocol": batch.PROTOCOL_PATH,
        "protocol_canonical_sha256": batch.protocol_sha256(ROOT),
        "decision": DECISION,
        "decision_canonical_sha256": batch.canonical_sha256(ROOT / DECISION),
        "code_canonical_sha256": batch.code_identity(ROOT),
        "configurations": configurations,
        "configuration_identity": digest(configurations),
        "execution_contract": {
            "risk_policy": to_plain(RiskPolicy()),
            "cost_stress": to_plain(COST_STRESS),
            "delay_stress_additional_minutes": DELAY_STRESS_ADDITIONAL_MINUTES,
        },
        "forecaster": {
            "estimator": ESTIMATOR_VERSION,
            "shrinkage_prior": SHRINKAGE_PRIOR,
            "probability_status": PROBABILITY_STATUS,
        },
        "windows": to_plain(batch.FROZEN_WINDOWS),
        "corrections": [
            {
                "decision": "decisions/ADR-0047-G1-IMPLEMENTATION-REVIEW-INCOMPLETE-BAR-CORRECTION.md",
                "work_package": "FIX-SYSTEM-G1-INCOMPLETE-BAR-RECURSIVE-STATE-V1",
                "change": (
                    "incomplete 15m/1h/4h/1d bars reset ATR, EMA20/EMA50, ADX/DI and daily "
                    "EMA20+lookback, are never consumed and publish UNAVAILABLE"
                ),
                "files": ["backend/app/g1/indicators.py"],
                "tests": "backend/tests/test_g1_incomplete_bar_fix.py",
            }
        ],
        "run_command": "uv run python scripts/run_g1_development.py --phase A|B",
        "run_directory": batch.RUN_DIR,
        "source_bindings": binding_identity(ROOT),
        "stages": {
            "protocol_identity": "PASS",
            "cycle_component_active_in_g1_logic": "PASS",
            "shared_state_indicators": "PASS",
            "p1_implementation": "PASS",
            "p2_implementation": "PASS",
            "conflict_occupancy": "PASS",
            "conviction": "PASS",
            "forecaster_implementation": "PASS",
            "seven_configurations": "PASS",
            "staged_selection_guard": "PASS",
            "scoring_adjudication": "PASS",
            "source_manifest_bindings": "PASS",
            "replay_ui_integration": "PASS",
            "execution_guard": "PASS",
        },
        "synthetic_tests": {"files": SYNTHETIC_TESTS, "total": sum(SYNTHETIC_TESTS.values())},
        "historical_execution_authorized": False,
        "real_historical_g1_outcomes_inspected": False,
        "new_market_data_accessed": False,
        "forecaster_real_fitted": False,
        "p1_p2_real_performance_computed": False,
        "sealed_queries": 0,
        "validated_strategy": None,
        "operational_action": "NO_TRADE",
        "champion": "NONE",
        "real_money": False,
    }


def main() -> None:
    path = ROOT / OUTPUT
    path.write_text(json.dumps(record(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
