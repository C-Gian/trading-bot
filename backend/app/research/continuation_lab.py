"""Frozen development orchestration around the existing Decimal V2 simulator."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from app.backtest.engine import simulate
from app.backtest.models import Bar, CostModel, ExitReason, Intent

from .continuation import CUTOFF_US, VARIANTS, FeatureBar, FeatureSource, IneligibleSignal
from .evaluation_protocol import (
    EPOCH,
    HOUR_US,
    fold_contains,
    summarize_trades,
    utc_us,
    validate_protocol,
)

MINUTE_US = 60_000_000
DATASET_HASH = "02168b73d8513d825978cdde3cc133e466b4aebcc0aaa48fecfb473de6e3acb2"
DATASET_ID = "BTCUSDT-SPOT-1M-DEV-v1"
MANIFEST_SHA256 = "50279396df26965188214cb39199a775f2683e70dbfe66240dc03d1fa7bc6806"
PROFILES = ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")


def costs(profile: str) -> CostModel:
    if profile not in PROFILES:
        raise ValueError("undeclared execution profile")
    scale = 0 if profile == "ZERO" else 2 if profile == "DOUBLE" else 1
    return CostModel(
        "BTCUSDT_SPOT_COST_V1" if scale == 1 else f"BTCUSDT_SPOT_COST_V1_{profile}",
        Decimal(10 * scale),
        Decimal(10 * scale),
        Decimal(2 * scale),
        Decimal(2 * scale),
    )


def validate_config(config: dict[str, Any]) -> None:
    expected = {
        "strategy_version": "ALIGNED_PARTICIPATION_CONTINUATION_V1",
        "variant": config.get("variant"),
        "feature_version": "CONTINUATION_FEATURES_V1",
        "breakout_hours": 24,
        "volume_baseline_hours": 24,
        "volume_multiplier": 2,
        "context_increments": 42,
        "up_to_down_ratio": 2,
        "stop_fraction": 0.02,
        "target_fraction": 0.04,
        "max_hold_minutes": 1440,
        "profiles": list(PROFILES),
    }
    if config != expected or config["variant"] not in VARIANTS:
        raise ValueError("configuration differs from frozen structural variant")


@dataclass
class ResearchInputs:
    features: FeatureSource
    minute_times: np.ndarray
    minute_open: np.ndarray
    minute_high: np.ndarray
    minute_low: np.ndarray
    minute_close: np.ndarray

    @classmethod
    def load(cls, root: Path) -> ResearchInputs:
        """Read only exact manifest files, after byte hashes pass and runner admission."""
        manifest_bytes = (root / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json").read_bytes()
        if hashlib.sha256(manifest_bytes.replace(b"\r\n", b"\n")).hexdigest() != MANIFEST_SHA256:
            raise ValueError("unapproved manifest bytes; refusing data access")
        manifest = json.loads(manifest_bytes)
        if (
            manifest["symbol"] != "BTCUSDT"
            or manifest["manifest_id"] != DATASET_ID
            or manifest["content_hash"]["value"] != DATASET_HASH
            or utc_us(manifest["coverage"]["end"]) != CUTOFF_US
        ):
            raise ValueError("unapproved dataset")
        tables = {}
        expected_paths = {
            "canonical": "data/canonical/BTCUSDT-1m.parquet",
            "1h": "data/derived/BTCUSDT-1h.parquet",
            "4h": "data/derived/BTCUSDT-4h.parquet",
        }
        if set(manifest["files"]) != set(expected_paths):
            raise ValueError("unexpected dataset file set")
        for key, record in manifest["files"].items():
            if record["path"] != expected_paths[key]:
                raise ValueError("unapproved data path")
            path = root / record["path"]
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() != record["sha256"]:
                raise ValueError("dataset bytes differ; refusing to inspect table")
            tables[key] = pq.read_table(path)
        minute = tables["canonical"]
        times = minute["open_time"].cast(pa.int64()).to_numpy()
        if np.any(times > CUTOFF_US) or np.any(np.diff(times) <= 0) or np.any(times % MINUTE_US):
            raise ValueError("invalid canonical timestamps")

        def feature_bars(key: str) -> tuple[FeatureBar, ...]:
            table = tables[key]
            return tuple(
                FeatureBar(int(t), float(h), float(c), float(v), bool(complete))
                for t, h, c, v, complete in zip(
                    table["open_time"].cast(pa.int64()).to_numpy(),
                    table["high"].to_numpy(),
                    table["close"].to_numpy(),
                    table["volume"].to_numpy(),
                    table["complete"].to_numpy(),
                    strict=True,
                )
            )

        return cls(
            FeatureSource(feature_bars("1h"), feature_bars("4h")),
            times,
            *(minute[key].to_numpy() for key in ("open", "high", "low", "close")),
        )

    def path(self, signal_us: int) -> tuple[Bar, ...]:
        start = int(np.searchsorted(self.minute_times, signal_us))
        end = int(np.searchsorted(self.minute_times, signal_us + 1440 * MINUTE_US))
        return tuple(
            Bar(
                EPOCH + timedelta(microseconds=int(self.minute_times[i])),
                Decimal(str(float(self.minute_open[i]))),
                Decimal(str(float(self.minute_high[i]))),
                Decimal(str(float(self.minute_low[i]))),
                Decimal(str(float(self.minute_close[i]))),
            )
            for i in range(start, end)
        )


def trade_at(
    inputs: ResearchInputs,
    signal_us: int,
    reference: float,
    variant: str,
    profile: str,
    run_id: str,
) -> tuple[dict[str, Any], int]:
    instant = EPOCH + timedelta(microseconds=signal_us)
    price = Decimal(str(reference))
    intent = Intent(
        run_id,
        f"ALIGNED_PARTICIPATION_CONTINUATION_V1:{variant}",
        DATASET_ID,
        DATASET_HASH,
        instant,
        "LONG",
        "NEXT_1M_OPEN",
        price * Decimal("0.98"),
        price * Decimal("1.04"),
        "FIXED_TARGET_OR_STOP_OR_24H",
        1440,
    )
    record = simulate(intent, inputs.path(signal_us), costs(profile))
    trade = {
        "signal_us": signal_us,
        "year": instant.year,
        "status": record.data_quality_status,
        "reason": str(record.exit_reason),
        "record": record.deterministic_dict(),
    }
    if record.data_quality_status == "VALID":
        assert record.exit_timestamp is not None and record.net_r is not None
        assert record.gross_r is not None and record.net_pnl is not None
        assert record.entry_raw_price is not None
        exit_us = utc_us(record.exit_timestamp)
        trade.update(
            exit_us=exit_us,
            net_r=float(record.net_r),
            gross_r=float(record.gross_r),
            cost_drag_r=float(record.gross_r - record.net_r),
            net_return_bps=float(record.net_pnl / record.entry_raw_price * 10000),
        )
        available_us = exit_us if record.exit_reason == ExitReason.EXPIRY else exit_us + MINUTE_US
    elif record.data_quality_status == "UNRESOLVED":
        available_us = signal_us + 1440 * MINUTE_US
    else:
        available_us = signal_us
    trade["position_available_us"] = available_us
    return trade, available_us


class ContinuationLab:
    def __init__(self, inputs: ResearchInputs, protocol: dict[str, Any]):
        validate_protocol(protocol)
        self.inputs, self.protocol = inputs, protocol

    def run_trial(self, config: dict[str, Any], trial_id: str) -> dict[str, Any]:
        validate_config(config)
        variant = config["variant"]
        profile = trial_id.rsplit(":", 1)[-1]
        if profile not in PROFILES or trial_id != f"{variant}:{profile}":
            raise ValueError("undeclared trial")
        trades: list[dict[str, Any]] = []
        diagnostics = []
        for fold in self.protocol["folds"]:
            blocked_until = -1
            eligible = ineligible = suppressed = conditions = 0
            for signal_us in range(
                utc_us(fold["validation_start"]), utc_us(fold["last_signal_inclusive"]) + 1, HOUR_US
            ):
                assert fold_contains(fold, signal_us)
                try:
                    emits, feature, reference = self.inputs.features.decision(
                        signal_us, variant, int(profile == "DELAY_1H")
                    )
                except IneligibleSignal:
                    ineligible += 1
                    continue
                eligible += 1
                if not emits:
                    continue
                conditions += 1
                if signal_us < blocked_until:
                    suppressed += 1
                    continue
                trade, blocked_until = trade_at(
                    self.inputs, signal_us, reference, variant, profile, trial_id
                )
                trade.update(
                    fold_id=fold["fold_id"],
                    regime="PERSISTENT_UP" if feature.persistent_up else "OTHER",
                    feature_asof_us=feature.asof_us,
                    feature_values={
                        "signed_efficiency": feature.signed_efficiency,
                        "relative_volume": feature.relative_volume,
                    },
                    reference=reference,
                )
                trades.append(trade)
            diagnostics.append(
                {
                    "fold_id": fold["fold_id"],
                    "eligible_clocks": eligible,
                    "ineligible_clocks": ineligible,
                    "conditions_emitted": conditions,
                    "suppressed_conditions": suppressed,
                }
            )
        return {
            "profile": profile,
            "variant": variant,
            "trades": trades,
            "clock_diagnostics": diagnostics,
            "summary": summarize_trades(trades, self.protocol),
        }
