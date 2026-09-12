"""PROSPECTIVE_PAPER_EXECUTION_V1 must match the frozen engine exactly.

The prospective adapter exists only so forward paper evidence carries real timestamps.
Every scenario below is run through both implementations over identical pre-cutoff
fixtures and must agree field for field, so the adapter can never silently drift from
`EXECUTION_MODEL_V2`.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from app.backtest.engine import simulate
from app.backtest.models import Bar, CostModel, ExitReason, Intent
from app.data.policy import CUTOFF
from app.product.execution import (
    AMBIGUOUS_FILL_POLICY,
    ENTRY_TIMING_RULE,
    PROSPECTIVE_ENGINE_VERSION,
    PROSPECTIVE_EXECUTION_VERSION,
    ProspectiveIntent,
    simulate_prospective,
)

ROOT = Path(__file__).resolve().parents[2]
PRE_CUTOFF = datetime(2024, 6, 3, 12, tzinfo=UTC)
POST_CUTOFF = datetime(2026, 3, 5, 12, tzinfo=UTC)
REFERENCE = Decimal(50000)
STOP = REFERENCE * Decimal("0.98")
TARGET = REFERENCE * Decimal("1.04")
IDENTITY: dict[str, Any] = {
    "run_id": "EQUIVALENCE",
    "strategy_reference": "ALIGNED_PARTICIPATION_CONTINUATION_V1:ALIGNED",
    "dataset_manifest_id": "FIXTURE",
    "dataset_content_hash": "FIXTURE",
    "direction": "LONG",
    "entry_timing_rule": ENTRY_TIMING_RULE,
    "stop": STOP,
    "target": TARGET,
    "target_exit_rule": "FIXED_TARGET_OR_STOP_OR_24H",
    "max_hold_minutes": 1440,
}
# Version fields are expected to differ: that is the whole point of the separate adapter.
VERSION_FIELDS = ("engine_version", "execution_model_version")


def _bar(signal: datetime, index: int, opened, high, low, close) -> Bar:
    return Bar(
        signal + timedelta(minutes=index),
        Decimal(str(opened)),
        Decimal(str(high)),
        Decimal(str(low)),
        Decimal(str(close)),
    )


def _flat(signal: datetime, count: int) -> list[Bar]:
    return [_bar(signal, i, 50000, 50100, 49900, 50000) for i in range(count)]


def _scenarios(signal: datetime) -> dict[str, list[Bar]]:
    """One deterministic fixture per execution rule the contract fixes."""
    target = _flat(signal, 10)
    target[3] = _bar(signal, 3, 50000, TARGET + 500, 49900, TARGET)

    stop = _flat(signal, 10)
    stop[2] = _bar(signal, 2, 50000, 50100, STOP - 100, STOP)

    gap_open_below_stop = _flat(signal, 10)
    gap_open_below_stop[2] = _bar(signal, 2, 48900, 49500, 48000, 48500)

    open_above_target = _flat(signal, 10)
    open_above_target[4] = _bar(signal, 4, TARGET + 900, TARGET + 1200, TARGET, TARGET + 1000)

    ambiguous = _flat(signal, 10)
    ambiguous[4] = _bar(signal, 4, 50000, TARGET + 10, STOP - 10, 50000)

    gapped = _flat(signal, 10)
    del gapped[4]

    entry_touches_both = _flat(signal, 10)
    entry_touches_both[0] = _bar(signal, 0, 50000, TARGET + 10, STOP - 10, 50000)

    return {
        "target": target,
        "stop": stop,
        "stop_gap_open": gap_open_below_stop,
        "open_above_target": open_above_target,
        "ambiguous_stop_first": ambiguous,
        "expiry": _flat(signal, 1441),
        "unresolved_gap": gapped,
        "unresolved_end_of_data": _flat(signal, 10),
        "missing_entry_bar": _flat(signal, 10)[3:],
        "entry_bar_touches_both": entry_touches_both,
    }


def _comparable(record) -> dict:
    payload = record.deterministic_dict()
    for field in VERSION_FIELDS:
        payload.pop(field)
    return payload


def _both(name: str, signal: datetime = PRE_CUTOFF, costs: CostModel = CostModel()):
    bars = _scenarios(signal)[name]
    frozen = simulate(Intent(signal_timestamp=signal, **IDENTITY), bars, costs)
    prospective = simulate_prospective(
        ProspectiveIntent(signal_timestamp=signal, **IDENTITY), bars, costs
    )
    return frozen, prospective


# --- exact equivalence -----------------------------------------------------------


@pytest.mark.parametrize("scenario", sorted(_scenarios(PRE_CUTOFF)))
def test_prospective_adapter_matches_the_frozen_engine_exactly(scenario: str) -> None:
    frozen, prospective = _both(scenario)
    assert _comparable(prospective) == _comparable(frozen)


def test_entry_price_and_time_agree() -> None:
    frozen, prospective = _both("target")
    assert prospective.entry_timestamp == frozen.entry_timestamp == PRE_CUTOFF
    assert prospective.entry_raw_price == frozen.entry_raw_price
    assert prospective.entry_effective_price == frozen.entry_effective_price
    assert prospective.entry_execution_friction == frozen.entry_execution_friction


def test_target_and_stop_outcomes_agree() -> None:
    for scenario, reason in (
        ("target", ExitReason.TARGET),
        ("open_above_target", ExitReason.TARGET),
        ("stop", ExitReason.STOP),
        ("stop_gap_open", ExitReason.STOP_GAP),
    ):
        frozen, prospective = _both(scenario)
        assert prospective.exit_reason == frozen.exit_reason == reason
        assert prospective.exit_raw_price == frozen.exit_raw_price
        assert prospective.exit_timestamp == frozen.exit_timestamp


def test_ambiguous_bar_resolves_stop_first_in_both() -> None:
    for scenario in ("ambiguous_stop_first", "entry_bar_touches_both"):
        frozen, prospective = _both(scenario)
        assert prospective.exit_reason == frozen.exit_reason == ExitReason.STOP
        assert prospective.exit_raw_price == frozen.exit_raw_price == STOP
    assert AMBIGUOUS_FILL_POLICY == "STOP_FIRST_V1"


def test_expiry_agrees_at_the_full_horizon() -> None:
    frozen, prospective = _both("expiry")
    assert prospective.exit_reason == frozen.exit_reason == ExitReason.EXPIRY
    assert prospective.holding_minutes == frozen.holding_minutes == 1440
    assert (
        prospective.exit_timestamp == frozen.exit_timestamp == PRE_CUTOFF + timedelta(minutes=1440)
    )
    assert prospective.expiry_timestamp == frozen.expiry_timestamp


def test_realized_r_and_cost_semantics_agree() -> None:
    for scenario in ("target", "stop", "stop_gap_open", "expiry"):
        frozen, prospective = _both(scenario)
        assert prospective.net_r == frozen.net_r
        assert prospective.gross_r == frozen.gross_r
        assert prospective.net_pnl == frozen.net_pnl
        assert prospective.gross_pnl == frozen.gross_pnl
        assert prospective.initial_price_risk == frozen.initial_price_risk
        assert prospective.entry_fee == frozen.entry_fee and prospective.exit_fee == frozen.exit_fee
        assert prospective.cost_model_version == frozen.cost_model_version


def test_gap_and_missing_data_conservatism_agrees() -> None:
    for scenario, reason, quality in (
        ("unresolved_gap", ExitReason.UNRESOLVED_DATA_GAP, "UNRESOLVED"),
        ("unresolved_end_of_data", ExitReason.UNRESOLVED_END_OF_DATA, "UNRESOLVED"),
        ("missing_entry_bar", ExitReason.INVALID_MISSING_ENTRY_BAR, "INVALID"),
    ):
        frozen, prospective = _both(scenario)
        assert prospective.exit_reason == frozen.exit_reason == reason
        assert prospective.data_quality_status == frozen.data_quality_status == quality
        assert prospective.net_r is frozen.net_r is None
        assert prospective.exit_timestamp is frozen.exit_timestamp is None


def test_non_tradable_intent_agrees() -> None:
    bars = _flat(PRE_CUTOFF, 5)
    identity = {**IDENTITY, "stop": Decimal(60000)}
    frozen = simulate(Intent(signal_timestamp=PRE_CUTOFF, **identity), bars)
    prospective = simulate_prospective(
        ProspectiveIntent(signal_timestamp=PRE_CUTOFF, **identity), bars
    )
    assert prospective.exit_reason == frozen.exit_reason == ExitReason.INVALID_NON_TRADABLE
    assert _comparable(prospective) == _comparable(frozen)


def test_double_cost_profile_also_agrees() -> None:
    costs = CostModel(
        profile="DOUBLE",
        entry_fee_bps=Decimal(20),
        exit_fee_bps=Decimal(20),
        entry_friction_bps=Decimal(4),
        exit_friction_bps=Decimal(4),
    )
    for scenario in ("target", "stop", "expiry"):
        frozen, prospective = _both(scenario, costs=costs)
        assert _comparable(prospective) == _comparable(frozen)


# --- cutoff separation -----------------------------------------------------------


def test_the_frozen_engine_remains_cutoff_protected() -> None:
    bars = _flat(POST_CUTOFF, 5)
    with pytest.raises(ValueError, match="development boundary"):
        Intent(signal_timestamp=POST_CUTOFF, **IDENTITY)
    with pytest.raises(ValueError, match="exceeds development boundary"):
        simulate(Intent(signal_timestamp=PRE_CUTOFF, **IDENTITY), bars)


def test_the_prospective_adapter_accepts_real_post_cutoff_timestamps() -> None:
    assert POST_CUTOFF > CUTOFF
    bars = _scenarios(POST_CUTOFF)["target"]
    record = simulate_prospective(ProspectiveIntent(signal_timestamp=POST_CUTOFF, **IDENTITY), bars)
    assert record.data_quality_status == "VALID"
    assert record.signal_timestamp == POST_CUTOFF
    assert record.entry_timestamp == POST_CUTOFF
    assert record.exit_timestamp == POST_CUTOFF + timedelta(minutes=3)
    assert record.engine_version == PROSPECTIVE_ENGINE_VERSION
    assert record.execution_model_version == PROSPECTIVE_EXECUTION_VERSION


def test_post_cutoff_results_are_identical_to_the_same_shape_pre_cutoff() -> None:
    """Only the instants differ; the adapter has no hidden date dependence."""
    for scenario in sorted(_scenarios(PRE_CUTOFF)):
        pre = simulate_prospective(
            ProspectiveIntent(signal_timestamp=PRE_CUTOFF, **IDENTITY),
            _scenarios(PRE_CUTOFF)[scenario],
        )
        post = simulate_prospective(
            ProspectiveIntent(signal_timestamp=POST_CUTOFF, **IDENTITY),
            _scenarios(POST_CUTOFF)[scenario],
        )
        offset = POST_CUTOFF - PRE_CUTOFF
        assert post.exit_reason == pre.exit_reason
        assert post.data_quality_status == pre.data_quality_status
        assert post.net_r == pre.net_r
        if pre.exit_timestamp is not None:
            assert post.exit_timestamp == pre.exit_timestamp + offset


def test_prospective_intent_rejects_naive_or_off_hour_clocks() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ProspectiveIntent(signal_timestamp=datetime(2026, 3, 5, 12), **IDENTITY)  # noqa: DTZ001
    with pytest.raises(ValueError, match="UTC hour boundary"):
        ProspectiveIntent(signal_timestamp=POST_CUTOFF + timedelta(minutes=7), **IDENTITY)
    with pytest.raises(ValueError, match="holding horizon"):
        ProspectiveIntent(signal_timestamp=POST_CUTOFF, **{**IDENTITY, "max_hold_minutes": 1441})
    with pytest.raises(ValueError, match="only LONG"):
        ProspectiveIntent(signal_timestamp=POST_CUTOFF, **{**IDENTITY, "direction": "SHORT"})


def test_naive_path_timestamps_are_refused() -> None:
    naive = [Bar(datetime(2026, 3, 5, 12), REFERENCE, REFERENCE, REFERENCE, REFERENCE)]  # noqa: DTZ001
    with pytest.raises(ValueError, match="timezone-aware"):
        simulate_prospective(ProspectiveIntent(signal_timestamp=POST_CUTOFF, **IDENTITY), naive)


# --- separation from development code --------------------------------------------


def test_no_research_or_backtest_module_imports_the_prospective_adapter() -> None:
    offenders = []
    for path in sorted((ROOT / "backend/app").rglob("*.py")):
        if path.parts[-2] == "product":
            continue
        source = path.read_text(encoding="utf-8")
        if "product.execution" in source or "simulate_prospective" in source:
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_the_adapter_never_reaches_development_storage_or_sealed_data() -> None:
    source = (ROOT / "backend/app/product/execution.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    app_modules = {name for name in modules if "backtest" in name or "research" in name}
    assert app_modules == {"backtest.models"}
    assert not {name for name in modules if "data.store" in name or "sealed" in name}
    assert "data/canonical" not in source and "data/derived" not in source
    for forbidden in ("api_key", "secret", "order", "withdraw", "leverage", "margin"):
        assert forbidden not in source.lower()
