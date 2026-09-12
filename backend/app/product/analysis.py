"""One deterministic on-demand ALIGNED paper-research analysis.

The frozen `ALIGNED_PARTICIPATION_CONTINUATION_V1` gates, thresholds and plan geometry
are reused unchanged: 2% stop, 4% target, LONG or NO_TRADE only, next 1m open entry,
1,440 minute maximum hold. Nothing here fits, tunes, ranks or persists anything, and the
result is transient. ALIGNED is a paper-research candidate, never a Champion.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from ..research.continuation import FeatureBar, IneligibleSignal
from . import PRODUCT_ANALYSIS_VERSION
from .features import HOUR_US, PROSPECTIVE_FEATURES_VERSION, ProspectiveFeatureSource
from .market_feed import Kline, MarketFeedError, fetch_klines

STRATEGY_VERSION = "ALIGNED_PARTICIPATION_CONTINUATION_V1"
VARIANT = "ALIGNED"
FEATURE_VERSION = "CONTINUATION_FEATURES_V2"
PROSPECTIVE_FEATURES = PROSPECTIVE_FEATURES_VERSION
RESEARCH_STATUS = "PAPER_RESEARCH_CANDIDATE"
CHAMPION_STATUS = "NONE"
CLASSIFICATION = "EXPERIMENTAL PAPER RESEARCH — NOT AN APPROVED LIVE STRATEGY"
SYMBOL = "BTCUSDT"
DIRECTION = "LONG"
ENTRY_RULE = "NEXT_1M_OPEN"
EXIT_POLICY = "FIXED_TARGET_OR_STOP_OR_24H"
EXECUTION_MODEL = "EXECUTION_MODEL_V2"
STOP_FRACTION = Decimal("0.98")
TARGET_FRACTION = Decimal("1.04")
MAX_HOLD_MINUTES = 1440

# The frozen decision evaluates both feature clocks, so it needs the union of the
# lookbacks at the signal hour and at the hour before it: 26 hourly and 44 four-hour bars.
REQUIRED_HOURLY = 26
REQUIRED_CONTEXT = 44
HOURLY_LIMIT = 48
CONTEXT_LIMIT = 64
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _bars(klines: tuple[Kline, ...]) -> tuple[FeatureBar, ...]:
    return tuple(
        FeatureBar(kline.open_ms * 1000, kline.high, kline.close, kline.volume, True)
        for kline in klines
    )


def analysis_identity(result: dict[str, Any]) -> str:
    """Stable identity of one evaluated signal, so a trade cannot be created twice."""
    plan = result.get("plan") or {}
    payload = {
        "strategy_version": result["strategy_version"],
        "variant": result["variant"],
        "feature_version": result["feature_version"],
        "signal_time": result["signal_time"],
        "decision": result["decision"],
        "reference_price": plan.get("reference_price"),
        "stop_price": plan.get("stop_price"),
        "target_price": plan.get("target_price"),
        "max_hold_minutes": plan.get("max_hold_minutes"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _instant(micros: int) -> str:
    return (EPOCH + timedelta(microseconds=micros)).isoformat().replace("+00:00", "Z")


def _incomplete(status: str, detail: str, now: datetime) -> dict[str, Any]:
    """Fail closed: an analysis that cannot be evaluated is never a trade plan."""
    return {
        "analysis_version": PRODUCT_ANALYSIS_VERSION,
        "classification": CLASSIFICATION,
        "symbol": SYMBOL,
        "strategy_version": STRATEGY_VERSION,
        "variant": VARIANT,
        "feature_version": FEATURE_VERSION,
        "prospective_features_version": PROSPECTIVE_FEATURES,
        "research_status": RESEARCH_STATUS,
        "champion_status": CHAMPION_STATUS,
        "analysis_time": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "signal_time": None,
        "data_status": status,
        "data_detail": detail,
        "decision": "NO_TRADE",
        "plan": None,
        "paper_trade_persisted": False,
        "real_money": False,
    }


def analyse(
    *, now: datetime | None = None, client: Any = None, feed: Any = fetch_klines
) -> dict[str, Any]:
    """Evaluate the frozen ALIGNED rule once against current public market data."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    kwargs: dict[str, Any] = {"now": now}
    if client is not None:
        kwargs["client"] = client
    try:
        hourly = feed("1h", HOURLY_LIMIT, **kwargs)
        context = feed("4h", CONTEXT_LIMIT, **kwargs)
    except MarketFeedError as exc:
        return _incomplete("MARKET_DATA_UNAVAILABLE", str(exc), now)
    if len(hourly) < REQUIRED_HOURLY or len(context) < REQUIRED_CONTEXT:
        return _incomplete(
            "INCOMPLETE_MARKET_DATA",
            f"received {len(hourly)}/{REQUIRED_HOURLY} hourly "
            f"and {len(context)}/{REQUIRED_CONTEXT} four-hour completed bars",
            now,
        )

    signal_us = (hourly[-1].open_ms * 1000 // HOUR_US + 1) * HOUR_US
    try:
        source = ProspectiveFeatureSource(_bars(hourly), _bars(context))
        emits, feature, reference = source.decision(signal_us, VARIANT)
    except IneligibleSignal as exc:
        return _incomplete("INCOMPLETE_MARKET_DATA", str(exc), now)
    except ValueError as exc:
        return _incomplete("INVALID_MARKET_DATA", str(exc), now)

    result = _incomplete("OK", "completed contiguous lookback available", now)
    result["signal_time"] = _instant(signal_us)
    result["reference_price"] = float(reference)
    result["features"] = {
        "breakout": feature.breakout,
        "persistent_up": feature.persistent_up,
        "participation": feature.participation,
        "signed_efficiency": feature.signed_efficiency,
        "relative_volume": feature.relative_volume,
    }
    if not emits:
        result["analysis_id"] = analysis_identity(result)
        return result
    price = Decimal(str(reference))
    result["decision"] = DIRECTION
    result["plan"] = {
        "direction": DIRECTION,
        "entry_rule": ENTRY_RULE,
        "entry_semantics": (
            "Paper entry at the next completed 1m open after the signal hour, "
            "with adverse entry friction under EXECUTION_MODEL_V2."
        ),
        "execution_model": EXECUTION_MODEL,
        "exit_policy": EXIT_POLICY,
        "reference_price": float(reference),
        "stop_price": float(price * STOP_FRACTION),
        "target_price": float(price * TARGET_FRACTION),
        "stop_fraction": 0.02,
        "target_fraction": 0.04,
        "max_hold_minutes": MAX_HOLD_MINUTES,
        "expiry_time": _instant(signal_us + MAX_HOLD_MINUTES * 60 * 1_000_000),
        "leverage": False,
        "short": False,
        "order_placed": False,
    }
    result["analysis_id"] = analysis_identity(result)
    return result
