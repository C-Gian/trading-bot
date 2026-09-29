"""DevelopmentCore: the frozen G2Core plus the fixed-batch hooks needed by G2-02.

Only two methods of the frozen core are re-stated here, each as a line-for-line transcription of
`app.g2.core.G2Core` with explicit hooks:

- `_refit`: the model dictionary mask (ablations / TREND_ONLY), the NULL location-zero readout and
  the utility-head switch (references that have no utility readout);
- `_decide`: the system-version label, the optional cycle shadow, the policy mode
  (UTILITY = frozen `policy`; TREND_QUANTILE = TREND_REFERENCE_POLICY; NONE) and the
  economic-window gate (2020 is initialization only: no economic position may be opened before
  2021-01-01 00:00 UTC; forecasts, labels, residual archives and refits run unchanged).

With the G2-V0 variant and no economic gate the issued record stream is byte-identical to
`G2Core` (verified by fingerprint in `tests/test_g2_development.py`). Nothing else of the frozen
core is overridden: ingestion, aggregation, features, execution, funding, maturity, residual
archives and risk accounting are the frozen implementation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from ..bars import Bar
from ..contract import (
    BASE_LATENCY,
    COLUMNS,
    DECISION_MINUTES,
    HORIZON,
    MINUTE,
    PENALTIES,
    STOP_ATR_MULTIPLE,
)
from ..core import SIDES, G2Core, _Fit, _PendingForecast, _PendingLabel, policy
from ..distribution import (
    FALLBACK,
    PREQUENTIAL,
    Distribution,
    calibration_reason,
    direction,
    distribution,
    strength_label,
)
from ..execution import FundingBook
from ..models import (
    Readout,
    Scaler,
    SupportError,
    TrainingSet,
    check_support,
    fit_scaler,
    ridge,
    select_training,
)
from ..records import (
    Action,
    Decision,
    OrderIntent,
    Prediction,
    Reason,
    RiskSnapshot,
    RunManifest,
    SourceAuditEvent,
    UtilityView,
    record_key,
)
from ..risk import ExchangeFilters, filtered_quantity
from .variants import G2_V0, Variant

ECONOMIC_WINDOW_NOT_OPEN = "ECONOMIC_WINDOW_NOT_OPEN_INITIALIZATION_PERIOD"
TREND_NO_SIGNAL = "TREND_REFERENCE_QUANTILES_NOT_DIRECTIONAL"
TREND_UNAVAILABLE = "TREND_REFERENCE_FORECAST_UNAVAILABLE"
FORECAST_REFERENCE_ONLY = "FORECAST_REFERENCE_NO_POLICY"


class _NoCycle:
    """References/ablations do not compute the shadow cycle (it has zero role in every system)."""

    def on_bar(self, bar: Bar) -> None:
        return None


def trend_policy(dist: Distribution | None) -> tuple[str, list[str]]:
    """TREND_REFERENCE_POLICY (contract section 23): LONG iff q10 > 0; SHORT iff q90 < 0."""
    if dist is None:
        return "NONE", [TREND_UNAVAILABLE]
    if dist.q10 > 0:
        return "LONG", [str(Reason.LONG_SELECTED)]
    if dist.q90 < 0:
        return "SHORT", [str(Reason.SHORT_SELECTED)]
    return "NONE", [TREND_NO_SIGNAL]


class DevelopmentCore(G2Core):
    def __init__(
        self,
        manifest: RunManifest,
        funding: FundingBook,
        filters: ExchangeFilters,
        friction: float,
        audit: tuple[SourceAuditEvent, ...] = (),
        variant: Variant = G2_V0,
        economic_start: datetime | None = None,
    ) -> None:
        super().__init__(manifest, funding, filters, friction, audit)
        self.variant = variant
        self.economic_start = economic_start
        self._mask = variant.mask
        if not variant.cycle_shadow:
            self.cycle = _NoCycle()  # type: ignore[assignment]
        # Scoring tap (not records): the training-baseline atoms of every forecast fit, so the
        # scorer can evaluate CRPS for forecasts issued under the fallback distribution.
        self.forecast_atoms: dict[str, np.ndarray] = {}

    # ------------------------------------------------------------------ fitting
    def _fit_head(self, training: TrainingSet, scaler: Scaler, forecast: bool) -> Readout:
        check_support(training)
        if forecast and self.variant.forecast_mode == "NULL":
            return Readout(scaler, 0.0, (0.0,) * len(COLUMNS))
        xs = scaler.transform(training.x)
        fixed = tuple(
            scale is None or not active
            for scale, active in zip(scaler.scales, self._mask, strict=True)
        )
        intercept, coefficients = ridge(xs, training.y, PENALTIES, fixed)
        return Readout(scaler, intercept, tuple(float(c) for c in coefficients))

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
            readout = self._fit_head(forecast_training, scaler, True)
            atoms = forecast_training.y - forecast_training.y.mean()
            manifest = self._manifest(
                "FORECAST", t, "FITTED", "SUPPORT_MET", forecast_training, readout, scaler, atoms
            )
            self.fits["FORECAST"] = _Fit(manifest, readout, atoms)
            self.forecast_atoms[manifest.fit_id] = atoms
        except SupportError as exc:
            scaler = None
            manifest = self._manifest(
                "FORECAST", t, "UNAVAILABLE_SUPPORT", str(exc), forecast_training
            )
            self.fits["FORECAST"] = None
        self.store.append(manifest)
        if not self.variant.utility_heads:
            return
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
                    readout = self._fit_head(training, scaler, False)
                    manifest = self._manifest(
                        head, t, "FITTED", "SUPPORT_MET", training, readout, scaler
                    )
                    self.fits[head] = _Fit(manifest, readout)
                except SupportError as exc:
                    manifest = self._manifest(head, t, "UNAVAILABLE_SUPPORT", str(exc), training)
                    self.fits[head] = None
            self.store.append(manifest)

    def _manifest(self, head: str, t: datetime, *args: Any, **kwargs: Any) -> Any:
        manifest = super()._manifest(head, t, *args, **kwargs)
        if self.variant.system_version == manifest.system_version:
            return manifest
        return type(manifest)(
            **{**manifest.__dict__, "system_version": self.variant.system_version}
        )

    # ------------------------------------------------------------------ decision
    def _select(
        self,
        state_available: bool,
        long_view: UtilityView,
        short_view: UtilityView,
        forecast_direction: str,
        dist: Distribution | None,
    ) -> tuple[str, list[str]]:
        mode = self.variant.policy_mode
        if mode == "UTILITY":
            return policy(state_available, long_view, short_view, forecast_direction)
        if mode == "TREND_QUANTILE":
            return trend_policy(dist)
        return "NONE", [FORECAST_REFERENCE_ONLY]

    def _decide(self, t: datetime) -> None:
        snap = self.features.snapshot(t)
        state = self._state_record(t, snap)
        self.store.append(state)
        if self.variant.cycle_shadow:
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
            self.variant.system_version,
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
                ("model_version", self.variant.system_version),
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

        # ---- policy (G2-V0: utility only; forecast direction never forces the action)
        long_view, short_view = utilities["LONG"], utilities["SHORT"]
        selection, policy_reasons = self._select(
            snap.available, long_view, short_view, forecast_direction, dist
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
        if self.economic_start is not None and t < self.economic_start:
            risk_reasons.append(ECONOMIC_WINDOW_NOT_OPEN)
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
