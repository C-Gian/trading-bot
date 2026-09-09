import json
import shutil
from pathlib import Path

import pytest
from app.research.adaptive import ROOT, validate_adaptive


def test_cumulative_accounting_keeps_prior_search_visible():
    result = validate_adaptive()
    assert result["profile_trials"] >= 41
    assert result["adaptive_decisions"] == result["result_dependent_forks"] == 1
    assert result["sealed_queries"] == 0


@pytest.mark.parametrize(
    "field,value", [("allocated_structural_variants", 4), ("sealed_queries", 1)]
)
def test_undeclared_allocation_is_rejected(tmp_path: Path, field, value):
    target = tmp_path / "research/memory"
    target.mkdir(parents=True)
    source = ROOT / "research/memory/ADAPTIVE_DECISIONS.json"
    shutil.copy(source, target / source.name)
    payload = json.loads(source.read_text())
    payload["decisions"][0][field] = value
    (target / source.name).write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="allocation"):
        validate_adaptive(tmp_path)
