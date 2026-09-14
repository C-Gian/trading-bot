"""Causal prospective paper execution on a real, already-observed future fill.

``PAPER_EXECUTION_V2_CAUSAL_NEXT_MINUTE`` is intentionally separate from the blocked
V1 paper-entry workflow and from the frozen historical backtester.  Its input starts at
the minute whose open was observed only after a durable paper intent existed.  The
fixed 2% stop, 4% target and 1,440-minute horizon are anchored to that actual fill.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ..backtest.models import Bar, CostModel, ExitReason, TradeRecord

PAPER_EXECUTION_VERSION = "PAPER_EXECUTION_V2_CAUSAL_NEXT_MINUTE"
PAPER_ENGINE_VERSION = "PROSPECTIVE_PAPER_ENGINE_V2"
ENTRY_TIMING_RULE = "STRICTLY_AFTER_DURABLE_INTENT_NEXT_1M_OPEN"
AMBIGUOUS_FILL_POLICY = "STOP_FIRST_V1"
MAX_HOLD_MINUTES = 1440
BPS = Decimal(10000)
MINUTE = timedelta(minutes=1)


@dataclass(frozen=True)
class CausalPaperPlan:
    """A filled plan whose entry minute and fixed geometry are already persisted."""

    run_id: str
    strategy_reference: str
    dataset_manifest_id: str
    dataset_content_hash: str
    entry_timestamp: datetime
    stop: Decimal
    target: Decimal
    max_hold_minutes: int = MAX_HOLD_MINUTES

    def __post_init__(self) -> None:
        if self.entry_timestamp.tzinfo is None:
            raise ValueError("paper entry timestamp must be timezone-aware")
        utc = self.entry_timestamp.astimezone(UTC)
        if utc.second or utc.microsecond:
            raise ValueError("paper entry timestamp must be a UTC minute boundary")
        if not 1 <= self.max_hold_minutes <= MAX_HOLD_MINUTES:
            raise ValueError("holding horizon exceeds approved maximum")


def _versions() -> dict[str, str]:
    return {
        "engine_version": PAPER_ENGINE_VERSION,
        "execution_model_version": PAPER_EXECUTION_VERSION,
    }


def _unresolved(plan: CausalPaperPlan, reason: ExitReason) -> TradeRecord:
    return TradeRecord(
        schema_version=1,
        run_id=plan.run_id,
        strategy_reference=plan.strategy_reference,
        dataset_manifest_id=plan.dataset_manifest_id,
        dataset_content_hash=plan.dataset_content_hash,
        signal_timestamp=plan.entry_timestamp,
        entry_timestamp=None,
        entry_raw_price=None,
        entry_effective_price=None,
        stop=plan.stop,
        target=plan.target,
        target_exit_rule="FIXED_TARGET_OR_STOP_OR_24H",
        expiry_timestamp=None,
        exit_timestamp=None,
        exit_reason=reason,
        exit_raw_price=None,
        exit_effective_price=None,
        entry_fee=None,
        exit_fee=None,
        entry_execution_friction=None,
        exit_execution_friction=None,
        gross_pnl=None,
        net_pnl=None,
        initial_price_risk=None,
        gross_r=None,
        net_r=None,
        holding_minutes=None,
        data_quality_status=(
            "INVALID"
            if reason in {ExitReason.INVALID_MISSING_ENTRY_BAR, ExitReason.INVALID_NON_TRADABLE}
            else "UNRESOLVED"
        ),
        suppressed_signal_count=0,
        **_versions(),
    )


def _unresolved_after_entry(
    plan: CausalPaperPlan,
    reason: ExitReason,
    entry_bar: Bar,
    entry_effective: Decimal,
    entry_fee: Decimal,
    expiry: datetime,
    costs: CostModel,
) -> TradeRecord:
    return replace(
        _unresolved(plan, reason),
        entry_timestamp=entry_bar.open_time,
        entry_raw_price=entry_bar.open,
        entry_effective_price=entry_effective,
        expiry_timestamp=expiry,
        entry_fee=entry_fee,
        entry_execution_friction=entry_effective - entry_bar.open,
        initial_price_risk=entry_bar.open - plan.stop,
        cost_model_version=costs.profile,
    )


def simulate_causal_paper(
    plan: CausalPaperPlan,
    bars: Iterable[Bar],
    costs: CostModel = CostModel(),
) -> TradeRecord:
    """Resolve a filled V2 paper plan without translating its real timestamps."""
    path = tuple(bars)
    if any(bar.open_time.tzinfo is None for bar in path):
        raise ValueError("paper path timestamps must be timezone-aware")
    if not path or path[0].open_time != plan.entry_timestamp:
        return _unresolved(plan, ExitReason.INVALID_MISSING_ENTRY_BAR)
    entry_bar = path[0]
    entry_raw = entry_bar.open
    if plan.stop >= entry_raw or plan.target <= entry_raw:
        return _unresolved(plan, ExitReason.INVALID_NON_TRADABLE)
    entry_effective = entry_raw * (BPS + costs.entry_friction_bps) / BPS
    entry_fee = entry_effective * costs.entry_fee_bps / BPS
    expiry = entry_bar.open_time + timedelta(minutes=plan.max_hold_minutes)
    previous = entry_bar.open_time - MINUTE
    exit_raw = None
    exit_time = None
    reason = ExitReason.UNRESOLVED_END_OF_DATA
    for bar in path:
        if bar.open_time != previous + MINUTE:
            return _unresolved_after_entry(
                plan,
                ExitReason.UNRESOLVED_DATA_GAP,
                entry_bar,
                entry_effective,
                entry_fee,
                expiry,
                costs,
            )
        previous = bar.open_time
        stop_hit = bar.low <= plan.stop
        target_hit = bar.high >= plan.target
        if bar.open < plan.stop:
            exit_raw, exit_time, reason = bar.open, bar.open_time, ExitReason.STOP_GAP
            break
        if bar.open >= plan.target:
            exit_raw, exit_time, reason = plan.target, bar.open_time, ExitReason.TARGET
            break
        if stop_hit:
            exit_raw, exit_time, reason = plan.stop, bar.open_time, ExitReason.STOP
            break
        if target_hit:
            exit_raw, exit_time, reason = plan.target, bar.open_time, ExitReason.TARGET
            break
        if bar.open_time + MINUTE >= expiry:
            exit_raw, exit_time, reason = (
                bar.close,
                bar.open_time + MINUTE,
                ExitReason.EXPIRY,
            )
            break
    if exit_raw is None or exit_time is None:
        return _unresolved_after_entry(
            plan, reason, entry_bar, entry_effective, entry_fee, expiry, costs
        )
    exit_effective = exit_raw * (BPS - costs.exit_friction_bps) / BPS
    exit_fee = exit_effective * costs.exit_fee_bps / BPS
    gross = exit_raw - entry_raw
    net = exit_effective - entry_effective - entry_fee - exit_fee
    risk = entry_raw - plan.stop
    return TradeRecord(
        1,
        plan.run_id,
        plan.strategy_reference,
        plan.dataset_manifest_id,
        plan.dataset_content_hash,
        plan.entry_timestamp,
        entry_bar.open_time,
        entry_raw,
        entry_effective,
        plan.stop,
        plan.target,
        "FIXED_TARGET_OR_STOP_OR_24H",
        expiry,
        exit_time,
        reason,
        exit_raw,
        exit_effective,
        entry_fee,
        exit_fee,
        entry_effective - entry_raw,
        exit_raw - exit_effective,
        gross,
        net,
        risk,
        gross / risk,
        net / risk,
        int((exit_time - entry_bar.open_time).total_seconds() / 60),
        "VALID",
        0,
        cost_model_version=costs.profile,
        **_versions(),
    )
