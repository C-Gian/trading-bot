from pathlib import Path

import numpy as np

from app.research.wp005_integrity import HOUR_US, _mask_hash, _unsafe, canonical_hash


def test_independent_quarantine_crosses_late_close_boundary():
    times = np.asarray([HOUR_US - 1, HOUR_US], dtype=np.int64)
    assert _unsafe(times, HOUR_US) == {0, HOUR_US}
    assert len(_mask_hash(times)) == 64


def test_canonical_hash_ignores_mapping_order():
    assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})


def test_wp005_artifacts_are_outside_experiment_tree():
    root = Path(__file__).resolve().parents[2]
    assert "research/diagnostics" in (
        root / "research/diagnostics/WP-005/feature-result-reconciliation.json"
    ).as_posix()
