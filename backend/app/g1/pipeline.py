"""Prediction / decision / realization pipeline (core contracts sections 4-9).

The synthetic emitter exercises the PredictionSnapshot contract with fixture-controlled values; it
fits nothing and claims no market skill. The decision logic is the generic contract logic shared
by every playbook: data readiness, a single agreeing proposal, HIGH conviction and the risk /
occupancy vetoes. It contains no P1/P2 trigger, location, invalidation or objective construction —
those remain for the Research Director's later freeze. Cycle state is read only through
`cycle.decision_timing_qualifier`, which is `CYCLE_METHOD_NOT_READY` until activation.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from .canonical import content_id
from .cycle import decision_timing_qualifier
from .fixtures import ScenarioStep
from .ledger import COST_CONTRACT_VERSION, ReferenceLedger
from .records import (
    Action,
    Actionability,
    Bias,
    Conviction,
    CycleState,
    DecisionSnapshot,
    Direction,
    MarketState,
    ModelArtifact,
    Playbook,
    PredictionRealization,
    PredictionSnapshot,
    SignalSnapshot,
    StructuralMode,
    TradePlan,
)

EMITTER_VERSION = "G1-CP1-SYNTHETIC-FIXTURE-EMITTER-V1"
PROBABILITY_STATUS = "UNCALIBRATED_SYNTHETIC_FIXTURE_VALUE_NOT_A_PROBABILITY"
QUANTILES = (0.1, 0.9)
PLAYBOOK_VERSION = "REGISTERED_INTERFACE_ONLY_CONSTRUCTION_NOT_FROZEN"
ENTRY_WINDOW = timedelta(minutes=15)
HORIZON = timedelta(minutes=240)


def synthetic_model_artifact() -> ModelArtifact:
    cells = tuple(f"{bias.value}x{conviction.value}" for bias in Bias for conviction in Conviction)
    payload = (EMITTER_VERSION, cells)
    return ModelArtifact(
        content_id("MOD", payload),
        "SYNTHETIC_FIXTURE_EMITTER",
        EMITTER_VERSION,
        False,
        None,
        PROBABILITY_STATUS,
        cells,
        (
            "NO_STATISTICAL_MODEL_FITTED",
            "VALUES_ARE_FIXTURE_CONTROLLED_CONTRACT_EXERCISES",
            "NOT_THE_SHRUNKEN_EMPIRICAL_G1_FORECASTER",
        ),
    )


def market_state(
    run_id: str,
    decision_time: datetime,
    step: ScenarioStep,
    signals: tuple[SignalSnapshot, ...],
    cycle: CycleState,
    ready: bool,
) -> MarketState:
    by_name = {signal.name: signal for signal in signals}
    context_4h = by_name["last_completed_4h_move"].state
    structure_1h = by_name["last_completed_1h_move"].state
    mode = step.mode if ready else StructuralMode.UNAVAILABLE
    payload = (
        run_id,
        decision_time,
        step,
        [s.signal_id for s in signals],
        cycle.cycle_state_id,
        ready,
    )
    return MarketState(
        content_id("MST", payload),
        run_id,
        decision_time,
        decision_time,
        step.bias,
        mode,
        structure_1h,
        context_4h,
        by_name["prior_completed_utc_day_range"].state,
        by_name["utc_session_vwap_completed_1m"].state,
        "NOT_IMPLEMENTED_IN_CHECKPOINT_1",
        decision_timing_qualifier(cycle),
        ready,
        step.supporting,
        step.opposing,
        tuple(s.signal_id for s in signals),
        cycle.cycle_state_id,
        "SYNTHETIC_FIXTURE_SCRIPT_PLUS_CAUSAL_PLUMBING",
    )


def actionability(
    step: ScenarioStep,
    ready: bool,
    unavailable: str | None,
    ledger: ReferenceLedger,
    cycle: CycleState,
) -> tuple[Actionability, Playbook | None]:
    # Checkpoint-1 scenario contract: fixture-scripted decisions never consult the cycle
    # qualifier (the frozen P1/P2 engine in `development.py` is the only cycle consumer).
    del cycle
    blockers: list[str] = []
    if not ready:
        blockers.append(unavailable or "DATA_NOT_READY")
    sides = {side for _, side in step.proposals}
    if not step.proposals:
        blockers.append("NO_APPROVED_SETUP")
    elif len(sides) > 1:
        blockers.append("CONFLICTING_PLAYBOOKS")
    if step.conviction is not Conviction.HIGH:
        blockers.append("CONVICTION_NOT_HIGH")
    setup_ready = bool(step.proposals) and len(sides) == 1 and step.conviction is Conviction.HIGH
    risk = ledger.entry_blockers()
    risk_eligible = not any(b != "POSITION_OCCUPIED" for b in risk)
    occupancy_free = "POSITION_OCCUPIED" not in risk
    blockers.extend(risk)
    if blockers:
        final = Action.NO_TRADE
        playbook = None
    else:
        playbook, side = min(step.proposals, key=lambda item: list(Playbook).index(item[0]))
        final = Action(side.value)
    return (
        Actionability(
            setup_ready, ready, ready, risk_eligible, occupancy_free, final, tuple(blockers)
        ),
        playbook,
    )


def prediction(
    run_id: str,
    decision_time: datetime,
    step: ScenarioStep,
    reference: Decimal | None,
    state: MarketState,
    cycle: CycleState,
    model: ModelArtifact,
    action: Actionability,
    unavailable: str | None,
) -> PredictionSnapshot:
    available = unavailable is None and reference is not None
    direction = step.direction if available else Direction.UNAVAILABLE

    def value(number: float) -> float | None:
        return number if available else None

    strength = step.mean_return / step.prior_risk_scale if available else None
    payload = (run_id, decision_time, step, reference, state.market_state_id, action, unavailable)
    return PredictionSnapshot(
        content_id("PRD", payload),
        run_id,
        decision_time,
        decision_time,
        decision_time,
        decision_time + HORIZON,
        reference,
        step.bias,
        direction,
        value(step.probability_up),
        value(1 - step.probability_up),
        PROBABILITY_STATUS if available else "UNAVAILABLE",
        value(step.mean_return),
        value(step.median_return),
        value(step.lower_return),
        value(step.upper_return),
        QUANTILES,
        strength,
        value(step.prior_risk_scale),
        "SYNTHETIC_FIXTURE_NO_EMPIRICAL_SUPPORT" if available else "UNAVAILABLE",
        step.conviction if available else Conviction.LOW,
        action,
        tuple(f"{playbook.value}:{side.value}" for playbook, side in step.proposals),
        step.supporting,
        step.opposing,
        state.market_state_id,
        cycle.cycle_state_id,
        model.model_artifact_id,
        None if available else (unavailable or "REFERENCE_PRICE_UNAVAILABLE"),
    )


def trade_plan(
    run_id: str,
    decision_id: str,
    decision_time: datetime,
    step: ScenarioStep,
    playbook: Playbook,
    action: Action,
    reference: Decimal,
    ledger: ReferenceLedger,
) -> TradePlan:
    from .records import Side

    side = Side(action.value)
    sign = Decimal(side.sign)
    stop = (reference * (1 - sign * Decimal(str(step.stop_fraction)))).quantize(Decimal("0.01"))
    objective = (reference * (1 + sign * Decimal(str(step.objective_fraction)))).quantize(
        Decimal("0.01")
    )
    policy = ledger.policy
    payload = (run_id, decision_id, side, playbook, reference, stop, objective)
    return TradePlan(
        content_id("PLN", payload),
        run_id,
        decision_id,
        side,
        playbook.value,
        PLAYBOOK_VERSION,
        decision_time,
        decision_time,
        policy.operational_delay_minutes,
        "NEXT_ELIGIBLE_1M_OPEN_AFTER_READINESS_PLUS_DELAY",
        decision_time + timedelta(minutes=policy.operational_delay_minutes) + ENTRY_WINDOW,
        reference,
        stop,
        objective,
        policy.max_hold_minutes,
        (Decimal(str(step.objective_fraction)) / Decimal(str(step.stop_fraction))).quantize(
            Decimal("0.0001")
        ),
        COST_CONTRACT_VERSION,
        "SIGNED_SETTLEMENT_FUNDING_AT_00_08_16_UTC",
        ledger.equity,
        ledger.equity * policy.risk_fraction,
        ledger.equity * policy.max_gross_notional_multiple,
        "DETERMINED_AT_FILL_0.25PCT_EQUITY_RISK_CAPPED_1X_NOTIONAL",
        step.conviction,
        step.supporting,
        step.opposing,
        "SYNTHETIC_FIXTURE_REFERENCE_PAPER_VALID",
    )


def decision(
    run_id: str,
    decision_time: datetime,
    predicted: PredictionSnapshot,
    action: Actionability,
    playbook: Playbook | None,
    plan_id_for: str | None,
) -> DecisionSnapshot:
    payload = (run_id, predicted.prediction_id, action, playbook)
    return DecisionSnapshot(
        content_id("DEC", payload),
        run_id,
        predicted.prediction_id,
        predicted.market_state_id,
        decision_time,
        decision_time,
        action.final_decision,
        None if playbook is None else playbook.value,
        predicted.conviction,
        action,
        action.blockers,
        plan_id_for,
    )


def realize(
    predicted: PredictionSnapshot, terminal: Decimal | None, resolution: datetime
) -> PredictionRealization:
    """A separate, later record; the issued PredictionSnapshot is never modified."""
    validity = "VALID"
    if predicted.predicted_direction is Direction.UNAVAILABLE or predicted.reference_price is None:
        validity = "UNSCORABLE_PREDICTION_UNAVAILABLE"
    elif terminal is None:
        validity = "UNSCORABLE_MISSING_TERMINAL_MINUTE"
    realized = direction = correct = error = covered = None
    baselines: tuple[tuple[str, float | str | None], ...] = ()
    if validity == "VALID":
        assert predicted.reference_price is not None and terminal is not None
        realized = float(terminal / predicted.reference_price - 1)
        direction = "UP" if realized > 0 else "DOWN" if realized < 0 else "FLAT"
        if predicted.predicted_direction in (Direction.UP, Direction.DOWN):
            correct = predicted.predicted_direction.value == direction
        if predicted.mean_terminal_return is not None:
            error = abs(predicted.mean_terminal_return - realized)
        if (
            predicted.lower_quantile_return is not None
            and predicted.upper_quantile_return is not None
        ):
            covered = predicted.lower_quantile_return <= realized <= predicted.upper_quantile_return
        baselines = (("zero_return_absolute_error", abs(realized)),)
    payload = (predicted.prediction_id, resolution, validity, terminal)
    return PredictionRealization(
        content_id("RLZ", payload),
        predicted.prediction_id,
        resolution,
        resolution,
        validity,
        realized,
        direction,
        correct,
        error,
        covered,
        "NOT_SCORED_UNCALIBRATED_SYNTHETIC_PROBABILITY",
        baselines,
    )
