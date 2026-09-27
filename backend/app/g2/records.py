"""Immutable G2-V0 domain/event records and canonical reason codes (contract sections 21-22).

Every record is a frozen dataclass whose first field is its stable identity and which carries the
instant `available_at` from which a causal consumer may see it. Identities derive from the run and
the event instant only, never from wall-clock time. Outcomes, labels, fills and closures are
separate later records: a prediction or decision is never rewritten when its outcome arrives.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

Terms = tuple[float | None, ...]


class Reason(StrEnum):
    # Forecast/data
    FORECAST_AVAILABLE = "FORECAST_AVAILABLE"
    FORECAST_UNAVAILABLE_WARMUP = "FORECAST_UNAVAILABLE_WARMUP"
    FORECAST_UNAVAILABLE_MISSING_DATA = "FORECAST_UNAVAILABLE_MISSING_DATA"
    FORECAST_UNAVAILABLE_INVALID_SIGMA = "FORECAST_UNAVAILABLE_INVALID_SIGMA"
    FORECAST_UNAVAILABLE_NO_MODEL = "FORECAST_UNAVAILABLE_NO_MODEL"
    TRAINING_TARGET_BASELINE_UNVALIDATED = "TRAINING_TARGET_BASELINE_UNVALIDATED"
    PREQUENTIAL_CDF_UNCALIBRATED = "PREQUENTIAL_CDF_UNCALIBRATED"
    # Policy
    LONG_SELECTED = "LONG_SELECTED"
    SHORT_SELECTED = "SHORT_SELECTED"
    UTILITY_MARGIN_NOT_POSITIVE = "UTILITY_MARGIN_NOT_POSITIVE"
    UTILITY_MARGIN_TIE = "UTILITY_MARGIN_TIE"
    INSUFFICIENT_POLICY_EVIDENCE = "INSUFFICIENT_POLICY_EVIDENCE"
    PATH_UTILITY_OVERRIDES_TERMINAL_VIEW = "PATH_UTILITY_OVERRIDES_TERMINAL_VIEW"
    # Risk/execution
    POSITION_ALREADY_OPEN = "POSITION_ALREADY_OPEN"
    PATH_DRAWDOWN_STOP_ACTIVE = "PATH_DRAWDOWN_STOP_ACTIVE"
    CONTRACT_FILTER_NOT_MET = "CONTRACT_FILTER_NOT_MET"
    EXECUTION_ENTRY_DATA_MISSING = "EXECUTION_ENTRY_DATA_MISSING"
    EXECUTION_EXIT_DATA_MISSING = "EXECUTION_EXIT_DATA_MISSING"
    FUNDING_DATA_INVALID = "FUNDING_DATA_INVALID"
    SOURCE_STALE_OR_INVALID = "SOURCE_STALE_OR_INVALID"
    # Cycle
    CYCLE_SHADOW_ONLY = "CYCLE_SHADOW_ONLY"
    CYCLE_UNRELIABLE = "CYCLE_UNRELIABLE"
    CYCLE_UNAVAILABLE = "CYCLE_UNAVAILABLE"


FORECAST_UNAVAILABLE = frozenset(
    {
        Reason.FORECAST_UNAVAILABLE_WARMUP,
        Reason.FORECAST_UNAVAILABLE_MISSING_DATA,
        Reason.FORECAST_UNAVAILABLE_INVALID_SIGMA,
        Reason.FORECAST_UNAVAILABLE_NO_MODEL,
    }
)


class Action(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


def _part(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def record_key(prefix: str, run_id: str, *parts: object) -> str:
    """Stable identity from the run and the event coordinates (never from wall time)."""
    text = "|".join((prefix, run_id, *(_part(part) for part in parts)))
    return f"{prefix}-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:24]}"


@dataclass(frozen=True)
class SourceAuditEvent:
    event_id: str
    run_id: str
    available_at: datetime
    kind: str  # METADATA_READ / OBSERVATION_READ / SYNTHETIC_SOURCE
    source: str
    requested_start: datetime | None
    requested_end: datetime | None
    opened_objects: tuple[str, ...]
    returned_start: datetime | None
    returned_end: datetime | None
    rows_returned: int
    exposure_class: str
    detail: str


@dataclass(frozen=True)
class FitManifest:
    fit_id: str
    run_id: str
    system_version: str
    head: str  # FORECAST / LONG_UTILITY / SHORT_UTILITY
    fit_boundary: datetime
    available_at: datetime
    status: str  # FITTED / UNAVAILABLE_SUPPORT
    support_detail: str
    training_start: datetime | None
    training_end: datetime | None
    rows: int
    latest_label_time: datetime | None
    target: str
    centers: Terms
    scales: Terms
    constant_columns: tuple[str, ...]
    intercept: float | None
    coefficients: Terms
    penalties: tuple[float, ...]
    fallback_atoms: int
    fallback_atoms_sha256: str | None
    source_hashes: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class MarketState:
    state_id: str
    run_id: str
    decision_time: datetime
    available_at: datetime
    max_source_time: datetime | None
    price: float | None
    raw_terms: Terms
    term_status: tuple[str, ...]
    price_response: float | None
    sigma_4h: float | None
    atr14_1h: float | None
    ewm: tuple[tuple[str, float | None], ...]
    daily: tuple[tuple[str, float | str | None], ...]
    weekly: tuple[tuple[str, float | str | None], ...]
    status: str  # AVAILABLE / FORECAST_UNAVAILABLE_*
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class Prediction:
    prediction_id: str
    run_id: str
    system_version: str
    decision_time: datetime
    available_at: datetime
    decision_id: str
    state_id: str
    fit_id: str | None
    source_hashes: tuple[tuple[str, str], ...]
    max_source_time: datetime | None
    training_start: datetime | None
    training_end: datetime | None
    latest_label_time: datetime | None
    target_time: datetime
    raw_terms: Terms
    scaled_terms: Terms
    contributions: Terms
    intercept: float | None
    mu_z: float | None
    mean_return: float | None
    median_return: float | None
    q10: float | None
    q50: float | None
    q90: float | None
    p_positive: float | None
    sigma_4h: float | None
    calibration_status: str
    residual_source: str
    residual_count: int
    view_strength_z: float | None
    strength_label: str | None
    direction: str  # UP / DOWN / NEUTRAL / UNAVAILABLE
    evidence_status: tuple[tuple[str, str | int | None], ...]
    reason_codes: tuple[str, ...]
    maturity_status: str  # always PENDING at issue; outcomes append later


@dataclass(frozen=True)
class PredictionOutcome:
    outcome_id: str
    prediction_id: str
    run_id: str
    decision_time: datetime
    target_time: datetime
    available_at: datetime
    status: str  # MATURED / TARGET_UNAVAILABLE
    realized_return: float | None
    realized_z: float | None
    residual_z: float | None
    residual_archived: bool


@dataclass(frozen=True)
class UtilityView:
    side: str
    fit_id: str | None
    predicted_utility: float | None
    residual_q10: float | None
    residual_count: int
    residual_span_days: float | None
    evidence_status: str  # PREQUENTIAL_READY / INSUFFICIENT / NO_MODEL / STATE_UNAVAILABLE
    prudential_margin: float | None


@dataclass(frozen=True)
class RiskSnapshot:
    equity: float  # realized research equity
    marked_equity: float  # latest causal mark (realized + open-position mark)
    peak_equity: float
    drawdown: float
    drawdown_stop_active: bool
    position_open: bool  # an actual open trade only (ENTRY_PENDING is Decision.position_state)
    open_trade_id: str | None


@dataclass(frozen=True)
class Decision:
    decision_id: str
    prediction_id: str
    run_id: str
    decision_time: datetime
    available_at: datetime
    action: Action
    policy_selection: str  # LONG_SELECTED / SHORT_SELECTED / NONE
    reason_codes: tuple[str, ...]
    long_utility: UtilityView
    short_utility: UtilityView
    forecast_direction: str
    position_state: str  # FLAT / OPEN / ENTRY_PENDING
    risk: RiskSnapshot
    stop_distance: float | None
    reference_price: float | None
    intended_entry_time: datetime | None
    intended_expiry_time: datetime | None
    cycle_role: str


@dataclass(frozen=True)
class ShadowLabel:
    label_id: str
    run_id: str
    decision_time: datetime
    side: str
    available_at: datetime
    status: str  # AVAILABLE / UNAVAILABLE
    reason_codes: tuple[str, ...]
    stop_distance: float | None
    raw_entry: float | None
    stop_price: float | None
    raw_exit: float | None
    exit_kind: str | None  # STOP / STOP_GAP / EXPIRY
    exit_time: datetime | None
    gross_pnl_per_unit: float | None
    friction_per_unit: float | None
    funding_per_unit: float | None
    funding_settlements: int
    net_pnl_per_unit: float | None
    net_r: float | None
    predicted_utility: float | None
    utility_residual: float | None
    utility_fit_id: str | None


@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    run_id: str
    decision_id: str
    side: str
    available_at: datetime
    intended_entry_time: datetime
    expires_before: datetime
    intended_expiry_time: datetime
    stop_distance: float
    reference_price: float
    reference_quantity: float
    order_type: str


@dataclass(frozen=True)
class SimulatedFill:
    fill_id: str
    run_id: str
    trade_id: str
    intent_id: str
    kind: str  # ENTRY / EXIT / ENTRY_REJECTED
    side: str
    event_time: datetime
    available_at: datetime
    raw_price: float | None
    accounting_price: float | None
    quantity: float
    friction_cost: float
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class FundingEvent:
    funding_id: str
    run_id: str
    trade_id: str
    funding_time: datetime
    available_at: datetime
    rate: float | None
    price_proxy: float | None
    price_proxy_kind: str
    quantity: float
    amount: float
    status: str  # SETTLED / FUNDING_DATA_INVALID
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class StopExpiryEvent:
    event_id: str
    run_id: str
    trade_id: str
    kind: str  # STOP / STOP_GAP / EXPIRY / EXPIRY_LATE_EXIT_DATA_MISSING
    event_time: datetime
    available_at: datetime
    trigger_price: float | None
    raw_exit: float
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ClosedTrade:
    trade_id: str
    run_id: str
    decision_id: str
    intent_id: str
    side: str
    available_at: datetime
    intended_entry_time: datetime
    entry_time: datetime
    raw_entry: float
    accounting_entry: float
    stop_price: float
    stop_distance: float
    intended_expiry_time: datetime
    exit_time: datetime
    raw_exit: float
    accounting_exit: float
    exit_kind: str
    quantity: float
    planned_risk: float
    friction_cost: float
    funding_pnl: float
    funding_events: tuple[str, ...]
    gross_pnl: float
    net_pnl: float
    realized_net_r: float
    entry_shortfall: float  # raw fill minus decision reference price (observable proxy)
    violation_flags: tuple[str, ...]


@dataclass(frozen=True)
class RiskStateEvent:
    risk_id: str
    run_id: str
    event_time: datetime
    available_at: datetime
    kind: str  # INITIAL / ENTRY / EXIT / FUNDING / DRAWDOWN_STOP_TRIGGERED
    equity: float  # realized research equity after the event
    marked_equity: float  # causal mark after the event
    mark_basis: str  # price basis of that mark
    peak_equity: float
    drawdown: float
    drawdown_stop_active: bool
    position_open: bool


@dataclass(frozen=True)
class CycleScaleShadow:
    nominal_scale: str
    input_resolution: str
    warmup_ready: bool
    gap_state: str
    quality_label: str
    dominant_period: float | None
    dominant_period_minutes: float | None
    phase_degrees: float | None
    projection_coordinate: float | None
    projection_amplitude: float | None
    explained_fraction: float | None
    period_stability: float | None
    slope_direction: str
    last_turn_kind: str | None
    last_turn_estimated_at: datetime | None
    last_turn_confirmed_at: datetime | None
    reason_code: str | None


@dataclass(frozen=True)
class CycleShadowState:
    cycle_id: str
    run_id: str
    decision_time: datetime
    available_at: datetime
    method_version: str
    runtime_role: str  # SHADOW_ONLY
    forecast_coefficients: int
    policy_coefficients: int
    veto_authority: str
    reason_codes: tuple[str, ...]
    scales: tuple[CycleScaleShadow, ...]


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    available_at: datetime
    system_version: str
    implementation_version: str
    evidence_class: str
    label: str
    dataset_start: datetime
    dataset_end: datetime
    source_hashes: tuple[tuple[str, str], ...]
    exchange_filters: tuple[tuple[str, float], ...]
    exchange_filters_sha256: str
    friction_scenario: str
    friction: float
    frozen: tuple[tuple[str, str], ...]


RECORD_TYPES = (
    SourceAuditEvent,
    FitManifest,
    MarketState,
    Prediction,
    PredictionOutcome,
    Decision,
    ShadowLabel,
    OrderIntent,
    SimulatedFill,
    FundingEvent,
    StopExpiryEvent,
    ClosedTrade,
    RiskStateEvent,
    CycleShadowState,
)
