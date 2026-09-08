import json
from pathlib import Path

import jsonschema
import pytest
from app.research.records import RecordValidationError, validate_result
from app.research.runner import (
    declared_content_identity,
    deterministic_run_identity,
    finalize_result,
    run_declared_trials,
    run_fixture,
    sha256,
)

ROOT = Path(__file__).resolve().parents[2]


def load_schema(name):
    return json.loads((ROOT / "contracts" / name).read_text())


def prereg():
    return {
        "schema_version": 2,
        "experiment_id": "SYNTHETIC_TEST",
        "experiment_version": 1,
        "created_at_utc": "2020-01-01T00:00:00Z",
        "hypothesis": "synthetic fixture",
        "rationale": "validate infrastructure",
        "research_scope": "synthetic only",
        "dataset": {
            "manifest_id": "SYNTHETIC-DATA",
            "content_hash": "b" * 64,
            "maximum_timestamp": "2020-01-31T00:00:00Z",
        },
        "metrics": {"primary": "fixture_value", "secondary": ["fixture_count"]},
        "evaluation_design": "single deterministic fixture",
        "leakage_controls": ["synthetic bounded input"],
        "cost_execution_reference": "EXECUTION_MODEL_V1",
        "parameter_space": {},
        "trial_budget": 1,
        "stopping_rule": "one trial",
        "seeds": [7],
        "code_config_reference": "SYNTHETIC_CONFIG_V1",
        "status": "PREREGISTERED",
    }


def result():
    return {
        "schema_version": 2,
        "experiment_id": "SYNTHETIC_TEST",
        "experiment_version": 1,
        "preregistration_reference": "SYNTHETIC_TEST",
        "preregistration_created_at_utc": "2020-01-01T00:00:00Z",
        "completed_at_utc": "2020-01-02T00:00:00Z",
        "status": "COMPLETED",
        "code_config_reference": "SYNTHETIC_CONFIG_V1",
        "dataset": {"manifest_id": "SYNTHETIC-DATA", "content_hash": "b" * 64},
        "seed_reference": [7],
        "primary_result": 1,
        "secondary_results": {"fixture_count": 1},
        "artifacts": [],
        "validation_outcome": "PASS",
        "interpretation": "fixture only",
        "trial_accounting": {"declared_budget": 1, "executed_trials": 1},
        "run_identity_hash": "c" * 64,
    }


def write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_prereg_schema_requires_primary_metric_and_budget():
    schema = load_schema("experiment_preregistration.schema.json")
    jsonschema.validate(prereg(), schema)
    for mutate in (lambda p: p["metrics"].pop("primary"), lambda p: p.pop("trial_budget")):
        bad = prereg()
        mutate(bad)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)


def test_real_cross_record_validator_and_orphan(tmp_path):
    pre = write(tmp_path / "prereg.json", prereg())
    res = write(tmp_path / "result.json", result())
    assert validate_result(res, pre)["experiment_id"] == "SYNTHETIC_TEST"
    with pytest.raises(RecordValidationError):
        validate_result(res, tmp_path / "missing.json")


@pytest.mark.parametrize("change", ["version", "identity", "predates", "budget", "seed"])
def test_cross_record_mismatches_fail(tmp_path, change):
    p = prereg()
    r = result()
    if change == "version":
        r["experiment_version"] = 2
    if change == "identity":
        r["dataset"]["content_hash"] = "d" * 64
    if change == "predates":
        r["completed_at_utc"] = "2019-01-01T00:00:00Z"
    if change == "budget":
        r["trial_accounting"]["executed_trials"] = 2
    if change == "seed":
        r["seed_reference"] = [99]
    with pytest.raises(RecordValidationError):
        validate_result(write(tmp_path / "r.json", r), write(tmp_path / "p.json", p))


def test_finalized_result_cannot_be_overwritten(tmp_path):
    p = write(tmp_path / "p.json", prereg())
    destination = tmp_path / "result.json"
    finalize_result(result(), p, destination)
    with pytest.raises(FileExistsError):
        finalize_result(result(), p, destination)


def test_runner_enforces_budget_and_is_reproducibly_identified(tmp_path):
    p = write(tmp_path / "p.json", prereg())
    manifest = write(
        tmp_path / "manifest.json",
        {
            "manifest_id": "SYNTHETIC-DATA",
            "content_hash": {"value": "b" * 64},
            "coverage": {"end": "2020-01-31T00:00:00Z"},
        },
    )
    config = {"reference": "SYNTHETIC_CONFIG_V1", "fixture": 1}
    versions = {
        "engine": "BACKTEST_ENGINE_V1",
        "execution": "EXECUTION_MODEL_V1",
        "cost": "BTCUSDT_SPOT_COST_V1",
    }
    assert deterministic_run_identity(
        prereg(), "abc", config, versions
    ) == deterministic_run_identity(prereg(), "abc", config, versions)
    adapter = lambda _: {"primary_result": 1, "secondary_results": {"fixture_count": 1}}
    with pytest.raises(RecordValidationError):
        run_fixture(
            p,
            tmp_path / "bad.json",
            manifest,
            "abc",
            config,
            versions,
            "2020-01-02T00:00:00Z",
            2,
            adapter,
        )
    completed = run_fixture(
        p,
        tmp_path / "ok.json",
        manifest,
        "abc",
        config,
        versions,
        "2020-01-02T00:00:00Z",
        1,
        adapter,
    )
    assert completed["validation_outcome"] == "PASS"


def test_malformed_dataset_manifest_fails():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"symbol": "BTCUSDT"}, load_schema("dataset_manifest.schema.json"))


def test_production_runner_owns_declared_trial_iteration_and_identity(tmp_path):
    manifest_path = ROOT / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    manifest = json.loads(manifest_path.read_text())
    strategy = tmp_path / "strategy.py"
    config = tmp_path / "config.json"
    strategy.write_text("RULE = 'fixed'\n")
    config.write_text('{"fixed": true}')
    plan = [
        {
            "trial_id": trial_id,
            "config_path": str(config),
            "config_sha256": sha256(config),
        }
        for trial_id in ("fixed-a", "fixed-b")
    ]
    payload = prereg()
    payload.update(
        {
            "dataset": {
                "manifest_id": manifest["manifest_id"],
                "content_hash": manifest["content_hash"]["value"],
                "maximum_timestamp": manifest["coverage"]["end"],
            },
            "trial_budget": 2,
            "seeds": [1, 2],
            "parameter_space": {
                "strategy_path": str(strategy),
                "strategy_sha256": sha256(strategy),
                "trial_plan": plan,
            },
            "code_config_reference": declared_content_identity(strategy, plan),
        }
    )
    path = write(tmp_path / "prereg.json", payload)
    seen = []

    def adapter(configuration, trial_id):
        seen.append(trial_id)
        return {"fixed": configuration["fixed"]}

    trials = run_declared_trials(path, manifest_path, adapter)
    assert seen == ["fixed-a", "fixed-b"]
    assert [trial["trial_id"] for trial in trials] == seen

    bad = json.loads(json.dumps(payload))
    bad["parameter_space"]["trial_plan"].append(
        {"trial_id": "undeclared", "config_path": str(config), "config_sha256": sha256(config)}
    )
    with pytest.raises(RecordValidationError):
        run_declared_trials(write(tmp_path / "undeclared.json", bad), manifest_path, adapter)

    strategy.write_text("RULE = 'changed'\n")
    with pytest.raises(RecordValidationError):
        run_declared_trials(path, manifest_path, adapter)


@pytest.mark.parametrize(
    "timestamp",
    ["2024-12-31T20:30:00-05:00", "2025-01-01T00:00:00"],
)
def test_preregistration_rejects_offset_or_naive_cutoff_bypass(tmp_path, timestamp):
    from app.research.records import validate_preregistration

    payload = prereg()
    payload["dataset"]["maximum_timestamp"] = timestamp
    with pytest.raises(RecordValidationError):
        validate_preregistration(write(tmp_path / "prereg.json", payload))
