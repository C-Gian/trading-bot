from __future__ import annotations

from dataclasses import replace

import pytest
from app.research.model_search_memory import admit_model_spec, bind_model_spec
from app.research.search_memory import SearchMemoryError
from app.research.wp008 import executable_spec


def signature(experiment_id: str, spec):
    binding = bind_model_spec(spec)
    return {
        "experiment_id": experiment_id,
        "root_family": spec.root_family,
        "behavior_hash": binding.behavior_hash,
        "structural_hash": binding.structural_hash,
    }


def test_model_gate_detects_duplicate_and_numeric_drift() -> None:
    spec = executable_spec("LINEAR_FULL")
    prior = [signature("EXISTING", spec)]
    with pytest.raises(SearchMemoryError, match="DUPLICATE"):
        admit_model_spec(
            spec,
            declared_family=spec.root_family,
            signatures=prior,
            aliases={},
        )
    drift = replace(
        spec,
        signal_rule={"field": "predicted_default_net_R", "operator": ">", "threshold": 0.1},
    )
    with pytest.raises(SearchMemoryError, match="PARAMETER_VARIANT"):
        admit_model_spec(
            drift,
            declared_family=spec.root_family,
            signatures=prior,
            aliases={},
        )


def test_no_flow_is_structural_descendant_not_new_root() -> None:
    full = executable_spec("LINEAR_FULL")
    no_flow = executable_spec("LINEAR_NO_FLOW")
    decision = admit_model_spec(
        no_flow,
        declared_family=no_flow.root_family,
        signatures=[signature("EXP-ML-014-LINEAR-NET-R-FULL", full)],
        aliases={},
    )
    assert decision["classification"] == "DESCENDANT_MECHANISM_CHANGE"
    assert decision["matched_experiment_ids"] == ["EXP-ML-014-LINEAR-NET-R-FULL"]
