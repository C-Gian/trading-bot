"""G2-V0 authoritative scientific state machine.

`market facts -> G2 state -> continuous 4h forecast -> LONG/SHORT utility -> LONG/SHORT/NO_TRADE
-> risk/execution simulation -> immutable records`.

The core advances one minute boundary at a time. At boundary t it may only use 1m klines whose
close is at or before t. Per boundary, in this fixed order:

1. ingest the minute ending at t (if it exists) and close every completed higher-timeframe bar;
2. execution on that minute: pending entry fill/rejection, stop/expiry exit, mark-to-market;
3. settled funding at t for an open position;
4. forecast targets maturing at t (outcomes append; the prediction is never rewritten);
5. shadow labels / utility residuals maturing at t;
6. the scheduled monthly refit at 00:00 UTC on the first day of a month (boundary t);
7. on a completed 15m boundary: state, cycle shadow state, prediction, decision, order intent.

Replay speed, adapters and wall time never enter this module.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from .bars import Aggregator, Minute, MinuteTape, valid_minute
from .contract import (
    BASE_LATENCY,
    COLUMNS,
    DECISION_MINUTES,
    HORIZON,
    LABEL_HORIZON,
    MARGIN_TIE,
    MINUTE,
    PENALTIES,
    STOP_ATR_MULTIPLE,
    SYSTEM_VERSION,
)
from .cycle import CycleShadow
from .distribution import (
    FALLBACK,
    PREQUENTIAL,
    ResidualArchive,
    calibration_reason,
    direction,
    distribution,
    strength_label,
)
from .execution import FundingBook, OpenTrade, accounting_price, shadow_label
from .features import FeatureEngine, StateSnapshot
from .models import (
    Readout,
    Scaler,
    SupportError,
    atoms_sha256,
    first_of_month,
    fit_readout,
    fit_scaler,
    select_training,
)
from .records import (
    Action,
    ClosedTrade,
    Decision,
    FitManifest,
    FundingEvent,
    MarketState,
    OrderIntent,
    Prediction,
    PredictionOutcome,
    Reason,
    RiskSnapshot,
    RiskStateEvent,
    RunManifest,
    ShadowLabel,
    SimulatedFill,
    SourceAuditEvent,
    StopExpiryEvent,
    UtilityView,
    record_key,
)
from .risk import ExchangeFilters, Governor, filtered_quantity, round_stop
from .store import G2Store

HEADS = ("FORECAST", "LONG_UTILITY", "SHORT_UTILITY")
SIDES = ("LONG", "SHORT")


def _dt64(moment: datetime) -> np.datetime64:
    return np.datetime64(moment.replace(tzinfo=None), "m")


@dataclass
class _Fit:
    manifest: FitManifest
    readout: Readout | None
    atoms: np.ndarray | None = None


@dataclass
class _PendingForecast:
    decision_time: datetime
    prediction_id: str
    row: int | None
    price: float | None
    sigma: float | None
    mu_z: float | None


@dataclass
class _PendingLabel:
    decision_time: datetime
    row: int | None
    stop_distance: float | None
    predicted: dict[str, float | None]
    fit_ids: dict[str, str | None]


class _Rows:
    """Growable training buffers: one row per decision with an available state."""

    def __init__(self) -> None:
        self.n = 0
        cap = 4096
        self.times = np.empty(cap, dtype="datetime64[m]")
        self.x = np.empty((cap, len(COLUMNS)))
        self.z = np.full(cap, np.nan)
        self.z_at = np.empty(cap, dtype="datetime64[m]")
        self.net = {side: np.full(cap, np.nan) for side in SIDES}
        self.net_at = np.empty(cap, dtype="datetime64[m]")

    def add(self, moment: datetime, raw: tuple[float | None, ...]) -> int:
        if self.n == len(self.z):
            grow = len(self.z)
            self.times = np.concatenate([self.times, np.empty(grow, dtype="datetime64[m]")])
            self.x = np.concatenate([self.x, np.empty((grow, len(COLUMNS)))])
            self.z = np.concatenate([self.z, np.full(grow, np.nan)])
            self.z_at = np.concatenate([self.z_at, np.empty(grow, dtype="datetime64[m]")])
            for side in SIDES:
                self.net[side] = np.concatenate([self.net[side], np.full(grow, np.nan)])
            self.net_at = np.concatenate([self.net_at, np.empty(grow, dtype="datetime64[m]")])
        i = self.n
        self.times[i] = _dt64(moment)
        self.x[i] = [float(v) for v in raw]  # type: ignore[arg-type]
        self.z_at[i] = _dt64(moment + HORIZON)
        self.net_at[i] = _dt64(moment + LABEL_HORIZON)
        self.n += 1
        return i


class G2Core:
    def __init__(
        self,
        manifest: RunManifest,
        funding: FundingBook,
        filters: ExchangeFilters,
        friction: float,
        audit: tuple[SourceAuditEvent, ...] = (),
    ) -> None:
        self.manifest = manifest
        self.run_id = manifest.run_id
        self.funding = funding
        self.filters = filters
        self.friction = friction
        self.start = manifest.dataset_start
        self.end = manifest.dataset_end
        self.cursor = self.start
        self.tape = MinuteTape(self.start, int((self.end - self.start) // MINUTE))
        self.aggregator = Aggregator()
        self.features = FeatureEngine()
        self.cycle = CycleShadow()
        self.store = G2Store()
        self.governor = Governor()
        self.rows = _Rows()
        self.fits: dict[str, _Fit | None] = dict.fromkeys(HEADS)
        self.archives = {head: ResidualArchive(SYSTEM_VERSION) for head in HEADS}
        self.pending_forecasts: deque[_PendingForecast] = deque()
        self.pending_labels: deque[_PendingLabel] = deque()
        self.closes15: dict[datetime, float] = {}
        self._inbox: dict[datetime, Minute] = {}
        self.intent: OrderIntent | None = None
        self.trade: OpenTrade | None = None
        self.last_close: float | None = None
        self.invalid_minutes = 0
        self.store.append(manifest)
        for event in audit:
            self.store.append(event)
        self._risk_event(self.start, "INITIAL", "INITIAL_EQUITY")

    # ------------------------------------------------------------------ driving
    @property
    def complete(self) -> bool:
        return self.cursor >= self.end

    def ingest(self, minute: Minute) -> None:
        if minute.available_at <= self.cursor:
            raise ValueError("a minute arrived after its availability instant was processed")
        if not self.start <= minute.open_time < self.end:
            raise ValueError("minute outside the registered run window")
        self._inbox[minute.available_at] = minute

    def advance_to(self, target: datetime) -> None:
        target = min(target, self.end)
        while self.cursor < target:
            self._step(self.cursor + MINUTE)

    # ------------------------------------------------------------------ one boundary
    def _step(self, t: datetime) -> None:
        self.cursor = t
        minute = self._inbox.pop(t, None)
        if minute is not None and not valid_minute(minute):
            self.invalid_minutes += 1
            minute = None
        closed = []
        if minute is not None:
            self.tape.put(minute)
            closed.extend(self.aggregator.add(minute))
        self.tape.advance(t)
        closed.extend(self.aggregator.close_until(t))
        for bar in closed:
            if bar.timeframe == "15m" and bar.complete:
                self.closes15[bar.close_time] = bar.close
            self.features.on_bar(bar)
            self.cycle.on_bar(bar)
        self._execute(t, minute)
        self._funding(t)
        self._mature_forecasts(t)
        self._mature_labels(t)
        if first_of_month(t):
            self._refit(t)
        if t.minute % DECISION_MINUTES == 0:
            self._decide(t)

    # ------------------------------------------------------------------ execution
    def _risk_event(self, t: datetime, kind: str, basis: str) -> None:
        g = self.governor
        self.store.append(
            RiskStateEvent(
                record_key("G2R", self.run_id, t, kind),
                self.run_id,
                t,
                t,
                kind,
                g.equity,
                g.mark,
                basis,
                g.peak,
                g.drawdown,
                g.locked,
                self.trade is not None,
            )
        )

    def _remark(self, t: datetime, price: float | None, basis: str) -> None:
        """Mark the account at `price` (flat: realized equity); a lock triggers at `t`."""
        trade = self.trade
        mark = (
            self.governor.equity
            if trade is None or price is None
            else trade.mark(self.governor.equity, price)
        )
        if self.governor.mark_to(mark):
            self._risk_event(t, "DRAWDOWN_STOP_TRIGGERED", basis)

    def _execute(self, t: datetime, minute: Minute | None) -> None:
        intent = self.intent
        if intent is not None and t >= intent.intended_entry_time + MINUTE:
            self.intent = None
            self.governor.pending_intent = None
            if minute is not None and minute.open_time == intent.intended_entry_time:
                self._fill_entry(t, intent, minute)
            else:
                self._reject(t, intent, Reason.EXECUTION_ENTRY_DATA_MISSING, None)
        trade = self.trade
        if trade is not None and minute is not None and minute.open_time >= trade.entry_time:
            bar = (minute.open, minute.high, minute.low, minute.close)
            verdict = trade.exit_check(minute.open_time, bar)
            if verdict is not None:
                self._close(t, trade, minute.open_time, *verdict)
        if minute is not None:
            self.last_close = minute.close
            self._remark(t, minute.close, "1M_CLOSE")

    def _reject(self, t: datetime, intent: OrderIntent, reason: Reason, raw: float | None) -> None:
        self.store.append(
            SimulatedFill(
                record_key("G2X", self.run_id, intent.intent_id, "ENTRY_REJECTED"),
                self.run_id,
                record_key("G2T", self.run_id, intent.intent_id),
                intent.intent_id,
                "ENTRY_REJECTED",
                intent.side,
                intent.intended_entry_time,
                t,
                raw,
                None,
                0.0,
                0.0,
                (str(reason),),
            )
        )

    def _fill_entry(self, t: datetime, intent: OrderIntent, minute: Minute) -> None:
        raw = minute.open
        quantity = filtered_quantity(self.governor.equity, intent.stop_distance, raw, self.filters)
        if quantity is None:
            self._reject(t, intent, Reason.CONTRACT_FILTER_NOT_MET, raw)
            return
        sign = 1 if intent.side == "LONG" else -1
        stop = round_stop(raw - sign * intent.stop_distance, intent.side, self.filters)
        trade_id = record_key("G2T", self.run_id, intent.intent_id)
        trade = OpenTrade(
            trade_id,
            intent.intent_id,
            intent.decision_id,
            intent.side,
            intent.reference_price,
            intent.intended_entry_time,
            intent.intended_expiry_time,
            minute.open_time,
            raw,
            accounting_price(raw, intent.side, True, self.friction),
            stop,
            abs(raw - stop),
            quantity,
            self.friction,
        )
        self.governor.equity -= trade.entry_cost
        self.governor.open_trade = trade_id
        self.trade = trade
        # The causal mark at the fill instant is the fill price: post-friction equity.
        self._remark(t, raw, "ENTRY_FILL_PRICE")
        self.store.append(
            SimulatedFill(
                record_key("G2X", self.run_id, intent.intent_id, "ENTRY"),
                self.run_id,
                trade_id,
                intent.intent_id,
                "ENTRY",
                intent.side,
                minute.open_time,
                t,
                raw,
                trade.accounting_entry,
                quantity,
                trade.entry_cost,
                (),
            )
        )
        self._risk_event(t, "ENTRY", "ENTRY_FILL_PRICE")

    def _close(
        self,
        t: datetime,
        trade: OpenTrade,
        exit_time: datetime,
        kind: str,
        raw_exit: float,
        trigger: float | None,
    ) -> None:
        reasons: tuple[str, ...] = ()
        if kind == "EXPIRY_LATE_EXIT_DATA_MISSING":
            reasons = (str(Reason.EXECUTION_EXIT_DATA_MISSING),)
            trade.violations.append(str(Reason.EXECUTION_EXIT_DATA_MISSING))
        self.store.append(
            StopExpiryEvent(
                record_key("G2E", self.run_id, trade.trade_id),
                self.run_id,
                trade.trade_id,
                kind,
                exit_time,
                t,
                trigger,
                raw_exit,
                reasons,
            )
        )
        accounting_exit = accounting_price(raw_exit, trade.side, False, self.friction)
        exit_cost = trade.quantity * raw_exit * self.friction
        gross = trade.sign * trade.quantity * (raw_exit - trade.raw_entry)
        self.store.append(
            SimulatedFill(
                record_key("G2X", self.run_id, trade.intent_id, "EXIT"),
                self.run_id,
                trade.trade_id,
                trade.intent_id,
                "EXIT",
                trade.side,
                exit_time,
                t,
                raw_exit,
                accounting_exit,
                trade.quantity,
                exit_cost,
                reasons,
            )
        )
        friction_cost = trade.entry_cost + exit_cost
        net = gross - friction_cost + trade.funding_pnl
        self.governor.equity += gross - exit_cost
        planned = trade.quantity * trade.stop_distance
        self.store.append(
            ClosedTrade(
                trade.trade_id,
                self.run_id,
                trade.decision_id,
                trade.intent_id,
                trade.side,
                t,
                trade.intended_entry_time,
                trade.entry_time,
                trade.raw_entry,
                trade.accounting_entry,
                trade.stop_price,
                trade.stop_distance,
                trade.intended_expiry_time,
                exit_time,
                raw_exit,
                accounting_exit,
                kind,
                trade.quantity,
                planned,
                friction_cost,
                trade.funding_pnl,
                tuple(trade.funding_ids),
                gross,
                net,
                net / planned if planned > 0 else 0.0,
                trade.raw_entry - trade.decision_reference,
                tuple(trade.violations),
            )
        )
        self.trade = None
        self.governor.open_trade = None
        self._remark(t, None, "FLAT_AFTER_EXIT")
        self._risk_event(t, "EXIT", "FLAT_AFTER_EXIT")

    def _funding(self, t: datetime) -> None:
        trade = self.trade
        if trade is None or not t > trade.entry_time:
            return
        settlements = self.funding.settlements(t - MINUTE, t)
        for moment, rate in settlements:
            proxy_bar = self.tape.minute(moment - MINUTE)
            proxy = None if proxy_bar is None else proxy_bar[3]
            reasons: tuple[str, ...] = ()
            if rate is None:
                amount, status = 0.0, "FUNDING_DATA_INVALID"
                reasons = (str(Reason.FUNDING_DATA_INVALID),)
            elif proxy is None:
                # Conservative: the settlement is charged as an adverse cost at the last price.
                reference = self.last_close or trade.raw_entry
                amount, status = -abs(rate) * trade.quantity * reference, "FUNDING_DATA_INVALID"
                reasons = (str(Reason.FUNDING_DATA_INVALID),)
            else:
                amount = -trade.sign * rate * trade.quantity * proxy
                status = "SETTLED"
            if reasons:
                trade.violations.append(str(Reason.FUNDING_DATA_INVALID))
            funding_id = record_key("G2FU", self.run_id, trade.trade_id, moment)
            trade.funding_pnl += amount
            trade.funding_ids.append(funding_id)
            self.governor.equity += amount
            self.store.append(
                FundingEvent(
                    funding_id,
                    self.run_id,
                    trade.trade_id,
                    moment,
                    t,
                    rate,
                    proxy,
                    "USDM_1M_LAST_PRICE_CLOSE_PROXY_NOT_MARK",
                    trade.quantity,
                    amount,
                    status,
                    reasons,
                )
            )
            self._remark(t, proxy if proxy is not None else self.last_close, "FUNDING_PRICE_PROXY")
            self._risk_event(t, "FUNDING", "FUNDING_PRICE_PROXY")

    # ------------------------------------------------------------------ maturity
    def _mature_forecasts(self, t: datetime) -> None:
        while self.pending_forecasts and self.pending_forecasts[0].decision_time + HORIZON <= t:
            item = self.pending_forecasts.popleft()
            target_time = item.decision_time + HORIZON
            later = self.closes15.pop(target_time, None)
            realized = realized_z = residual = None
            status = "TARGET_UNAVAILABLE"
            if later is not None and item.price is not None:
                realized = math.log(later / item.price)
                status = "MATURED"
                if item.sigma is not None:
                    realized_z = realized / item.sigma
                    if item.row is not None:
                        self.rows.z[item.row] = realized_z
                    if item.mu_z is not None:
                        residual = realized_z - item.mu_z
                        self.archives["FORECAST"].append(
                            item.decision_time, t, residual, SYSTEM_VERSION
                        )
            self.store.append(
                PredictionOutcome(
                    record_key("G2O", self.run_id, item.decision_time),
                    item.prediction_id,
                    self.run_id,
                    item.decision_time,
                    target_time,
                    t,
                    status,
                    realized,
                    realized_z,
                    residual,
                    residual is not None,
                )
            )
        for stale in [m for m in self.closes15 if m < t - HORIZON]:
            del self.closes15[stale]

    def _mature_labels(self, t: datetime) -> None:
        while self.pending_labels and self.pending_labels[0].decision_time + LABEL_HORIZON <= t:
            item = self.pending_labels.popleft()
            for side in SIDES:
                outcome = shadow_label(
                    self.tape,
                    self.funding,
                    item.decision_time,
                    side,
                    item.stop_distance,
                    self.friction,
                )
                predicted = item.predicted[side]
                residual = None
                if outcome.net_r is not None:
                    if item.row is not None:
                        self.rows.net[side][item.row] = outcome.net_r
                    if predicted is not None:
                        residual = outcome.net_r - predicted
                        self.archives[f"{side}_UTILITY"].append(
                            item.decision_time, t, residual, SYSTEM_VERSION
                        )
                self.store.append(
                    ShadowLabel(
                        record_key("G2L", self.run_id, item.decision_time, side),
                        self.run_id,
                        item.decision_time,
                        side,
                        t,
                        outcome.status,
                        tuple(str(r) for r in outcome.reasons),
                        item.stop_distance,
                        outcome.raw_entry,
                        outcome.stop_price,
                        outcome.raw_exit,
                        outcome.exit_kind,
                        outcome.exit_time,
                        outcome.gross,
                        outcome.friction,
                        outcome.funding,
                        outcome.settlements,
                        outcome.net,
                        outcome.net_r,
                        predicted,
                        residual,
                        item.fit_ids[side],
                    )
                )

    # ------------------------------------------------------------------ fitting
    def _source_hashes(self) -> tuple[tuple[str, str], ...]:
        return self.manifest.source_hashes

    def _manifest(
        self,
        head: str,
        t: datetime,
        status: str,
        detail: str,
        training: object | None = None,
        readout: Readout | None = None,
        scaler: Scaler | None = None,
        atoms: np.ndarray | None = None,
    ) -> FitManifest:
        times = getattr(training, "times", None)
        label_times = getattr(training, "label_times", None)
        rows = 0 if times is None else len(times)

        def moment(value: np.datetime64) -> datetime:
            return value.astype("datetime64[m]").astype(datetime).replace(tzinfo=t.tzinfo)

        return FitManifest(
            record_key("G2F", self.run_id, head, t),
            self.run_id,
            SYSTEM_VERSION,
            head,
            t,
            t,
            status,
            detail,
            moment(times.min()) if rows and times is not None else None,
            moment(times.max()) if rows and times is not None else None,
            rows,
            moment(label_times.max()) if rows and label_times is not None else None,
            "Z4H = R4H / SIGMA_4H" if head == "FORECAST" else f"{head.split('_')[0]} NET_R",
            () if scaler is None else scaler.centers,
            () if scaler is None else scaler.scales,
            () if scaler is None else scaler.constant,
            None if readout is None else readout.intercept,
            () if readout is None else readout.coefficients,
            PENALTIES,
            0 if atoms is None else len(atoms),
            None if atoms is None else atoms_sha256(atoms),
            self._source_hashes(),
        )

    def _refit(self, t: datetime) -> None:
        rows = self.rows
        n = rows.n
        times, x = rows.times[:n], rows.x[:n]
        forecast_training = select_training(times, x, rows.z[:n], rows.z_at[:n], t)
        scaler: Scaler | None = None
        try:
            if len(forecast_training.y) == 0:
                raise SupportError("0 mature rows")
            scaler = fit_scaler(forecast_training.x)
            readout = fit_readout(forecast_training, scaler)
            atoms = forecast_training.y - forecast_training.y.mean()
            manifest = self._manifest(
                "FORECAST", t, "FITTED", "SUPPORT_MET", forecast_training, readout, scaler, atoms
            )
            self.fits["FORECAST"] = _Fit(manifest, readout, atoms)
        except SupportError as exc:
            scaler = None
            manifest = self._manifest(
                "FORECAST", t, "UNAVAILABLE_SUPPORT", str(exc), forecast_training
            )
            self.fits["FORECAST"] = None
        self.store.append(manifest)
        for side in SIDES:
            head = f"{side}_UTILITY"
            training = select_training(times, x, rows.net[side][:n], rows.net_at[:n], t)
            if scaler is None:
                manifest = self._manifest(
                    head, t, "UNAVAILABLE_SUPPORT", "NO_FORECAST_SCALER", training
                )
                self.fits[head] = None
            else:
                try:
                    if len(training.y) == 0:
                        raise SupportError("0 mature rows")
                    readout = fit_readout(training, scaler)
                    manifest = self._manifest(
                        head, t, "FITTED", "SUPPORT_MET", training, readout, scaler
                    )
                    self.fits[head] = _Fit(manifest, readout)
                except SupportError as exc:
                    manifest = self._manifest(head, t, "UNAVAILABLE_SUPPORT", str(exc), training)
                    self.fits[head] = None
            self.store.append(manifest)

    # ------------------------------------------------------------------ decision
    def _decide(self, t: datetime) -> None:
        snap = self.features.snapshot(t)
        state = self._state_record(t, snap)
        self.store.append(state)
        self.store.append(self.cycle.snapshot(self.run_id, t))
        prediction_id = record_key("G2P", self.run_id, t)
        decision_id = record_key("G2D", self.run_id, t)
        raw = np.array([np.nan if v is None else v for v in snap.raw], dtype=float)
        forecast_fit = self.fits["FORECAST"]
        row = self.rows.add(t, snap.raw) if snap.available else None

        # ---- forecast
        reasons: list[str] = []
        mu_z = None
        scaled: tuple[float | None, ...] = (None,) * len(COLUMNS)
        contributions: tuple[float | None, ...] = (None,) * len(COLUMNS)
        intercept = None
        dist = None
        residual_source, residual_count = "NONE", 0
        if not snap.available:
            assert snap.reason is not None
            reasons.append(str(snap.reason))
        elif forecast_fit is None or forecast_fit.readout is None:
            reasons.append(str(Reason.FORECAST_UNAVAILABLE_NO_MODEL))
        else:
            s, c, mu = forecast_fit.readout.terms(raw)
            mu_z = mu
            scaled = tuple(float(v) for v in s)
            contributions = tuple(float(v) for v in c)
            intercept = forecast_fit.readout.intercept
            ready, count, _ = self.archives["FORECAST"].status(t)
            if ready:
                residuals = self.archives["FORECAST"].window(t)[1]
                residual_source, residual_count = PREQUENTIAL, count
            else:
                assert forecast_fit.atoms is not None
                residuals = forecast_fit.atoms
                residual_source, residual_count = FALLBACK, len(residuals)
            assert snap.sigma_4h is not None
            dist = distribution(mu, snap.sigma_4h, residuals, residual_source)
            reasons.append(str(Reason.FORECAST_AVAILABLE))
            reasons.append(str(calibration_reason(residual_source)))
        forecast_manifest = None if forecast_fit is None else forecast_fit.manifest
        view = (
            None
            if dist is None or snap.sigma_4h is None
            else abs(dist.median_return) / snap.sigma_4h
        )
        forecast_direction = "UNAVAILABLE" if dist is None else direction(dist.median_return)
        prediction = Prediction(
            prediction_id,
            self.run_id,
            SYSTEM_VERSION,
            t,
            t,
            decision_id,
            state.state_id,
            None if forecast_manifest is None else forecast_manifest.fit_id,
            self._source_hashes(),
            snap.max_source_time,
            None if forecast_manifest is None else forecast_manifest.training_start,
            None if forecast_manifest is None else forecast_manifest.training_end,
            None if forecast_manifest is None else forecast_manifest.latest_label_time,
            t + HORIZON,
            snap.raw,
            scaled,
            contributions,
            intercept,
            mu_z,
            None if dist is None else dist.mean_return,
            None if dist is None else dist.median_return,
            None if dist is None else dist.q10,
            None if dist is None else dist.q50,
            None if dist is None else dist.q90,
            None if dist is None else dist.p_positive,
            snap.sigma_4h,
            "UNAVAILABLE" if dist is None else residual_source,
            residual_source,
            residual_count,
            view,
            None if view is None else strength_label(view),
            forecast_direction,
            (
                (
                    "model_support",
                    "NONE" if forecast_manifest is None else forecast_manifest.status,
                ),
                ("model_training_rows", 0 if forecast_manifest is None else forecast_manifest.rows),
                ("residual_source", residual_source),
                ("residual_count", residual_count),
                ("missingness", "NONE" if snap.available else str(snap.reason)),
                ("drift_diagnostics", "NOT_EVALUATED_IN_G2_01"),
                ("model_version", SYSTEM_VERSION),
            ),
            tuple(reasons),
            "PENDING",
        )
        self.store.append(prediction)
        self.pending_forecasts.append(
            _PendingForecast(t, prediction_id, row, snap.price, snap.sigma_4h, mu_z)
        )

        # ---- utility heads (issued whenever a model and state exist)
        stop_distance = (
            STOP_ATR_MULTIPLE * snap.atr14 if snap.atr14 is not None and snap.atr14 > 0 else None
        )
        utilities: dict[str, UtilityView] = {}
        predicted: dict[str, float | None] = {}
        fit_ids: dict[str, str | None] = {}
        for side in SIDES:
            head = f"{side}_UTILITY"
            fit = self.fits[head]
            fit_ids[side] = None if fit is None else fit.manifest.fit_id
            ready, count, span = self.archives[head].status(t)
            if not snap.available:
                utilities[side] = UtilityView(
                    side, fit_ids[side], None, None, count, span, "STATE_UNAVAILABLE", None
                )
                predicted[side] = None
                continue
            if fit is None or fit.readout is None:
                utilities[side] = UtilityView(side, None, None, None, count, span, "NO_MODEL", None)
                predicted[side] = None
                continue
            value = fit.readout.terms(raw)[2]
            predicted[side] = value
            if ready:
                q10 = float(np.quantile(self.archives[head].window(t)[1], 0.10, method="linear"))
                utilities[side] = UtilityView(
                    side, fit_ids[side], value, q10, count, span, "PREQUENTIAL_READY", value + q10
                )
            else:
                utilities[side] = UtilityView(
                    side, fit_ids[side], value, None, count, span, "INSUFFICIENT", None
                )
        self.pending_labels.append(_PendingLabel(t, row, stop_distance, predicted, fit_ids))

        # ---- policy (utility only; forecast direction never forces the action)
        long_view, short_view = utilities["LONG"], utilities["SHORT"]
        selection, policy_reasons = policy(
            snap.available, long_view, short_view, forecast_direction
        )

        # ---- risk / execution vetoes
        governor = self.governor
        position_state = (
            "OPEN"
            if self.trade is not None
            else "ENTRY_PENDING"
            if self.intent is not None
            else "FLAT"
        )
        risk_reasons: list[str] = []
        if governor.locked:
            risk_reasons.append(str(Reason.PATH_DRAWDOWN_STOP_ACTIVE))
        if position_state != "FLAT":
            risk_reasons.append(str(Reason.POSITION_ALREADY_OPEN))
        action = Action.NO_TRADE
        if selection in SIDES and not risk_reasons:
            if stop_distance is None or snap.price is None:
                risk_reasons.append(str(Reason.SOURCE_STALE_OR_INVALID))
            elif (
                filtered_quantity(governor.equity, stop_distance, snap.price, self.filters) is None
            ):
                risk_reasons.append(str(Reason.CONTRACT_FILTER_NOT_MET))
            else:
                action = Action(selection)
        all_reasons = tuple(
            reasons + policy_reasons + risk_reasons + [str(Reason.CYCLE_SHADOW_ONLY)]
        )
        decision = Decision(
            decision_id,
            prediction_id,
            self.run_id,
            t,
            t,
            action,
            f"{selection}_SELECTED" if selection in SIDES else "NONE",
            all_reasons,
            long_view,
            short_view,
            forecast_direction,
            position_state,
            RiskSnapshot(
                governor.equity,
                governor.mark,
                governor.peak,
                governor.drawdown,
                governor.locked,
                self.trade is not None,
                governor.open_trade,
            ),
            stop_distance,
            snap.price,
            t + BASE_LATENCY if action is not Action.NO_TRADE else None,
            t + HORIZON if action is not Action.NO_TRADE else None,
            str(Reason.CYCLE_SHADOW_ONLY),
        )
        self.store.append(decision)
        if action is not Action.NO_TRADE:
            assert stop_distance is not None and snap.price is not None
            quantity = filtered_quantity(governor.equity, stop_distance, snap.price, self.filters)
            assert quantity is not None
            intent = OrderIntent(
                record_key("G2I", self.run_id, t),
                self.run_id,
                decision_id,
                str(action),
                t,
                t + BASE_LATENCY,
                t + DECISION_MINUTES * MINUTE,
                t + HORIZON,
                stop_distance,
                snap.price,
                quantity,
                "MARKET_HISTORICAL_BAR_SIMULATION",
            )
            self.store.append(intent)
            self.intent = intent
            governor.pending_intent = intent.intent_id

    def _state_record(self, t: datetime, snap: StateSnapshot) -> MarketState:
        return MarketState(
            record_key("G2S", self.run_id, t),
            self.run_id,
            t,
            t,
            snap.max_source_time,
            snap.price,
            snap.raw,
            snap.term_status,
            snap.price_response,
            snap.sigma_4h,
            snap.atr14,
            snap.ewm,
            snap.daily,
            snap.weekly,
            "AVAILABLE" if snap.available else str(snap.reason),
            () if snap.available else (str(snap.reason),),
        )


def select_side(long_margin: float, short_margin: float) -> tuple[str, str]:
    """Contract section 17: the prudential-margin action rule (before risk vetoes)."""
    long_ok, short_ok = long_margin > 0, short_margin > 0
    if not long_ok and not short_ok:
        return "NONE", str(Reason.UTILITY_MARGIN_NOT_POSITIVE)
    if long_ok and not short_ok:
        return "LONG", str(Reason.LONG_SELECTED)
    if short_ok and not long_ok:
        return "SHORT", str(Reason.SHORT_SELECTED)
    if abs(long_margin - short_margin) <= MARGIN_TIE:
        return "NONE", str(Reason.UTILITY_MARGIN_TIE)
    if long_margin > short_margin:
        return "LONG", str(Reason.LONG_SELECTED)
    return "SHORT", str(Reason.SHORT_SELECTED)


def policy(
    state_available: bool,
    long_view: UtilityView,
    short_view: UtilityView,
    forecast_direction: str,
) -> tuple[str, list[str]]:
    """Utility-only selection. Both heads need prequential evidence; the terminal forecast
    direction never selects a side and only annotates an explicit override."""
    if (
        not state_available
        or long_view.prudential_margin is None
        or short_view.prudential_margin is None
    ):
        return "NONE", [str(Reason.INSUFFICIENT_POLICY_EVIDENCE)]
    selection, code = select_side(long_view.prudential_margin, short_view.prudential_margin)
    reasons = [code]
    if (selection == "LONG" and forecast_direction == "DOWN") or (
        selection == "SHORT" and forecast_direction == "UP"
    ):
        reasons.append(str(Reason.PATH_UTILITY_OVERRIDES_TERMINAL_VIEW))
    return selection, reasons
