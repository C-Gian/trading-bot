"""Frozen WP-007 orchestration around the unchanged Decimal V2 simulator.

Data admission, cost profiles, execution semantics and the walk-forward protocol are
reused unmodified from the accepted substrate; only the entry rule and its feature
source differ.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from app.backtest.engine import simulate
from app.backtest.models import ExitReason, Intent

from .continuation_lab import DATASET_HASH, DATASET_ID, MINUTE_US, PROFILES, ResearchInputs, costs
from .evaluation_protocol import EPOCH, HOUR_US, fold_contains, summarize_trades, utc_us
from .flow import (
    BALANCE,
    CONTEXT_MINUTES,
    CONTEXT_RULE,
    FEATURE_VERSION,
    STRATEGY_VERSION,
    VARIANTS,
    FlowSource,
    IneligibleFlowSignal,
)
from .order_flow import DATASET_ID as FLOW_DATASET_ID

CONFIG_DIRECTORY = "research/configs/wp007"
STEMS = {"FLOW_CORE": "flow_core", "FLOW_PRICE_RESPONSE": "flow_price_response"}


def config_path(variant: str) -> str:
    if variant not in STEMS:
        raise ValueError("undeclared strategy variant")
    return f"{CONFIG_DIRECTORY}/{STEMS[variant]}.json"


def validate_config(config: dict[str, Any]) -> None:
    """Fail closed on any structural or numeric drift from the frozen declaration."""
    expected = {
        "strategy_version": STRATEGY_VERSION,
        "variant": config.get("variant"),
        "feature_version": FEATURE_VERSION,
        "feature_dataset": FLOW_DATASET_ID,
        "balance_threshold": BALANCE,
        "context_timeframe_minutes": CONTEXT_MINUTES,
        "context_rule": CONTEXT_RULE,
        "stop_fraction": 0.02,
        "target_fraction": 0.04,
        "max_hold_minutes": 1440,
        "profiles": list(PROFILES),
    }
    if config != expected or config["variant"] not in VARIANTS:
        raise ValueError("configuration differs from frozen structural variant")


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
        f"{STRATEGY_VERSION}:{variant}",
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


class FlowLab:
    """One frozen variant/profile per trial; no selection, fitting or added profile."""

    def __init__(self, inputs: ResearchInputs, features: FlowSource, protocol: dict[str, Any]):
        self.inputs = inputs
        self.features = features
        self.protocol = protocol

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
                utc_us(fold["validation_start"]),
                utc_us(fold["last_signal_inclusive"]) + 1,
                HOUR_US,
            ):
                assert fold_contains(fold, signal_us)
                try:
                    emits, feature, reference = self.features.decision(
                        signal_us, variant, int(profile == "DELAY_1H")
                    )
                except IneligibleFlowSignal:
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
                    regime="UNCLASSIFIED",
                    feature_asof_us=feature.asof_us,
                    feature_values={
                        "current_share": feature.current_share,
                        "previous_share": feature.previous_share,
                        "context_share": feature.context_share,
                        "context_open_us": feature.context_open_us,
                        "context_close_us": feature.context_close_us,
                        "context_staleness_hours": feature.context_staleness_us // HOUR_US,
                        "price_response": feature.price_response,
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
            "summary": summarize_trades(trades, self.protocol, allow_unclassified_regime=True),
        }
