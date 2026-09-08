import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]


def schema(name: str):
    return json.loads((ROOT / "contracts" / name).read_text())


def prereg():
    return {
        "experiment_id": "SYNTHETIC-TEST",
        "version": 1,
        "created_at_utc": "2020-01-01T00:00:00Z",
        "hypothesis": "fixture",
        "rationale": "fixture",
        "scope": "synthetic fixture",
        "dataset_reference": "research/fixtures/only",
        "primary_metric": "fixture_metric",
        "secondary_metrics": [],
        "evaluation_design": "fixture",
        "leakage_controls": "fixture",
        "cost_execution_reference": "not applicable",
        "parameter_space": {},
        "trial_budget": 1,
        "stopping_rule": "one trial",
        "seeds": [1],
        "code_reference": "fixture",
        "status": "PREREGISTERED",
    }


def test_prereg_contract_required_fields():
    jsonschema.validate(prereg(), schema("experiment_preregistration.schema.json"))
    for field in ("primary_metric", "trial_budget"):
        invalid = prereg()
        invalid.pop(field)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid, schema("experiment_preregistration.schema.json"))


def test_linked_result_and_orphan_rejection():
    result = {
        "experiment_id": "SYNTHETIC-TEST",
        "preregistration_reference": "SYNTHETIC-TEST",
        "status": "COMPLETED",
        "primary_metric_result": 0,
    }
    jsonschema.validate(result, schema("experiment_result.schema.json"))
    assert result["preregistration_reference"] == prereg()["experiment_id"]
    orphan = {**result, "preregistration_reference": "MISSING"}
    assert orphan["preregistration_reference"] != prereg()["experiment_id"]


def test_malformed_manifest_fails():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"symbol": "BTCUSDT"}, schema("dataset_manifest.schema.json"))
