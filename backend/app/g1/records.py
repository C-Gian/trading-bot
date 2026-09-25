"""Minimal versioned System G1 domain records (core contracts sections 2-14).

Every record is a frozen dataclass whose collection fields are tuples, so an issued record cannot be
mutated in place. Identities are content-derived (`canonical.content_id`). Records are appended to
an `EventStore`, which refuses to overwrite or re-issue an identity with different content.

This is deliberately BTCUSDT/System G1 specific: no generic asset or strategy framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from . import (
    ALGORITHM_VERSION,
    DECISION_TIMEFRAME,
    EVIDENCE_CLASS,
    FORECAST_HORIZON_MINUTES,
    GENERATION,
    REFERENCE_INSTRUMENT,
    SCHEMA_VERSION,
)

Reasons = tuple[str, ...]
Pairs = tuple[tuple[str, float | str | None], ...]


class SignalRole(StrEnum):
    ACTIVE = "ACTIVE"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    DIAGNOSTIC = "DIAGNOSTIC"
    METHOD_NOT_READY = "METHOD_NOT_READY"


class Bias(StrEnum):
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    BULLISH = "BULLISH"


class StructuralMode(StrEnum):
    TREND = "TREND"
    RANGE = "RANGE"
    TRANSITION = "TRANSITION"
    UNAVAILABLE = "UNAVAILABLE"


class Direction(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"
    UNAVAILABLE = "UNAVAILABLE"


class Conviction(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Action(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"

    @property
    def sign(self) -> int:
        return 1 if self is Side.LONG else -1


class Playbook(StrEnum):
    P1 = "SYSTEM-G1-P1-DIRECTIONAL-CONTINUATION"
    P2 = "SYSTEM-G1-P2-FAILED-AUCTION-REENTRY"


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    configuration_id: str
    configuration_version: str
    source_manifests: tuple[tuple[str, str], ...]
    dataset_start: datetime
    dataset_end: datetime
    cost_contract_version: str
    risk_contract_version: str
    cycle_method_version: str
    provenance: str
    generation: str = GENERATION
    algorithm_version: str = ALGORITHM_VERSION
    schema_version: str = SCHEMA_VERSION
    decision_clock: str = DECISION_TIMEFRAME
    forecast_horizon_minutes: int = FORECAST_HORIZON_MINUTES
    reference_instrument: str = REFERENCE_INSTRUMENT
    evidence_class: str = EVIDENCE_CLASS


@dataclass(frozen=True)
class SignalSnapshot:
    signal_id: str
    run_id: str
    family: str
    name: str
    version: str
    market_time: datetime
    available_at: datetime
    timeframe: str
    values: Pairs
    state: str
    quality: str
    role: SignalRole
    reason_code: str
    reason: str
    source_refs: Reasons = ()


@dataclass(frozen=True)
class TurnEvent:
    kind: str
    estimated_turn_time: datetime
    confirmation_time: datetime


@dataclass(frozen=True)
class CycleScaleState:
    nominal_scale: str
    input_resolution: str
    period_min: int
    period_max: int
    bars_seen: int
    warmup_bars: int
    warmup_ready: bool
    gap_state: str
    dominant_period_bars: float | None
    dominant_period_minutes: float | None
    power_hash: str | None
    quality_metrics: Pairs
    quality_label: str
    coordinate: float | None
    phase_estimate_diagnostic: float | None
    slope_direction: str
    last_confirmed_turn: TurnEvent | None
    method_version: str
    limitations: Reasons


@dataclass(frozen=True)
class CycleState:
    cycle_state_id: str
    run_id: str
    market_time: datetime
    available_at: datetime
    method_version: str
    method_status: str
    decision_role: SignalRole
    timing_qualifier: str
    group_summary: Pairs
    scales: tuple[CycleScaleState, ...]


@dataclass(frozen=True)
class MarketState:
    market_state_id: str
    run_id: str
    decision_time: datetime
    available_at: datetime
    directional_bias: Bias
    structural_mode: StructuralMode
    structure_1h: str
    context_4h: str
    daily_context: str
    location: str
    participation: str
    cycle_summary: str
    data_ready: bool
    supporting_reasons: Reasons
    opposing_reasons: Reasons
    signal_ids: Reasons
    cycle_state_id: str
    state_source: str


@dataclass(frozen=True)
class ModelArtifact:
    model_artifact_id: str
    estimator: str
    version: str
    fitted: bool
    training_interval: tuple[str, str] | None
    calibration_status: str
    conditioning_cells: Reasons
    limitations: Reasons


@dataclass(frozen=True)
class Actionability:
    setup_ready: bool
    data_ready: bool
    execution_ready: bool
    risk_eligible: bool
    occupancy_free: bool
    final_decision: Action
    blockers: Reasons


@dataclass(frozen=True)
class PredictionSnapshot:
    prediction_id: str
    run_id: str
    issue_time: datetime
    information_cutoff: datetime
    available_at: datetime
    target_end: datetime
    reference_price: Decimal | None
    directional_bias: Bias
    predicted_direction: Direction
    probability_up: float | None
    probability_down: float | None
    probability_status: str
    mean_terminal_return: float | None
    median_terminal_return: float | None
    lower_quantile_return: float | None
    upper_quantile_return: float | None
    quantile_levels: tuple[float, float]
    standardized_strength: float | None
    prior_risk_scale: float | None
    support_status: str
    conviction: Conviction
    actionability: Actionability
    playbook_context: Reasons
    supporting_reasons: Reasons
    opposing_reasons: Reasons
    market_state_id: str
    cycle_state_id: str
    model_artifact_id: str
    unavailable_reason: str | None
    decision_timeframe: str = DECISION_TIMEFRAME
    reference_instrument: str = REFERENCE_INSTRUMENT
    algorithm_version: str = ALGORITHM_VERSION
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class PredictionRealization:
    realization_id: str
    prediction_id: str
    resolution_time: datetime
    available_at: datetime
    resolution_validity: str
    realized_terminal_return: float | None
    realized_direction: str | None
    direction_correct: bool | None
    magnitude_error: float | None
    interval_covered: bool | None
    probability_score: str
    baseline_scores: Pairs


@dataclass(frozen=True)
class DecisionSnapshot:
    decision_id: str
    run_id: str
    prediction_id: str
    market_state_id: str
    decision_time: datetime
    available_at: datetime
    action: Action
    playbook_id: str | None
    conviction: Conviction
    actionability: Actionability
    blockers: Reasons
    trade_plan_id: str | None


@dataclass(frozen=True)
class TradePlan:
    trade_plan_id: str
    run_id: str
    decision_id: str
    side: Side
    playbook_id: str
    playbook_version: str
    trigger_time: datetime
    readiness_time: datetime
    operational_delay_minutes: int
    entry_order_rule: str
    entry_expiry: datetime
    reference_price: Decimal
    stop_price: Decimal
    objective_price: Decimal
    max_hold_minutes: int
    planned_reward_risk: Decimal
    cost_contract_version: str
    funding_assumption: str
    virtual_equity: Decimal
    planned_risk_amount: Decimal
    max_notional: Decimal
    quantity_rule: str
    conviction: Conviction
    supporting_reasons: Reasons
    opposing_reasons: Reasons
    data_quality: str
    reference_instrument: str = REFERENCE_INSTRUMENT


class FillKind(StrEnum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    FUNDING = "FUNDING"
    ENTRY_REJECTED = "ENTRY_REJECTED"


@dataclass(frozen=True)
class OrderFillEvent:
    event_id: str
    trade_plan_id: str
    kind: FillKind
    side: Side
    event_time: datetime
    available_at: datetime
    raw_price: Decimal | None
    effective_price: Decimal | None
    quantity: Decimal | None
    fee: Decimal
    friction_cost: Decimal
    funding_amount: Decimal
    reason: str


@dataclass(frozen=True)
class ClosedTrade:
    trade_id: str
    trade_plan_id: str
    side: Side
    playbook_id: str
    entry_time: datetime
    exit_time: datetime
    entry_raw_price: Decimal
    exit_raw_price: Decimal
    entry_effective_price: Decimal
    exit_effective_price: Decimal
    quantity: Decimal
    notional: Decimal
    gross_price_pnl: Decimal
    fees: Decimal
    friction_cost: Decimal
    funding: Decimal
    net_pnl: Decimal
    initial_risk_amount: Decimal
    net_r: Decimal
    exit_reason: str
    scorable: bool
    holding_minutes: int


@dataclass(frozen=True)
class LedgerSnapshot:
    as_of: datetime
    equity: Decimal
    peak_equity: Decimal
    drawdown_fraction: Decimal
    day_start_equity: Decimal
    day_loss_fraction: Decimal
    open_trade_plan_id: str | None
    open_side: Side | None
    open_quantity: Decimal
    unrealized_pnl: Decimal
    daily_entry_stop: bool
    run_entry_stop: bool


@dataclass(frozen=True)
class HotWindow:
    hot_window_id: str
    run_id: str
    start: datetime
    end: datetime
    trigger: str
    source_record_ids: Reasons
    created_after_run_completion: bool = True


@dataclass(frozen=True)
class PostAnalysisReport:
    report_id: str
    run_id: str
    hot_window_ids: Reasons
    status: str
    explanation_sources: Reasons
    limitations: Reasons
    decision_graph_input: bool = False


@dataclass(frozen=True)
class ResearchExposureRecord:
    exposure_id: str
    run_id: str
    evidence_class: str
    real_market_data_read: bool
    market_outcomes_inspected: bool
    sealed_queries: int
    configurations_inspected: int
    notes: Reasons = field(default_factory=tuple)
