from __future__ import annotations

from copy import deepcopy

import pytest
from app.research.checkpoint_views import build_comparison
from app.research.evaluation_protocol import load_protocol
from app.research.wp004 import ROOT
from app.research.wp004_validation import read_json, validate_trade, validate_trial


@pytest.fixture
def trial():
    return read_json(ROOT / "research/experiments/EXP-ALG-009-ALIGNED/trials.json")[0]


def test_saved_evidence_reconciles_without_market_rerun(trial):
    validate_trial(trial, "ALIGNED", "DEFAULT", load_protocol())


@pytest.mark.parametrize("mutation", ["fees", "timing", "occupancy", "barriers", "pnl", "profile"])
def test_corrupt_trade_evidence_fails(trial, mutation):
    trade = deepcopy(trial["trades"][0])
    if mutation == "fees":
        trade["record"]["entry_fee"] = "0"
    elif mutation == "timing":
        trade["feature_asof_us"] += 1
    elif mutation == "occupancy":
        trade["position_available_us"] -= 60_000_000
    elif mutation == "barriers":
        trade["record"]["stop"] = "1"
    elif mutation == "pnl":
        trade["net_r"] += 1
    elif mutation == "profile":
        trade["record"]["cost_model_version"] = "ZERO"
    with pytest.raises(ValueError):
        validate_trade(trade, "ALIGNED", "DEFAULT")


def test_summary_and_clock_accounting_cannot_drift(trial):
    corrupted = deepcopy(trial)
    corrupted["summary"]["metrics"]["net_expectancy_r"] = 10
    with pytest.raises(ValueError, match="summary"):
        validate_trial(corrupted, "ALIGNED", "DEFAULT", load_protocol())
    trial["clock_diagnostics"][0]["suppressed_conditions"] += 1
    with pytest.raises(ValueError, match="accounting"):
        validate_trial(trial, "ALIGNED", "DEFAULT", load_protocol())


def test_comparison_preserves_all_seeds_and_excludes_buy_hold():
    result = build_comparison()
    random = result["controls"]["EXP-CTRL-002-RANDOM"]["trials"]
    assert len(random) == len({t["seed"] for t in random}) == 32
    assert "EXP-BASE-001-BUYHOLD" not in result["controls"]
    assert result["new_strategy_trials"] == 0
    assert all(t["summary"]["protocol_sha256"] == result["protocol_sha256"] for t in random)
    assert (
        result["selected_family_terminal_classification"]
        == result["variants"]["ALIGNED"]["terminal_classification"]
    )
