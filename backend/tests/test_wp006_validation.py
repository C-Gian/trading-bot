"""The WP-006 audit must reject tampering with any saved evidence or counter."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from app.research.evaluation_protocol import load_protocol
from app.research.wp006 import ROOT
from app.research.wp006_validation import (
    read_json,
    validate_sealed_state,
    validate_trade,
    validate_trial,
    validate_wp006,
)

CORE = "research/experiments/EXP-ALG-010-PULLBACK-RECOVERY-CORE/trials.json"
CONFIRM = "research/experiments/EXP-ALG-011-PULLBACK-RECOVERY-CONFIRM/trials.json"


@pytest.fixture
def trial():
    return read_json(ROOT / CORE)[0]


def test_repository_checkpoint_validates():
    result = validate_wp006()
    assert result["status"] == "PASS"
    assert result["novelty_classification"] == "NEW_FAMILY"
    assert result["variants"] == 2 and result["profile_trials"] == 8
    assert result["numeric_parameter_variants"] == 0
    assert result["family_terminal_classification"] == result["classifications"]["RECOVERY_CORE"]
    assert result["sealed"]["candidates"] >= 11
    assert result["sealed"]["seal_eligible"] == 0
    assert result["cumulative"]["sealed_queries"] == 0


def test_saved_evidence_reconciles_without_market_rerun(trial):
    validate_trial(trial, "RECOVERY_CORE", "DEFAULT", load_protocol())
    validate_trial(read_json(ROOT / CONFIRM)[0], "RECOVERY_CONFIRM", "DEFAULT", load_protocol())


@pytest.mark.parametrize(
    "mutation", ["timing", "occupancy", "barriers", "pnl", "profile", "pullback", "regime"]
)
def test_corrupt_trade_evidence_fails(trial, mutation):
    trade = deepcopy(trial["trades"][0])
    if mutation == "timing":
        trade["feature_asof_us"] += 1
    elif mutation == "occupancy":
        trade["position_available_us"] -= 60_000_000
    elif mutation == "barriers":
        trade["record"]["stop"] = "1"
    elif mutation == "pnl":
        trade["net_r"] += 1
    elif mutation == "profile":
        trade["record"]["cost_model_version"] = "BTCUSDT_SPOT_COST_V1_ZERO"
    elif mutation == "pullback":
        trade["feature_values"]["previous_close"] = trade["feature_values"]["sma24_previous"] + 1
    elif mutation == "regime":
        trade["regime"] = "OTHER"
    with pytest.raises(ValueError):
        validate_trade(trade, "RECOVERY_CORE", "DEFAULT")


def test_an_undeclared_feature_cannot_be_smuggled_into_a_trade(trial):
    trade = deepcopy(trial["trades"][0])
    trade["feature_values"]["relative_volume"] = 2.0
    with pytest.raises(ValueError, match="undeclared feature"):
        validate_trade(trade, "RECOVERY_CORE", "DEFAULT")


def test_confirmation_gate_cannot_be_claimed_without_evidence():
    trade = deepcopy(read_json(ROOT / CONFIRM)[0]["trades"][0])
    validate_trade(trade, "RECOVERY_CONFIRM", "DEFAULT")
    trade["feature_values"]["exceeds_previous_high"] = False
    with pytest.raises(ValueError, match="confirmation gate"):
        validate_trade(trade, "RECOVERY_CONFIRM", "DEFAULT")


def test_summary_and_clock_accounting_cannot_drift(trial):
    corrupted = deepcopy(trial)
    corrupted["summary"]["metrics"]["net_expectancy_r"] = 10
    with pytest.raises(ValueError, match="summary"):
        validate_trial(corrupted, "RECOVERY_CORE", "DEFAULT", load_protocol())
    corrupted = deepcopy(trial)
    corrupted["clock_diagnostics"][0]["suppressed_conditions"] += 1
    with pytest.raises(ValueError, match="accounting"):
        validate_trial(corrupted, "RECOVERY_CORE", "DEFAULT", load_protocol())


def _sealed_mirror(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for relative in (
        "research/sealed/SEALED_QUERY_BUDGET.json",
        "research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json",
        "research/sealed/BTCUSDT_POST_CUTOFF/CONSUMPTION_LEDGER.jsonl",
        "research/memory/LEGACY_EXECUTABLE_SIGNATURES_V2.json",
        "research/memory/ADMISSION_LEDGER_V2.jsonl",
        "research/memory/OUTCOMES.jsonl",
        "research/memory/OUTCOMES_V2.jsonl",
        "research/memory/SEARCH_LEDGER.jsonl",
        "research/memory/HYPOTHESIS_FAMILIES.json",
        "research/memory/SEARCH_BUDGET.json",
        "research/memory/registry/ledger/WP-007.jsonl",
        "research/memory/registry/outcomes/WP-007.jsonl",
        "research/memory/registry/ledger/WP-008.jsonl",
        "research/memory/registry/outcomes/WP-008.jsonl",
        "research/memory/registry/ledger/WP-011.jsonl",
        "research/memory/registry/outcomes/WP-011.jsonl",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relative, target)
    (root / "research/sealed/BTCUSDT_POST_CUTOFF/results").mkdir(parents=True)
    for name in ("data/raw", "data/canonical", "data/derived"):
        (root / name).mkdir(parents=True)
    for experiment in read_json(ROOT / "research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json")[
        "candidates"
    ]:
        path = root / experiment["development_result_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / experiment["development_result_path"], path)
    return root


def test_sealed_state_is_locked_at_zero(tmp_path: Path):
    root = _sealed_mirror(tmp_path)
    sealed = validate_sealed_state(root)
    assert sealed["candidates"] >= 11 and sealed["seal_eligible"] == 0


def test_a_materialized_sealed_dataset_is_rejected(tmp_path: Path):
    root = _sealed_mirror(tmp_path)
    (root / "data/sealed").mkdir(parents=True)
    with pytest.raises(ValueError, match="reserved sealed dataset was materialized"):
        validate_sealed_state(root)


def test_a_post_cutoff_market_file_is_rejected(tmp_path: Path):
    root = _sealed_mirror(tmp_path)
    (root / "data/raw/BTCUSDT-1m-2025-01.zip").write_bytes(b"")
    with pytest.raises(ValueError, match="post-cutoff market file"):
        validate_sealed_state(root)


def test_an_unlocked_or_consumed_btc_scope_is_rejected(tmp_path: Path):
    root = _sealed_mirror(tmp_path)
    path = root / "research/sealed/SEALED_QUERY_BUDGET.json"
    budget = json.loads(path.read_text(encoding="utf-8"))
    budget["scopes"]["BTCUSDT_POST_CUTOFF"]["authorized_queries"] = 1
    path.write_text(json.dumps(budget, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="not locked at zero"):
        validate_sealed_state(root)


def test_a_fabricated_sealed_result_is_rejected(tmp_path: Path):
    root = _sealed_mirror(tmp_path)
    (root / "research/sealed/BTCUSDT_POST_CUTOFF/results/FAKE.json").write_text("{}")
    with pytest.raises(ValueError, match="sealed result exists"):
        validate_sealed_state(root)


def test_a_hand_edited_eligibility_table_is_rejected(tmp_path: Path):
    root = _sealed_mirror(tmp_path)
    path = root / "research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json"
    table = json.loads(path.read_text(encoding="utf-8"))
    for row in table["candidates"]:
        if row["experiment_id"] == "EXP-ALG-009-ALIGNED":
            row["sealed_eligibility"] = "DEVELOPMENT_ELIGIBLE_PENDING"
    path.write_text(json.dumps(table, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not reproducible"):
        validate_sealed_state(root)
