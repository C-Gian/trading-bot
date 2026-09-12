from __future__ import annotations

import json

import pytest
from app.research.nfci_context import CONTEXT_VERSION, NFCIContextError, load_nfci_context
from app.research.supervised import FULL_FEATURES
from app.research.wp004 import ROOT
from app.research.wp013 import (
    CONTROL_VARIANT,
    INTERACTION_FEATURES,
    PRIMARY_FEATURES,
    PRIMARY_VARIANT,
    preflight,
)
from app.research.wp013_lab import ContextRow


def test_context_feature_structure_changes_only_interactions() -> None:
    base = tuple(float(i) / 10 for i in range(1, 9))
    first = ContextRow(0, 1.0, -1.0, base)
    second = ContextRow(0, 1.0, 2.0, base)
    assert first.values(CONTROL_VARIANT) == second.values(CONTROL_VARIANT) == base
    assert first.values(PRIMARY_VARIANT)[:8] == second.values(PRIMARY_VARIANT)[:8] == base
    assert first.values(PRIMARY_VARIANT)[8:] == tuple(-value for value in base)
    assert second.values(PRIMARY_VARIANT)[8:] == tuple(2 * value for value in base)
    assert PRIMARY_FEATURES == FULL_FEATURES + INTERACTION_FEATURES
    assert len(INTERACTION_FEATURES) == 8
    assert "NFCI" not in PRIMARY_FEATURES


def test_wp013_protocol_is_exactly_frozen() -> None:
    protocol = json.loads(
        (ROOT / "research/protocols/WP-013-CONTEXTUAL-NFCI-INTERACTIONS-V1.json").read_text()
    )
    assert protocol["context"]["version"] == CONTEXT_VERSION
    assert protocol["context"]["direct_feature_count"] == 0
    assert protocol["context"]["thresholds"] == 0
    assert protocol["features"]["base"] == list(FULL_FEATURES)
    assert len(protocol["features"]["interactions"]) == 8
    assert protocol["training"]["purge_boundary_hours"] == 216


def test_wp013_preflight_passes() -> None:
    assert preflight(ROOT)["status"] == "PASS"


def test_nfci_context_rejects_post_cutoff() -> None:
    source = load_nfci_context(ROOT)
    with pytest.raises(NFCIContextError):
        source.at(1735689600000000)
