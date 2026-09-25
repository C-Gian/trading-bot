"""System G1 Development V1 causal engine (protocol sections 3-13).

One virtual clock drives, per completed 1m boundary: completed-bar aggregation, the frozen shared
indicators, the six-scale cycle family, the session VWAP, every book's ledger (fills, exits,
funding), 4h forecast realizations and — at every completed 15m candle — recognition (P1 state
machine, P2 detector), S-full conviction, the continuous forecast, and each book's configuration
decision. Recognition, conviction and the forecast are computed once and shared by every book, so
the seven configurations (and the cost/delay stress views) see identical inputs and differ only in
their declared component/playbook or execution assumption.

The engine is data-agnostic: it only consumes `Bar` objects and funding rates handed to it. Real
historical sources are reachable exclusively through `app.g1.batch` behind the execution guard.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from app.backtest.models import CostModel

from . import ALGORITHM_VERSION, FORECAST_HORIZON_MINUTES
from .bars import MINUTE, Aggregator, Bar, CausalView, FutureObservationError
from .canonical import content_id, digest
from .cycle import METHOD_VERSION, CycleEngine, timing_qualifier
from .forecaster import (
    ESTIMATOR_VERSION,
    PROBABILITY_STATUS,
    QUANTILES,
    EmpiricalShrunkForecaster,
    Forecast,
    TrainingRow,
    prior_risk_scale,
    unavailable,
)
from .indicators import (
    UNAVAILABLE,
    DailyContext,
    HourStructure,
    Participation,
    SessionVwap,
    WilderAdx,
    WilderAtr,
)
from .ledger import COST_CONTRACT_VERSION, ReferenceLedger, RiskPolicy, is_funding_time
from .playbooks import (
    CONFIGS,
    PLAYBOOK_VERSION,
    DecisionContext,
    P1Machine,
    Setup,
    conviction,
    decide,
    directional_bias,
    p2_setups,
)
from .records import (
    Action,
    Actionability,
    Bias,
    ClosedTrade,
    Conviction,
    CycleState,
    DecisionSnapshot,
    Direction,
    MarketState,
    ModelArtifact,
    OrderFillEvent,
    PredictionRealization,
    PredictionSnapshot,
    ResearchExposureRecord,
    RunManifest,
    Side,
    SignalRole,
    SignalSnapshot,
    StructuralMode,
    TradePlan,
)
from .store import EventStore

ENGINE_VERSION = "SYSTEM-G1-DEVELOPMENT-ENGINE-V1"
PROTOCOL_PATH = "research/protocols/SYSTEM-G1-DEVELOPMENT-V1.md"
DECISION_MINUTES = 15
HORIZON = timedelta(minutes=FORECAST_HORIZON_MINUTES)
COST_STRESS = CostModel(
    profile="G1_COST_STRESS_48BP_ROUND_TRIP_PLUS_FUNDING",
    entry_fee_bps=Decimal(20),
    exit_fee_bps=Decimal(20),
    entry_friction_bps=Decimal(4),
    exit_friction_bps=Decimal(4),
)
DELAY_STRESS_ADDITIONAL_MINUTES = 5
CENT = Decimal("0.01")


@dataclass(frozen=True)
class BookSpec:
    """One configuration under one execution assumption, trading only inside its window."""

    book_id: str
    config_id: str
    window_start: datetime
    window_end: datetime
    costs: CostModel = field(default_factory=CostModel)
    policy: RiskPolicy = field(default_factory=RiskPolicy)

    def __post_init__(self) -> None:
        if self.config_id not in CONFIGS:
            raise ValueError(f"unknown configuration {self.config_id}")


def primary_book(config_id: str, start: datetime, end: datetime) -> BookSpec:
    return BookSpec(f"{config_id}:PRIMARY", config_id, start, end)


def stress_books(config_id: str, start: datetime, end: datetime) -> tuple[BookSpec, ...]:
    """The two frozen robustness views; never combined."""
    delayed = RiskPolicy(
        operational_delay_minutes=RiskPolicy().operational_delay_minutes
        + DELAY_STRESS_ADDITIONAL_MINUTES
    )
    return (
        BookSpec(f"{config_id}:COST_48BP", config_id, start, end, costs=COST_STRESS),
        BookSpec(f"{config_id}:DELAY_PLUS_5M", config_id, start, end, policy=delayed),
    )


@dataclass(frozen=True)
class ForecastRow:
    """Compact per-issue scoring row (evaluation uses these, not the UI records)."""

    issue_time: datetime
    conviction: str
    available: bool
    probability_up: float | None
    mean_return: float | None
    training_up_rate: float | None
    realized_return: float | None = None
    valid: bool = False


@dataclass
class Book:
    spec: BookSpec
    ledger: ReferenceLedger
    decisions: int = 0
    entries_blocked: int = 0
    run_stop_triggered: bool = False
    equity_path: list[tuple[datetime, Decimal]] = field(default_factory=list)
    recorded_events: int = 0
    recorded_trades: int = 0


def development_manifest(
    sources: tuple[tuple[str, str], ...],
    start: datetime,
    end: datetime,
    books: tuple[BookSpec, ...],
    provenance: str,
    protocol_sha256: str,
) -> RunManifest:
    configuration = (
        ENGINE_VERSION,
        protocol_sha256,
        METHOD_VERSION,
        ESTIMATOR_VERSION,
        PLAYBOOK_VERSION,
        [(b.book_id, b.config_id, b.costs, b.policy, b.window_start, b.window_end) for b in books],
    )
    configuration_id = content_id("CFG", configuration)
    return RunManifest(
        content_id("RUN", (configuration_id, sources, start, end, provenance)),
        configuration_id,
        "SYSTEM-G1-DEVELOPMENT-V1",
        sources,
        start,
        end,
        COST_CONTRACT_VERSION,
        RiskPolicy().version,
        METHOD_VERSION,
        provenance,
        evidence_class=provenance,
    )


class DevelopmentEngine:
    def __init__(
        self,
        manifest: RunManifest,
        books: Iterable[BookSpec],
        funding_rates: dict[datetime, Decimal],
        display_book: str | None = None,
        retain_records: bool = True,
    ) -> None:
        self.manifest = manifest
        self.run_id = manifest.run_id
        self.books = {
            spec.book_id: Book(spec, ReferenceLedger(spec.policy, spec.costs)) for spec in books
        }
        if not self.books:
            raise ValueError("at least one book is required")
        self.display = display_book or next(iter(self.books))
        self.funding_rates = funding_rates
        self.retain = retain_records
        self.store = EventStore()
        self.view = CausalView()
        self.aggregator = Aggregator()
        self.cycles = CycleEngine()
        self.adx, self.structure, self.atr = WilderAdx(), HourStructure(), WilderAtr()
        self.vwap, self.daily, self.flow = SessionVwap(), DailyContext(), Participation()
        self.p1 = P1Machine()
        self.closes_15m: deque[Bar] = deque(maxlen=97)
        self.cursor = manifest.dataset_start
        self._inbox: deque[Bar] = deque()
        self._last_ingested: datetime | None = None
        self._pending: dict[
            datetime, list[tuple[PredictionSnapshot | None, int, float | None, str, str, Decimal]]
        ] = {}
        self.training: list[TrainingRow] = []
        self.model: EmpiricalShrunkForecaster | None = None
        self.model_artifact: ModelArtifact | None = None
        self.forecasts: list[ForecastRow] = []
        self.latest: dict[str, Any] = {}
        self.issues = 0
        self.store.append(manifest)

    # ---------------------------------------------------------------- core protocol
    @property
    def complete(self) -> bool:
        return self.cursor >= self.manifest.dataset_end

    @property
    def ledger(self) -> ReferenceLedger:
        return self.books[self.display].ledger

    def ingest(self, bar: Bar) -> None:
        if bar.timeframe != "1m":
            raise ValueError("the engine consumes 1m source events only")
        if self._last_ingested is not None and bar.open_time <= self._last_ingested:
            raise ValueError("source minutes must be ingested in order")
        if bar.available_at <= self.cursor:
            raise FutureObservationError("late source minute rejected: cursor already passed it")
        self._last_ingested = bar.open_time
        self._inbox.append(bar)

    def advance_to(self, cursor: datetime) -> None:
        cursor = min(cursor, self.manifest.dataset_end)
        while self.cursor + MINUTE <= cursor:
            self._boundary(self.cursor + MINUTE)

    def finish(self) -> None:
        """Resolve every book's unresolved end state once the engine reached its dataset end."""
        if not self.complete:
            raise RuntimeError("the engine has not reached its dataset end")
        for book in self.books.values():
            book.ledger.finalize(self.cursor)
            self._record_book(book, self.cursor, True)

    def latest_cycle(self) -> CycleState | None:
        cycle = self.latest.get("cycle")
        return cycle if isinstance(cycle, CycleState) else None

    def fingerprint(self) -> str:
        trades = {b: list(book.ledger.trades) for b, book in self.books.items()}
        return digest((self.store.fingerprint(), self.cursor, trades, self.forecasts))

    def exposure_record(self) -> ResearchExposureRecord:
        return ResearchExposureRecord(
            content_id("EXP", (self.run_id, self.manifest.evidence_class)),
            self.run_id,
            self.manifest.evidence_class,
            False,
            False,
            0,
            len({b.spec.config_id for b in self.books.values()}),
            ("SYNTHETIC_FIXTURE_ONLY",) if "SYNTHETIC" in self.manifest.evidence_class else (),
        )

    # ---------------------------------------------------------------- per-minute processing
    def _boundary(self, moment: datetime) -> None:
        arrived = []
        while self._inbox and self._inbox[0].available_at <= moment:
            arrived.append(self._inbox.popleft())
        emitted = self.aggregator.advance(moment, tuple(arrived))
        self.view.move_to(moment, emitted)
        self.cursor = moment
        minute = self.view.minute_at(moment - MINUTE)
        self.vwap.on_minute_boundary(moment - MINUTE, minute)
        for bar in emitted:
            self._route(bar)
        for book in self.books.values():
            events = book.ledger.on_minute(moment - MINUTE, minute)
            rate = self.funding_rates.get(moment)
            if rate is not None and is_funding_time(moment) and minute is not None:
                book.ledger.settle_funding(moment, rate, minute.close)
            self._record_book(book, moment, bool(events))
        for issued, index, sigma, bias, conv, reference in self._pending.pop(moment, []):
            self._realize(issued, index, sigma, bias, conv, reference, minute, moment)
        if moment.minute % DECISION_MINUTES == 0:
            self._decide(moment)

    def _route(self, bar: Bar) -> None:
        if bar.timeframe != "1m":
            self.cycles.on_bar(bar)
        if bar.timeframe == "4h":
            self.adx.update(bar)
        elif bar.timeframe == "1h":
            self.structure.update(bar)
        elif bar.timeframe == "15m":
            self.atr.update(bar)
            self.flow.update(bar)
            self.closes_15m.append(bar)
        elif bar.timeframe == "1d":
            self.daily.update(bar)

    def _record_book(self, book: Book, moment: datetime, changed: bool) -> None:
        ledger = book.ledger
        if ledger.run_entry_stop:
            book.run_stop_triggered = True
        new_events = ledger.events[book.recorded_events :]
        new_trades = ledger.trades[book.recorded_trades :]
        book.recorded_events, book.recorded_trades = len(ledger.events), len(ledger.trades)
        if new_events or new_trades:
            book.equity_path.append((moment, ledger.equity))
        if self.retain and book.spec.book_id == self.display:
            for record in (*new_events, *new_trades):
                self.store.append(record)

    # ---------------------------------------------------------------- forecasting
    def _sigma(self, moment: datetime) -> float | None:
        bars = list(self.closes_15m)
        if len(bars) < 97 or bars[-1].close_time != moment:
            return None
        for earlier, later in zip(bars, bars[1:], strict=False):
            if later.open_time != earlier.close_time or not later.complete or not earlier.complete:
                return None
        returns = [
            math.log(float(b.close) / float(a.close)) for a, b in zip(bars, bars[1:], strict=False)
        ]
        return prior_risk_scale(returns)

    def _model_for(self, moment: datetime) -> EmpiricalShrunkForecaster:
        year = moment.year
        if self.model is None or self.model.year != year:
            self.model = EmpiricalShrunkForecaster(year, self.training)
            start = min((r.issue_time for r in self.model.rows), default=None)
            self.model_artifact = ModelArtifact(
                content_id(
                    "MOD",
                    (
                        ESTIMATOR_VERSION,
                        year,
                        len(self.model.rows),
                        digest(
                            [(r.issue_time, r.bias, r.conviction, r.z) for r in self.model.rows]
                        ),
                    ),
                ),
                "EMPIRICAL_SHRUNK_CONDITIONAL_4H",
                ESTIMATOR_VERSION,
                bool(self.model.rows),
                None if start is None else (start.isoformat(), f"{year}-01-01T00:00:00+00:00"),
                PROBABILITY_STATUS,
                tuple(f"{b}x{c}" for b, c in self.model.cells),
                ("ANNUAL_EXPANDING_TRAINING_EXACT_4H_PURGE", "SHRINKAGE_W_N_OVER_N_PLUS_256"),
            )
            if self.retain:
                self.store.append(self.model_artifact)
        return self.model

    def _realize(
        self,
        issued: PredictionSnapshot | None,
        index: int,
        sigma: float | None,
        bias: str,
        conv: str,
        reference: Decimal,
        minute: Bar | None,
        moment: datetime,
    ) -> None:
        row = self.forecasts[index]
        realized = None
        if minute is not None and minute.close > 0 and reference > 0:
            realized = math.log(float(minute.close) / float(reference))
        if realized is not None and sigma is not None:
            self.training.append(TrainingRow(row.issue_time, bias, conv, realized / sigma))
        self.forecasts[index] = replace(
            row, realized_return=realized, valid=realized is not None and row.available
        )
        if issued is None or not self.retain:
            return
        validity = "VALID"
        if not row.available:
            validity = "UNSCORABLE_PREDICTION_UNAVAILABLE"
        elif realized is None:
            validity = "UNSCORABLE_MISSING_TERMINAL_MINUTE"
        direction = correct = error = covered = None
        baselines: tuple[tuple[str, float | str | None], ...] = ()
        if validity == "VALID" and realized is not None:
            direction = "UP" if realized > 0 else "DOWN" if realized < 0 else "FLAT"
            if issued.predicted_direction in (Direction.UP, Direction.DOWN):
                correct = issued.predicted_direction.value == direction
            if issued.mean_terminal_return is not None:
                error = abs(issued.mean_terminal_return - realized)
            if (
                issued.lower_quantile_return is not None
                and issued.upper_quantile_return is not None
            ):
                covered = issued.lower_quantile_return <= realized <= issued.upper_quantile_return
            up = 1.0 if realized > 0 else 0.0
            brier = None if row.probability_up is None else (row.probability_up - up) ** 2
            base = None if row.training_up_rate is None else (row.training_up_rate - up) ** 2
            baselines = (
                ("zero_return_absolute_error", abs(realized)),
                ("brier", brier),
                ("training_up_rate_brier", base),
            )
        self.store.append(
            PredictionRealization(
                content_id("RLZ", (issued.prediction_id, moment, validity, realized)),
                issued.prediction_id,
                moment,
                moment,
                validity,
                realized,
                direction,
                correct,
                error,
                covered,
                "BRIER_VS_TRAINING_UP_RATE_REPORTED_PROBABILITY_NOT_CALIBRATED",
                baselines,
            )
        )

    # ---------------------------------------------------------------- decisions
    def _context(self, moment: datetime) -> DecisionContext:
        candle = self.view.bar_closing_at("15m", moment)
        previous = self.view.bar_closing_at("15m", moment - timedelta(minutes=15))
        boundary = self.daily.boundary_for(moment)
        atr = self.atr.reading.value("atr") if self.atr.reading.available_at == moment else None
        flow = self.flow.reading if self.flow.reading.available_at == moment else None
        long_flow = flow is not None and self.flow.supports(1)
        short_flow = flow is not None and self.flow.supports(-1)
        scales = tuple(t.state() for t in self.cycles.trackers)
        return DecisionContext(
            moment,
            candle,
            previous,
            self.adx.reading.state,
            self.structure.reading.state,
            self.structure.ema20 if self.structure.reading.state != UNAVAILABLE else None,
            atr,
            boundary.value("high"),
            boundary.value("low"),
            self.vwap.reading().value("vwap"),
            self.daily.direction.state,
            long_flow,
            short_flow,
            timing_qualifier(scales),
        )

    def _decide(self, moment: datetime) -> None:
        ctx = self._context(moment)
        p1, p1_events = self.p1.step(ctx)
        p2, p2_events = p2_setups(ctx)
        setups: list[Setup] = [*p1, *p2]
        conv = conviction(setups, ctx)
        bias = directional_bias(ctx)
        sigma = self._sigma(moment)
        candle = ctx.candle
        reference = None if candle is None or not candle.complete else candle.close
        model = self._model_for(moment)
        forecast: Forecast
        if reference is None:
            forecast = unavailable("DECISION_CANDLE_INCOMPLETE_OR_MISSING", model.year)
        else:
            forecast = model.predict(bias, conv.value, sigma)
        self.issues += 1
        row = ForecastRow(
            moment,
            conv.value,
            forecast.available,
            forecast.probability_up,
            forecast.mean_return,
            model.up_rate,
        )
        index = len(self.forecasts)
        self.forecasts.append(row)
        records = (
            self._records(moment, ctx, setups, p1_events + p2_events, conv, bias, forecast, sigma)
            if self.retain
            else None
        )
        issued = records["prediction"] if records else None
        if reference is not None:
            self._pending.setdefault(moment + HORIZON, []).append(
                (issued, index, sigma, bias, conv.value, reference)
            )
        elif issued is not None:
            self._pending.setdefault(moment + HORIZON, []).append(
                (issued, index, None, bias, conv.value, Decimal(0))
            )
        for book in self.books.values():
            self._book_decision(book, moment, ctx, setups, conv, issued, records)

    def _book_decision(
        self,
        book: Book,
        moment: datetime,
        ctx: DecisionContext,
        setups: list[Setup],
        conv: Conviction,
        issued: PredictionSnapshot | None,
        records: dict[str, Any] | None,
    ) -> None:
        spec = book.spec
        decided = decide(setups, ctx, CONFIGS[spec.config_id])
        in_window = spec.window_start <= moment < spec.window_end
        blockers = list(decided.blockers)
        if decided.chosen is not None and not in_window:
            blockers.append("OUTSIDE_BOOK_TRADING_WINDOW")
        risk = book.ledger.entry_blockers()
        if decided.chosen is not None:
            blockers.extend(risk)
        action = Action.NO_TRADE
        plan: TradePlan | None = None
        if decided.chosen is not None and not blockers:
            action = Action(decided.chosen.side.value)
        if in_window:
            book.decisions += 1
            if decided.chosen is not None and risk:
                book.entries_blocked += 1
        if not (self.retain and spec.book_id == self.display) and action is Action.NO_TRADE:
            return
        actionability = Actionability(
            decided.chosen is not None,
            ctx.market_state_available,
            ctx.market_state_available,
            not any(b != "POSITION_OCCUPIED" for b in risk),
            "POSITION_OCCUPIED" not in risk,
            action,
            tuple(blockers),
        )
        prediction_id = "" if issued is None else issued.prediction_id
        market_state_id = "" if records is None else records["market_state"].market_state_id
        decision = DecisionSnapshot(
            content_id("DEC", (self.run_id, spec.book_id, moment, action, blockers, conv)),
            self.run_id,
            prediction_id,
            market_state_id,
            moment,
            moment,
            action,
            None if decided.chosen is None else decided.chosen.playbook.value,
            conv,
            actionability,
            tuple(blockers),
            None,
        )
        if action is not Action.NO_TRADE and decided.chosen is not None:
            plan = self._plan(book, decision, decided.chosen, conv, moment)
            decision = replace(decision, trade_plan_id=plan.trade_plan_id)
            book.ledger.submit(plan)
        if self.retain and spec.book_id == self.display:
            self.store.append(decision)
            if plan is not None:
                self.store.append(plan)
            self.latest["decision"] = decision
            self.latest["ledger"] = book.ledger.snapshot(moment)

    def _plan(
        self,
        book: Book,
        decision: DecisionSnapshot,
        setup: Setup,
        conv: Conviction,
        moment: datetime,
    ) -> TradePlan:
        assert (
            setup.stop is not None and setup.objective is not None and setup.reward_risk is not None
        )
        policy, ledger = book.spec.policy, book.ledger
        reference = Decimal(repr(setup.reference)).quantize(CENT)
        stop = Decimal(repr(setup.stop)).quantize(CENT)
        objective = Decimal(repr(setup.objective)).quantize(CENT)
        return TradePlan(
            content_id(
                "PLN", (self.run_id, book.spec.book_id, decision.decision_id, stop, objective)
            ),
            self.run_id,
            decision.decision_id,
            setup.side,
            setup.playbook.value,
            PLAYBOOK_VERSION,
            moment,
            moment,
            policy.operational_delay_minutes,
            "NEXT_ELIGIBLE_EXACT_1M_OPEN_AFTER_READINESS_PLUS_DELAY",
            moment + timedelta(minutes=policy.operational_delay_minutes) + timedelta(minutes=15),
            reference,
            stop,
            objective,
            policy.max_hold_minutes,
            Decimal(repr(setup.reward_risk)).quantize(Decimal("0.0001")),
            book.spec.costs.profile,
            "SIGNED_SETTLEMENT_FUNDING",
            ledger.equity,
            ledger.equity * policy.risk_fraction,
            ledger.equity * policy.max_gross_notional_multiple,
            "DETERMINED_AT_FILL_0.25PCT_EQUITY_RISK_CAPPED_1X_NOTIONAL",
            conv,
            setup.reasons,
            (),
            "REFERENCE_PAPER_USDM",
        )

    # ---------------------------------------------------------------- display records
    def _records(
        self,
        moment: datetime,
        ctx: DecisionContext,
        setups: list[Setup],
        events: list[str],
        conv: Conviction,
        bias: str,
        forecast: Forecast,
        sigma: float | None,
    ) -> dict[str, Any]:
        cycle = self.cycles.snapshot(self.run_id, moment)
        board = self._board(moment, ctx, sigma, cycle)
        mode = {
            "TREND_BULL": StructuralMode.TREND,
            "TREND_BEAR": StructuralMode.TREND,
            "RANGE": StructuralMode.RANGE,
            "TRANSITION": StructuralMode.TRANSITION,
        }.get(ctx.regime, StructuralMode.UNAVAILABLE)
        location = "UNAVAILABLE"
        if ctx.vwap is not None and ctx.candle is not None:
            location = (
                "ABOVE_SESSION_VWAP"
                if float(ctx.candle.close) > ctx.vwap
                else "AT_OR_BELOW_SESSION_VWAP"
            )
        participation = (
            "SUPPORTS_LONG"
            if ctx.participation_long
            else "SUPPORTS_SHORT"
            if ctx.participation_short
            else "NOT_SUPPORTING_OR_UNAVAILABLE"
        )
        supporting = tuple(e for e in events if e.endswith(("TRIGGERED", "REENTRY", "ARMED")))
        opposing = tuple(e for e in events if e not in supporting)
        state = MarketState(
            content_id(
                "MST",
                (self.run_id, moment, ctx.regime, ctx.structure, ctx.daily, ctx.cycle, events),
            ),
            self.run_id,
            moment,
            moment,
            Bias(bias),
            mode,
            ctx.structure,
            ctx.regime,
            ctx.daily,
            location,
            participation,
            ctx.cycle,
            ctx.market_state_available,
            supporting,
            opposing,
            tuple(s.signal_id for s in board),
            cycle.cycle_state_id,
            "SYSTEM_G1_DEVELOPMENT_V1_FROZEN_RULES",
        )
        assert self.model_artifact is not None
        available = forecast.available
        direction = Direction(forecast.direction)
        prediction = PredictionSnapshot(
            content_id("PRD", (self.run_id, moment, bias, conv, forecast, sigma)),
            self.run_id,
            moment,
            moment,
            moment,
            moment + HORIZON,
            None if ctx.candle is None or not ctx.candle.complete else ctx.candle.close,
            Bias(bias),
            direction,
            forecast.probability_up,
            None if forecast.probability_up is None else 1 - forecast.probability_up,
            PROBABILITY_STATUS if available else "UNAVAILABLE",
            forecast.mean_return,
            forecast.median_return,
            forecast.lower_return,
            forecast.upper_return,
            QUANTILES,
            forecast.mean_z,
            sigma,
            f"CELL_N={forecast.cell_n};SHRINKAGE_W={forecast.weight}"
            if available
            else "UNAVAILABLE",
            conv,
            Actionability(
                bool(setups),
                ctx.market_state_available,
                ctx.market_state_available,
                True,
                True,
                Action.NO_TRADE,
                (),
            ),
            tuple(
                f"{s.playbook.value}:{s.side.value}:{s.plan_veto or 'PLAN_VALID'}" for s in setups
            ),
            supporting,
            opposing,
            state.market_state_id,
            cycle.cycle_state_id,
            self.model_artifact.model_artifact_id,
            forecast.unavailable_reason,
            algorithm_version=ALGORITHM_VERSION,
        )
        for record in (*board, cycle, state, prediction):
            self.store.append(record)
        self.latest.update(
            {
                "signals": board,
                "cycle": cycle,
                "market_state": state,
                "prediction": prediction,
                "setups": setups,
            }
        )
        return {"prediction": prediction, "market_state": state}

    def _board(
        self, moment: datetime, ctx: DecisionContext, sigma: float | None, cycle: CycleState
    ) -> tuple[SignalSnapshot, ...]:
        rows: list[
            tuple[str, str, str, Any, tuple[tuple[str, float | str | None], ...], SignalRole]
        ] = [
            (
                "STRUCTURE_TREND",
                "adx_di_regime_4h",
                "4h",
                self.adx.reading,
                self.adx.reading.values,
                SignalRole.ACTIVE,
            ),
            (
                "STRUCTURE_TREND",
                "ema20_ema50_structure_1h",
                "1h",
                self.structure.reading,
                self.structure.reading.values,
                SignalRole.ACTIVE,
            ),
            (
                "STRUCTURE_TREND",
                "daily_ema20_corroboration",
                "1d",
                self.daily.direction,
                self.daily.direction.values,
                SignalRole.ACTIVE,
            ),
            (
                "PRICE_LOCATION_VALUE",
                "session_vwap",
                "1m",
                self.vwap.reading(),
                self.vwap.reading().values,
                SignalRole.ACTIVE,
            ),
            (
                "PRICE_LOCATION_VALUE",
                "previous_utc_day_range",
                "1d",
                self.daily.boundary_for(moment),
                self.daily.boundary_for(moment).values,
                SignalRole.ACTIVE,
            ),
            (
                "MOMENTUM_VOLATILITY",
                "wilder_atr14_15m",
                "15m",
                self.atr.reading,
                self.atr.reading.values,
                SignalRole.ACTIVE,
            ),
            (
                "PARTICIPATION_FLOW",
                "rvol_and_taker_imbalance_15m",
                "15m",
                self.flow.reading,
                self.flow.reading.values,
                SignalRole.ACTIVE,
            ),
        ]
        board = []
        for family, name, timeframe, reading, values, role in rows:
            available_at = reading.available_at or moment
            board.append(
                SignalSnapshot(
                    content_id("SIG", (self.run_id, name, moment, reading.state, values)),
                    self.run_id,
                    family,
                    name,
                    ENGINE_VERSION,
                    available_at,
                    available_at,
                    timeframe,
                    values,
                    reading.state,
                    "UNAVAILABLE" if reading.state == UNAVAILABLE else "READY",
                    role,
                    "FROZEN_SYSTEM_G1_DEVELOPMENT_V1_DEFINITION",
                    name,
                )
            )
        board.append(
            SignalSnapshot(
                content_id(
                    "SIG", (self.run_id, "cycle_timing_qualifier", moment, cycle.timing_qualifier)
                ),
                self.run_id,
                "CYCLICAL_STATE",
                "cycle_timing_qualifier",
                METHOD_VERSION,
                moment,
                moment,
                "multi",
                (("prior_risk_sigma4h", sigma),),
                cycle.timing_qualifier,
                "READY",
                SignalRole.ACTIVE,
                "ADR_0046_TIMING_QUALIFIER",
                "cycle corroboration role only",
            )
        )
        return tuple(board)


def trades_of(engine: DevelopmentEngine, book_id: str) -> list[ClosedTrade]:
    return list(engine.books[book_id].ledger.trades)


def fills_of(engine: DevelopmentEngine, book_id: str) -> list[OrderFillEvent]:
    return list(engine.books[book_id].ledger.events)


def drive(
    engine: DevelopmentEngine, bars: Iterable[Bar], step: timedelta = MINUTE
) -> DevelopmentEngine:
    pending = deque(bars)
    while not engine.complete:
        target = engine.cursor + step
        while pending and pending[0].available_at <= target:
            engine.ingest(pending.popleft())
        engine.advance_to(target)
    return engine


__all__ = ["BookSpec", "DevelopmentEngine", "Side"]
