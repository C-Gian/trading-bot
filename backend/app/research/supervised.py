"""Leakage-safe feature and isolated-label substrate for the WP-008 challenger."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from app.backtest.engine import simulate
from app.backtest.models import Intent

from .continuation_lab import DATASET_HASH, DATASET_ID, ResearchInputs, costs
from .evaluation_protocol import EPOCH, HOUR_US, utc_us
from .flow import context_open
from .order_flow import FEATURE_VERSION as ORDER_FLOW_FEATURE_VERSION
from .order_flow import read_buckets
from .wp004 import ROOT

FEATURE_VERSION = "SUPERVISED_FEATURES_V1"
LABEL_VERSION = "ISOLATED_FIXED_PLAN_DEFAULT_NET_R_V1"
STRATEGY_VERSION = "LINEAR_NET_R_SELECTION_V1"
FULL_FEATURES = (
    "LOG_RETURN_1H",
    "LOG_RETURN_24H",
    "LOG_DISTANCE_TO_PRIOR_24H_HIGH",
    "REALIZED_VOL_24H",
    "LOG_RELATIVE_VOLUME_1H",
    "DIRECTIONAL_EFFICIENCY_4H",
    "TAKER_BUY_SHARE_1H_CENTERED",
    "TAKER_BUY_SHARE_4H_CENTERED",
)
NO_FLOW_FEATURES = FULL_FEATURES[:6]
CONFIG_FEATURES = {"LINEAR_FULL": FULL_FEATURES, "LINEAR_NO_FLOW": NO_FLOW_FEATURES}
CUTOFF_US = utc_us("2024-12-31T23:59:00Z")
CONTEXT_US = 4 * HOUR_US
MINUTE_US = 60_000_000


class SupervisedDataError(ValueError):
    """Feature availability, containment, or fixed-spec validation failed."""


@dataclass(frozen=True)
class HourBar:
    open_us: int
    open: float
    high: float
    close: float
    volume: float
    share: float | None
    eligible: bool


@dataclass(frozen=True)
class ContextBar:
    open_us: int
    close: float
    share: float | None
    eligible: bool


@dataclass(frozen=True)
class SupervisedRow:
    signal_us: int
    reference: float
    context_open_us: int
    context_close_us: int
    feature_available_us: int
    values: tuple[float, ...]


@dataclass(frozen=True)
class IsolatedLabel:
    signal_us: int
    status: str
    reason: str
    outcome_us: int
    net_r: float | None


def vector_hash(signal_times: np.ndarray, values: np.ndarray, names: tuple[str, ...]) -> str:
    """Logical float64 matrix identity independent of JSON/Parquet encoding."""
    times = np.asarray(signal_times, dtype="<i8")
    matrix = np.asarray(values, dtype="<f8")
    if matrix.ndim != 2 or matrix.shape != (len(times), len(names)):
        raise SupervisedDataError("matrix shape does not match timestamps and feature order")
    if not np.isfinite(matrix).all():
        raise SupervisedDataError("feature matrix contains non-finite values")
    digest = hashlib.sha256()
    digest.update(json.dumps(list(names), separators=(",", ":")).encode())
    digest.update(np.asarray(matrix.shape, dtype="<i8").tobytes())
    digest.update(times.tobytes())
    digest.update(matrix.tobytes(order="C"))
    return digest.hexdigest()


def label_hash(signal_times: np.ndarray, labels: np.ndarray, outcomes: np.ndarray) -> str:
    times = np.asarray(signal_times, dtype="<i8")
    target = np.asarray(labels, dtype="<f8")
    outcome_times = np.asarray(outcomes, dtype="<i8")
    if len(times) != len(target) or len(times) != len(outcome_times):
        raise SupervisedDataError("label arrays have inconsistent lengths")
    if not np.isfinite(target).all():
        raise SupervisedDataError("labels contain non-finite values")
    digest = hashlib.sha256()
    digest.update(LABEL_VERSION.encode())
    digest.update(times.tobytes())
    digest.update(target.tobytes())
    digest.update(outcome_times.tobytes())
    return digest.hexdigest()


class SupervisedFeatureSource:
    """Completed historical bars only; execution paths are held separately."""

    def __init__(self, hourly: tuple[HourBar, ...], context: tuple[ContextBar, ...]):
        self.hourly = {bar.open_us: bar for bar in hourly}
        self.context = {bar.open_us: bar for bar in context}
        if len(self.hourly) != len(hourly) or len(self.context) != len(context):
            raise SupervisedDataError("feature bars must have unique timestamps")
        for bars, width in ((hourly, HOUR_US), (context, CONTEXT_US)):
            previous = -1
            for bar in bars:
                if bar.open_us <= previous or bar.open_us % width or bar.open_us > CUTOFF_US:
                    raise SupervisedDataError("misaligned, unordered, or post-cutoff feature bar")
                previous = bar.open_us
        self._cache: dict[int, SupervisedRow] = {}

    def at(self, signal_us: int) -> SupervisedRow:
        if signal_us % HOUR_US or signal_us > CUTOFF_US:
            raise SupervisedDataError("signal is misaligned or post-cutoff")
        if signal_us in self._cache:
            return self._cache[signal_us]
        hour_opens = [signal_us - offset * HOUR_US for offset in range(25, 0, -1)]
        hours = [self.hourly.get(open_us) for open_us in hour_opens]
        if any(bar is None or not bar.eligible for bar in hours):
            raise SupervisedDataError("hourly feature window is incomplete or quarantined")
        exact_hours = [bar for bar in hours if bar is not None]
        opened = context_open(signal_us)
        context_opens = [opened - offset * CONTEXT_US for offset in range(42, -1, -1)]
        contexts = [self.context.get(open_us) for open_us in context_opens]
        if any(bar is None or not bar.eligible for bar in contexts):
            raise SupervisedDataError("4h feature window is incomplete or quarantined")
        exact_contexts = [bar for bar in contexts if bar is not None]
        current = exact_hours[-1]
        current_context = exact_contexts[-1]
        if current.share is None or current_context.share is None:
            raise SupervisedDataError("required order-flow share is unavailable")
        if current.open <= 0 or current.close <= 0:
            raise SupervisedDataError("hourly prices must be positive")
        if any(bar.close <= 0 or bar.high <= 0 for bar in exact_hours):
            raise SupervisedDataError("hourly lookback prices must be positive")
        previous_volumes = [bar.volume for bar in exact_hours[:-1]]
        volume_mean = math.fsum(previous_volumes) / 24
        if current.volume <= 0 or volume_mean <= 0:
            raise SupervisedDataError("relative volume requires positive numerator and denominator")
        hourly_returns = [
            math.log(exact_hours[index].close / exact_hours[index - 1].close)
            for index in range(1, 25)
        ]
        changes = [
            exact_contexts[index].close - exact_contexts[index - 1].close for index in range(1, 43)
        ]
        up = math.fsum(max(change, 0.0) for change in changes)
        down = math.fsum(max(-change, 0.0) for change in changes)
        if up + down == 0:
            raise SupervisedDataError("directional efficiency denominator is zero")
        context_close_us = opened + CONTEXT_US
        if context_close_us > signal_us - HOUR_US:
            raise SupervisedDataError("4h context overlaps the current hourly bar")
        values = (
            math.log(current.close / current.open),
            math.log(current.close / exact_hours[0].close),
            math.log(current.close / max(bar.high for bar in exact_hours[:-1])),
            math.sqrt(math.fsum(value * value for value in hourly_returns) / 24),
            math.log(current.volume / volume_mean),
            (up - down) / (up + down),
            current.share - 0.5,
            current_context.share - 0.5,
        )
        if not all(math.isfinite(value) for value in values):
            raise SupervisedDataError("feature vector contains a non-finite value")
        row = SupervisedRow(
            signal_us=signal_us,
            reference=current.close,
            context_open_us=opened,
            context_close_us=context_close_us,
            feature_available_us=signal_us,
            values=values,
        )
        self._cache[signal_us] = row
        return row


def _verified_hourly_highs(root: Path) -> dict[int, tuple[float, bool]]:
    manifest = json.loads((root / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json").read_text())
    record = manifest["files"]["1h"]
    path = root / record["path"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != record["sha256"]:
        raise SupervisedDataError("hourly source bytes differ from accepted manifest")
    table = pq.read_table(path, columns=["open_time", "high", "complete"])
    times = table["open_time"].cast(pa.int64()).to_numpy()
    if np.any(times > CUTOFF_US):
        raise SupervisedDataError("post-cutoff hourly data is forbidden")
    return {
        int(open_us): (float(high), bool(complete))
        for open_us, high, complete in zip(
            times, table["high"].to_numpy(), table["complete"].to_numpy(), strict=True
        )
    }


def load_feature_source(root: Path = ROOT) -> SupervisedFeatureSource:
    highs = _verified_hourly_highs(root)
    flow_hours = read_buckets("1h", root)
    contexts = read_buckets("4h", root)
    hourly = []
    for bucket in flow_hours:
        high = highs.get(bucket.open_us)
        if high is None:
            raise SupervisedDataError("order-flow and hourly source timestamps diverged")
        hourly.append(
            HourBar(
                bucket.open_us,
                bucket.open,
                high[0],
                bucket.close,
                bucket.volume,
                bucket.share,
                bucket.eligible and high[1],
            )
        )
    context = tuple(
        ContextBar(bucket.open_us, bucket.close, bucket.share, bucket.eligible)
        for bucket in contexts
    )
    return SupervisedFeatureSource(tuple(hourly), context)


def isolated_label(inputs: ResearchInputs, row: SupervisedRow) -> IsolatedLabel:
    """One independent DEFAULT-cost plan; no position occupancy between labels."""
    instant = EPOCH + timedelta(microseconds=row.signal_us)
    reference = Decimal(str(row.reference))
    intent = Intent(
        f"{LABEL_VERSION}:{row.signal_us}",
        LABEL_VERSION,
        DATASET_ID,
        DATASET_HASH,
        instant,
        "LONG",
        "NEXT_1M_OPEN",
        reference * Decimal("0.98"),
        reference * Decimal("1.04"),
        "FIXED_TARGET_OR_STOP_OR_24H",
        1440,
    )
    record = simulate(intent, inputs.path(row.signal_us), costs("DEFAULT"))
    if record.exit_timestamp is not None:
        outcome_us = utc_us(record.exit_timestamp)
    else:
        outcome_us = row.signal_us + 1440 * MINUTE_US
    return IsolatedLabel(
        row.signal_us,
        record.data_quality_status,
        str(record.exit_reason),
        outcome_us,
        float(record.net_r) if record.net_r is not None else None,
    )


def validate_protocol(document: dict[str, Any]) -> None:
    if document["protocol_id"] != "WP-008-LINEAR-NET-R-V1":
        raise SupervisedDataError("supervised protocol identity changed")
    if tuple(document["features"]["LINEAR_FULL"]) != FULL_FEATURES:
        raise SupervisedDataError("LINEAR_FULL feature order changed")
    if tuple(document["features"]["LINEAR_NO_FLOW"]) != NO_FLOW_FEATURES:
        raise SupervisedDataError("LINEAR_NO_FLOW must remove exactly F7/F8")
    training, model, execution = document["training"], document["model"], document["execution"]
    if (
        training["purge_boundary_hours"] != 216
        or training["scaling"] != "TRAINING_ONLY_MEAN_STD_DDOF_0_PER_FOLD_CONFIGURATION"
        or training["label"] != LABEL_VERSION
        or model["algorithm"] != "NUMPY_FLOAT64_ORDINARY_LEAST_SQUARES_WITH_INTERCEPT"
        or model["signal_threshold"] != 0.0
        or model["threshold_searches"] != 0
        or model["hyperparameter_searches"] != 0
        or execution["stop_fraction"] != 0.02
        or execution["target_fraction"] != 0.04
        or execution["max_hold_minutes"] != 1440
        or document["profiles"] != ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"]
        or document["model_fits"] != 12
        or document["profile_evaluations"] != 8
    ):
        raise SupervisedDataError("supervised protocol drifted from the fixed declaration")


def load_supervised_protocol(root: Path = ROOT) -> dict[str, Any]:
    document = json.loads(
        (root / "research/protocols/WP-008-LINEAR-NET-R-V1.json").read_text(encoding="utf-8")
    )
    validate_protocol(document)
    return document


def dependency_identity(root: Path = ROOT) -> dict[str, str]:
    paths = (
        "backend/app/research/supervised.py",
        "backend/app/research/order_flow.py",
        "backend/app/research/continuation_lab.py",
        "backend/app/backtest/engine.py",
        "backend/app/backtest/models.py",
        "research/protocols/WP-008-LINEAR-NET-R-V1.json",
        "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json",
        "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json",
        "data/manifests/BTCUSDT-SPOT-ORDERFLOW-DEV-v1.json",
    )
    return {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}


__all__ = [
    "CONFIG_FEATURES",
    "FEATURE_VERSION",
    "FULL_FEATURES",
    "LABEL_VERSION",
    "NO_FLOW_FEATURES",
    "ORDER_FLOW_FEATURE_VERSION",
    "ContextBar",
    "HourBar",
    "IsolatedLabel",
    "SupervisedDataError",
    "SupervisedFeatureSource",
    "SupervisedRow",
    "dependency_identity",
    "isolated_label",
    "label_hash",
    "load_feature_source",
    "load_supervised_protocol",
    "vector_hash",
]
