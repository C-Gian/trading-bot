"""`PROSPECTIVE_PAPER_EXECUTION_V1`: forward paper execution on real timestamps.

The frozen historical simulator (`BACKTEST_ENGINE_V2`) correctly refuses clocks after
the development cutoff, so WP-010A/B1 translated post-cutoff instants onto an
in-development anchor. That workaround must not stand behind genuine forward paper
evidence, so this adapter reproduces the frozen execution semantics exactly while
working on real current timestamps.

It is deliberately separate from `app.backtest`: the historical engine is untouched and
stays cutoff-protected, and nothing here may be used to produce development evidence.
`backend/tests/test_prospective_execution.py` pins the equivalence by running both
implementations over the same pre-cutoff fixtures and requiring identical records.

Semantics held identical to `EXECUTION_MODEL_V2`:

- entry at `NEXT_1M_OPEN_EXECUTION`, the first 1m open at the signal instant, plus
  adverse entry friction;
- an open below the stop exits at that adverse open, otherwise a low touching the stop
  exits at the stop;
- a high touching the target exits at the target, and an open at or above the target
  still fills at the target rather than at a better price;
- a minute touching both resolves `STOP_FIRST_V1`;
- expiry exits at the close of the minute reaching the 1,440 minute horizon;
- a non-consecutive minute is `UNRESOLVED_DATA_GAP` and the end of data is
  `UNRESOLVED_END_OF_DATA`; neither manufactures an outcome.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from ..backtest.models import Bar, CostModel, ExitReason, TradeRecord

PROSPECTIVE_EXECUTION_VERSION = "PROSPECTIVE_PAPER_EXECUTION_V1"
PROSPECTIVE_ENGINE_VERSION = "PROSPECTIVE_PAPER_ENGINE_V1"
ENTRY_TIMING_RULE = "NEXT_1M_OPEN"
AMBIGUOUS_FILL_POLICY = "STOP_FIRST_V1"
MAX_HOLD_MINUTES = 1440
BPS = Decimal(10000)
MINUTE = timedelta(minutes=1)


@dataclass(frozen=True)
class ProspectiveIntent:
    """Mirrors the frozen `Intent` but carries a real, un-translated signal instant."""

    run_id: str
    strategy_reference: str
    dataset_manifest_id: str
    dataset_content_hash: str
    signal_timestamp: datetime
    direction: str
    entry_timing_rule: str
    stop: Decimal
    target: Decimal | None
    target_exit_rule: str | None
    max_hold_minutes: int

    def __post_init__(self) -> None:
        if self.direction != "LONG":
            raise ValueError("only LONG intents are supported")
        if self.entry_timing_rule != ENTRY_TIMING_RULE:
            raise ValueError("unsupported entry timing")
        if not 1 <= self.max_hold_minutes <= MAX_HOLD_MINUTES:
            raise ValueError("holding horizon exceeds approved maximum")
        if self.signal_timestamp.tzinfo is None:
            raise ValueError("prospective signal timestamp must be timezone-aware")
        utc = self.signal_timestamp.astimezone(UTC)
        if utc.minute or utc.second or utc.microsecond:
            raise ValueError("signal must occur on a UTC hour boundary")


def _versions() -> dict[str, str]:
    return {
        "engine_version": PROSPECTIVE_ENGINE_VERSION,
        "execution_model_version": PROSPECTIVE_EXECUTION_VERSION,
    }


def _unresolved(intent: ProspectiveIntent, reason: ExitReason) -> TradeRecord:
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
        **_versions(),
    )


def _unresolved_after_entry(
    intent: ProspectiveIntent,
    reason: ExitReason,
    entry_bar: Bar,
    entry_effective: Decimal,
    entry_fee: Decimal,
    expiry: datetime,
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


def simulate_prospective(
    intent: ProspectiveIntent,
    bars: Iterable[Bar],
    costs: CostModel = CostModel(),
) -> TradeRecord:
    """Resolve a forward paper trade under `EXECUTION_MODEL_V2` semantics."""
    path = tuple(bars)
    if any(bar.open_time.tzinfo is None for bar in path):
        raise ValueError("prospective path timestamps must be timezone-aware")
    if not path or path[0].open_time != intent.signal_timestamp:
        return _unresolved(intent, ExitReason.INVALID_MISSING_ENTRY_BAR)
    entry_bar = path[0]
    entry_raw = entry_bar.open
    if intent.stop >= entry_raw or (intent.target is not None and intent.target <= entry_raw):
        return _unresolved(intent, ExitReason.INVALID_NON_TRADABLE)
    entry_effective = entry_raw * (BPS + costs.entry_friction_bps) / BPS
    entry_fee = entry_effective * costs.entry_fee_bps / BPS
    expiry = entry_bar.open_time + timedelta(minutes=intent.max_hold_minutes)
    previous = entry_bar.open_time - MINUTE
    exit_raw = None
    exit_time = None
    reason = ExitReason.UNRESOLVED_END_OF_DATA
    for bar in path:
        if bar.open_time != previous + MINUTE:
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
        if bar.open_time + MINUTE >= expiry:
            exit_raw, exit_time, reason = (
                bar.close,
                bar.open_time + MINUTE,
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
        0,
        cost_model_version=costs.profile,
        **_versions(),
    )
