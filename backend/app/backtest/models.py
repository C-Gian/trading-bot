from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.data.policy import CUTOFF

from . import COST_VERSION, ENGINE_VERSION, EXECUTION_VERSION

D = Decimal
TEN_BPS = D("10")
TWO_BPS = D("2")


class ExitReason(StrEnum):
    TARGET = "TARGET"
    STOP = "STOP"
    STOP_GAP = "STOP_GAP"
    EXPIRY = "EXPIRY"
    INVALID_MISSING_ENTRY_BAR = "INVALID_MISSING_ENTRY_BAR"
    UNRESOLVED_DATA_GAP = "UNRESOLVED_DATA_GAP"
    UNRESOLVED_END_OF_DATA = "UNRESOLVED_END_OF_DATA"


@dataclass(frozen=True)
class Bar:
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    complete: bool = True


@dataclass(frozen=True)
class CostModel:
    profile: str = COST_VERSION
    entry_fee_bps: Decimal = TEN_BPS
    exit_fee_bps: Decimal = TEN_BPS
    entry_friction_bps: Decimal = TWO_BPS
    exit_friction_bps: Decimal = TWO_BPS

    def __post_init__(self) -> None:
        if (
            min(
                self.entry_fee_bps,
                self.exit_fee_bps,
                self.entry_friction_bps,
                self.exit_friction_bps,
            )
            < 0
        ):
            raise ValueError("cost components must be non-negative")


@dataclass(frozen=True)
class Intent:
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
        if self.entry_timing_rule != "NEXT_1M_OPEN":
            raise ValueError("unsupported entry timing")
        if not 1 <= self.max_hold_minutes <= 1440:
            raise ValueError("holding horizon exceeds approved maximum")
        if self.signal_timestamp.tzinfo is None or self.signal_timestamp > CUTOFF:
            raise ValueError("signal timestamp exceeds development boundary")


@dataclass(frozen=True)
class TradeRecord:
    schema_version: int
    run_id: str
    strategy_reference: str
    dataset_manifest_id: str
    dataset_content_hash: str
    signal_timestamp: datetime
    entry_timestamp: datetime | None
    entry_raw_price: Decimal | None
    entry_effective_price: Decimal | None
    stop: Decimal
    target: Decimal | None
    target_exit_rule: str | None
    expiry_timestamp: datetime | None
    exit_timestamp: datetime | None
    exit_reason: ExitReason
    exit_raw_price: Decimal | None
    exit_effective_price: Decimal | None
    entry_fee: Decimal | None
    exit_fee: Decimal | None
    entry_execution_friction: Decimal | None
    exit_execution_friction: Decimal | None
    gross_pnl: Decimal | None
    net_pnl: Decimal | None
    initial_price_risk: Decimal | None
    gross_r: Decimal | None
    net_r: Decimal | None
    holding_minutes: int | None
    data_quality_status: str
    suppressed_signal_count: int
    engine_version: str = ENGINE_VERSION
    execution_model_version: str = EXECUTION_VERSION
    cost_model_version: str = COST_VERSION

    def deterministic_dict(self) -> dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat().replace("+00:00", "Z")
            if isinstance(value, Decimal):
                return format(value, "f")
            if isinstance(value, StrEnum):
                return value.value
            return value

        return {key: convert(value) for key, value in asdict(self).items()}
