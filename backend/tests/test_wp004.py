import json
from copy import deepcopy

import pytest
from app.research.continuation_lab import PROFILES
from app.research.evaluation_protocol import load_protocol, protocol_hash
from app.research.runner import declared_content_identity, sha256
from app.research.wp004 import ROOT, SPEC, dependency_manifest, preflight, validate_identity


def declaration():
    config_path = "research/configs/wp004/aligned.json"
    plan = [
        {
            "trial_id": f"ALIGNED:{profile}",
            "config_path": config_path,
            "config_sha256": sha256(ROOT / config_path),
        }
        for profile in PROFILES
    ]
    strategy = ROOT / "backend/app/research/continuation.py"
    protocol = load_protocol()
    return {
        "experiment_id": "EXP-ALG-009-ALIGNED",
        "trial_budget": 4,
        "seeds": [0],
        "code_config_reference": declared_content_identity(strategy, plan),
        "parameter_space": {
            "trial_plan": plan,
            "dependencies": dependency_manifest(),
            "strategy_path": "backend/app/research/continuation.py",
            "strategy_sha256": sha256(strategy),
            "walk_forward": protocol,
            "protocol_sha256": protocol_hash(protocol),
            "family_id": "FAM-BREAKOUT",
            "hypothesis_id": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
            "primary_family_variant": "ALIGNED",
        },
    }


def test_exact_bounded_identity_and_dependency_closure():
    validate_identity(declaration())
    assert len(SPEC) == 3
    assert "backend/app/backtest/engine.py" in {entry["path"] for entry in dependency_manifest()}


@pytest.mark.parametrize("change", ["fourth_profile", "dependency", "schedule", "primary"])
def test_scientific_identity_drift_is_rejected(change):
    record = deepcopy(declaration())
    if change == "fourth_profile":
        record["parameter_space"]["trial_plan"][-1]["trial_id"] = "ALIGNED:DELAY_2H"
    elif change == "dependency":
        record["parameter_space"]["dependencies"][0]["sha256"] = "0" * 64
    elif change == "schedule":
        record["parameter_space"]["walk_forward"]["purge_hours"] = 1
    else:
        record["parameter_space"]["primary_family_variant"] = "REGIME_ONLY"
    with pytest.raises(ValueError):
        validate_identity(record)


def test_runner_cannot_replay_existing_or_uncommitted_research():
    # Before preregistration: missing admissions/dirty checkout. Afterwards: existing attempt/results.
    # This test never passes the gate and never loads market data.
    if (
        all((ROOT / f"research/experiments/{eid}/preregistration.json").exists() for eid in SPEC)
        and not (ROOT / "research/runs/WP-004-ATTEMPT.json").exists()
    ):
        return  # The deliberate, committed pre-run state is legitimately executable.
    with pytest.raises(ValueError):
        preflight()


def test_configs_exactly_match_declared_variants():
    assert {
        json.loads((ROOT / f"research/configs/wp004/{stem}.json").read_text())["variant"]
        for _, stem in SPEC.values()
    } == {"REGIME_ONLY", "PARTICIPATION_ONLY", "ALIGNED"}
