from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from app.data.policy import CUTOFF

from .models import Bar, CostModel, ExitReason, Intent, TradeRecord

BPS = Decimal(10000)


def _unresolved(intent: Intent, reason: ExitReason) -> TradeRecord:
    return TradeRecord(
        schema_version=1,
        run_id=intent.run_id,
        strategy_reference=intent.strategy_reference,
        dataset_manifest_id=intent.dataset_manifest_id,
        dataset_content_hash=intent.dataset_content_hash,
        signal_timestamp=intent.signal_timestamp,
        entry_timestamp=None,
        entry_raw_price=None,
        entry_effective_price=None,
        stop=intent.stop,
        target=intent.target,
        target_exit_rule=intent.target_exit_rule,
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
        data_quality_status="INVALID"
        if reason in {ExitReason.INVALID_MISSING_ENTRY_BAR, ExitReason.INVALID_NON_TRADABLE}
        else "UNRESOLVED",
        suppressed_signal_count=0,
    )


def _unresolved_after_entry(
    intent: Intent,
    reason: ExitReason,
    entry_bar: Bar,
    entry_effective: Decimal,
    entry_fee: Decimal,
    expiry,
    costs: CostModel,
) -> TradeRecord:
    return replace(
        _unresolved(intent, reason),
        entry_timestamp=entry_bar.open_time,
        entry_raw_price=entry_bar.open,
        entry_effective_price=entry_effective,
        expiry_timestamp=expiry,
        entry_fee=entry_fee,
        entry_execution_friction=entry_effective - entry_bar.open,
        initial_price_risk=entry_bar.open - intent.stop,
        cost_model_version=costs.profile,
    )


def simulate(
    intent: Intent,
    bars: Iterable[Bar],
    costs: CostModel = CostModel(),
    overlapping_signals: Iterable = (),
) -> TradeRecord:
    path = tuple(bars)
    if any(
        bar.open_time.tzinfo is None or bar.open_time.astimezone(CUTOFF.tzinfo) > CUTOFF
        for bar in path
    ):
        raise ValueError("canonical path timestamp exceeds development boundary")
    if not path or path[0].open_time != intent.signal_timestamp:
        return _unresolved(intent, ExitReason.INVALID_MISSING_ENTRY_BAR)
    entry_bar = path[0]
    entry_raw = entry_bar.open
    if intent.stop >= entry_raw or (intent.target is not None and intent.target <= entry_raw):
        return _unresolved(intent, ExitReason.INVALID_NON_TRADABLE)
    entry_effective = entry_raw * (BPS + costs.entry_friction_bps) / BPS
    entry_fee = entry_effective * costs.entry_fee_bps / BPS
    expiry = entry_bar.open_time + timedelta(minutes=intent.max_hold_minutes)
    previous = entry_bar.open_time - timedelta(minutes=1)
    exit_raw = None
    exit_time = None
    reason = ExitReason.UNRESOLVED_END_OF_DATA
    for bar in path:
        if bar.open_time != previous + timedelta(minutes=1):
            return _unresolved_after_entry(
                intent,
                ExitReason.UNRESOLVED_DATA_GAP,
                entry_bar,
                entry_effective,
                entry_fee,
                expiry,
                costs,
            )
        previous = bar.open_time
        stop_hit = bar.low <= intent.stop
        target_hit = intent.target is not None and bar.high >= intent.target
        if bar.open < intent.stop:
            exit_raw, exit_time, reason = bar.open, bar.open_time, ExitReason.STOP_GAP
            break
        if intent.target is not None and bar.open >= intent.target:
            exit_raw, exit_time, reason = intent.target, bar.open_time, ExitReason.TARGET
            break
        if stop_hit:
            exit_raw, exit_time, reason = intent.stop, bar.open_time, ExitReason.STOP
            break
        if target_hit:
            exit_raw, exit_time, reason = intent.target, bar.open_time, ExitReason.TARGET
            break
        if bar.open_time + timedelta(minutes=1) >= expiry:
            exit_raw, exit_time, reason = (
                bar.close,
                bar.open_time + timedelta(minutes=1),
                ExitReason.EXPIRY,
            )
            break
    if exit_raw is None or exit_time is None:
        return _unresolved_after_entry(
            intent, reason, entry_bar, entry_effective, entry_fee, expiry, costs
        )
    exit_effective = exit_raw * (BPS - costs.exit_friction_bps) / BPS
    exit_fee = exit_effective * costs.exit_fee_bps / BPS
    gross = exit_raw - entry_raw
    net = exit_effective - entry_effective - entry_fee - exit_fee
    risk = entry_raw - intent.stop
    suppressed = sum(intent.signal_timestamp < ts <= exit_time for ts in overlapping_signals)
    return TradeRecord(
        1,
        intent.run_id,
        intent.strategy_reference,
        intent.dataset_manifest_id,
        intent.dataset_content_hash,
        intent.signal_timestamp,
        entry_bar.open_time,
        entry_raw,
        entry_effective,
        intent.stop,
        intent.target,
        intent.target_exit_rule,
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
        suppressed,
        cost_model_version=costs.profile,
    )


def content_hash(record: TradeRecord) -> str:
    payload = json.dumps(record.deterministic_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
