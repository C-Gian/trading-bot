"""The single System G1 causal core shared by the replay and live-style adapters.

One virtual cursor drives aggregation, signals, cycles, state, forecasts, decisions, risk, fills
and score resolution. `ingest` only buffers source minutes; `advance_to(cursor)` processes every
minute boundary up to the cursor in event-time order, exposing at each boundary only observations
whose `available_at` is not after it. However the cursor jumps (replay speed, batching, live
heartbeats), the per-boundary processing — and therefore every issued record — is identical.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import Decimal

from . import pipeline, signals
from .bars import MINUTE, Aggregator, Bar, CausalView, FutureObservationError
from .canonical import content_id, digest
from .cycle import METHOD_VERSION, CycleEngine
from .fixtures import FIXTURE_ID, ScenarioStep, dataset_hash, scenario_digest
from .ledger import COST_CONTRACT_VERSION, ReferenceLedger, RiskPolicy, is_funding_time
from .records import (
    Action,
    CycleState,
    DecisionSnapshot,
    PredictionSnapshot,
    ResearchExposureRecord,
    RunManifest,
)
from .store import EventStore

DECISION_MINUTES = 15


def run_manifest(
    bars: tuple[Bar, ...], start: datetime, end: datetime, policy: RiskPolicy
) -> RunManifest:
    sources = (
        (FIXTURE_ID + ":1m-path", dataset_hash(bars)),
        (FIXTURE_ID + ":scenario", scenario_digest()),
    )
    configuration = ("G1-CP1-SYNTHETIC-CONFIGURATION", policy, METHOD_VERSION)
    configuration_id = content_id("CFG", configuration)
    payload = (configuration_id, sources, start, end)
    return RunManifest(
        content_id("RUN", payload),
        configuration_id,
        "G1-CP1-SYNTHETIC-CONFIGURATION-V1",
        sources,
        start,
        end,
        COST_CONTRACT_VERSION,
        policy.version,
        METHOD_VERSION,
        "SYSTEM_G1_CHECKPOINT_1_SYNTHETIC_FIXTURE_REGISTRATION",
    )


class G1Core:
    def __init__(
        self,
        manifest: RunManifest,
        scenario: Callable[[datetime], ScenarioStep],
        funding_rates: dict[datetime, Decimal],
        policy: RiskPolicy | None = None,
    ) -> None:
        self.manifest = manifest
        self.run_id = manifest.run_id
        self.scenario = scenario
        self.funding_rates = funding_rates
        self.store = EventStore()
        self.view = CausalView()
        self.aggregator = Aggregator()
        self.cycles = CycleEngine()
        self.ledger = ReferenceLedger(policy)
        self.model = pipeline.synthetic_model_artifact()
        self.cursor = manifest.dataset_start
        self._inbox: deque[Bar] = deque()
        self._last_ingested: datetime | None = None
        self._pending_predictions: dict[datetime, list[PredictionSnapshot]] = {}
        self.latest: dict[str, object] = {}
        self._trades_recorded = 0
        for record in (manifest, self.model):
            self.store.append(record)

    @property
    def complete(self) -> bool:
        return self.cursor >= self.manifest.dataset_end

    def ingest(self, bar: Bar) -> None:
        if bar.timeframe != "1m":
            raise ValueError("the core consumes 1m source events only")
        if self._last_ingested is not None and bar.open_time <= self._last_ingested:
            raise ValueError("source minutes must be ingested in order")
        if bar.available_at <= self.cursor:
            # A minute that arrives after the cursor passed its availability cannot rewrite
            # history; it is treated as missing.
            raise FutureObservationError("late source minute rejected: cursor already passed it")
        self._last_ingested = bar.open_time
        self._inbox.append(bar)

    def advance_to(self, cursor: datetime) -> None:
        cursor = min(cursor, self.manifest.dataset_end)
        # Only whole minute boundaries are processed; a sub-minute target never overshoots.
        while self.cursor + MINUTE <= cursor:
            self._boundary(self.cursor + MINUTE)

    def _boundary(self, moment: datetime) -> None:
        arrived = []
        while self._inbox and self._inbox[0].available_at <= moment:
            arrived.append(self._inbox.popleft())
        emitted = self.aggregator.advance(moment, tuple(arrived))
        self.view.move_to(moment, emitted)
        self.cursor = moment
        for bar in emitted:
            if bar.timeframe != "1m":
                self.cycles.on_bar(bar)
        minute = self.view.minute_at(moment - MINUTE)
        for event in self.ledger.on_minute(moment - MINUTE, minute):
            self.store.append(event)
        self._record_new_trades()
        rate = self.funding_rates.get(moment)
        if rate is not None and is_funding_time(moment) and minute is not None:
            before = len(self.ledger.events)
            self.ledger.settle_funding(moment, rate, minute.close)
            for event in self.ledger.events[before:]:
                self.store.append(event)
        for predicted in self._pending_predictions.pop(moment, []):
            terminal = None if minute is None else minute.close
            self.store.append(pipeline.realize(predicted, terminal, moment))
        if moment.minute % DECISION_MINUTES == 0:
            self._decide(moment)

    def _record_new_trades(self) -> None:
        for trade in self.ledger.trades[self._trades_recorded :]:
            self.store.append(trade)
        self._trades_recorded = len(self.ledger.trades)

    def _decide(self, moment: datetime) -> None:
        step = self.scenario(moment)
        board = signals.board(self.run_id, self.view, moment)
        ready, unavailable = signals.data_ready(self.view, moment)
        cycle = self.cycles.snapshot(self.run_id, moment)
        state = pipeline.market_state(self.run_id, moment, step, board, cycle, ready)
        decision_bar = self.view.bar_closing_at("15m", moment)
        reference = (
            None if decision_bar is None or not decision_bar.complete else decision_bar.close
        )
        action, playbook = pipeline.actionability(step, ready, unavailable, self.ledger, cycle)
        predicted = pipeline.prediction(
            self.run_id, moment, step, reference, state, cycle, self.model, action, unavailable
        )
        decided: DecisionSnapshot = pipeline.decision(
            self.run_id, moment, predicted, action, playbook, None
        )
        plan = None
        if action.final_decision is not Action.NO_TRADE:
            assert playbook is not None and reference is not None
            plan = pipeline.trade_plan(
                self.run_id,
                decided.decision_id,
                moment,
                step,
                playbook,
                action.final_decision,
                reference,
                self.ledger,
            )
            # The decision identity excludes the plan link, so linking keeps the same identity.
            decided = replace(decided, trade_plan_id=plan.trade_plan_id)
        for record in (*board, cycle, state, predicted, decided):
            self.store.append(record)
        if plan is not None:
            self.store.append(plan)
            self.ledger.submit(plan)
        self._pending_predictions.setdefault(predicted.target_end, []).append(predicted)
        snapshot = self.ledger.snapshot(moment)
        self.latest = {
            "signals": board,
            "cycle": cycle,
            "market_state": state,
            "prediction": predicted,
            "decision": decided,
            "ledger": snapshot,
        }

    def latest_cycle(self) -> CycleState | None:
        cycle = self.latest.get("cycle")
        return cycle if isinstance(cycle, CycleState) else None

    def exposure_record(self) -> ResearchExposureRecord:
        payload = (self.run_id, "SYNTHETIC")
        return ResearchExposureRecord(
            content_id("EXP", payload),
            self.run_id,
            self.manifest.evidence_class,
            False,
            False,
            0,
            0,
            ("SYNTHETIC_FIXTURE_ONLY", "NO_G1_HISTORICAL_CONFIGURATION_INSPECTED"),
        )

    def fingerprint(self) -> str:
        return digest((self.store.fingerprint(), self.cursor))


def run_to_end(core: G1Core, bars: tuple[Bar, ...], step: timedelta = MINUTE) -> G1Core:
    """Historical-style drive helper: ingest everything available and advance by `step`."""
    pending = deque(bars)
    while not core.complete:
        target = core.cursor + step
        while pending and pending[0].available_at <= target:
            core.ingest(pending.popleft())
        core.advance_to(target)
    return core
