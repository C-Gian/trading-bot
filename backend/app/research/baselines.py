from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
MINUTE_US = 60_000_000
HOUR_US = 60 * MINUTE_US
CUTOFF_US = 1_735_689_540_000_000


def random_seed(index: int) -> int:
    digest = hashlib.sha256(f"RANDOM_ENTRY_CONTROL_V1:{index}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def random_draw(seed: int, signal_us: int) -> float:
    digest = hashlib.sha256(f"{seed}:{signal_us}".encode()).digest()
    return int.from_bytes(digest, "big") / (1 << 256)


def signal_for(rule: str, closes: np.ndarray, highs: np.ndarray, index: int) -> bool:
    if index < 168 or index >= len(closes) or index >= len(highs):
        raise ValueError("required as-of history is unavailable")
    if rule == "TREND":
        return float(closes[index - 23 : index + 1].mean()) > float(
            closes[index - 167 : index + 1].mean()
        )
    if rule == "BREAKOUT":
        return float(closes[index]) > float(highs[index - 24 : index].max())
    if rule == "TREND_DELAY_1H":
        return float(closes[index - 24 : index].mean()) > float(closes[index - 168 : index].mean())
    if rule == "NO_TRADE":
        return False
    raise ValueError(f"unsupported fixed rule: {rule}")


@dataclass
class MarketData:
    minute_times: np.ndarray
    minute_open: np.ndarray
    minute_high: np.ndarray
    minute_low: np.ndarray
    minute_close: np.ndarray
    hour_times: np.ndarray
    hour_close: np.ndarray
    hour_high: np.ndarray
    eligible_indices: np.ndarray

    @classmethod
    def load(cls) -> MarketData:
        minute = pq.read_table(ROOT / "data/canonical/BTCUSDT-1m.parquet")
        hourly = pq.read_table(ROOT / "data/derived/BTCUSDT-1h.parquet")
        minute_times = minute["open_time"].cast(pa.int64()).to_numpy()
        hour_times = hourly["open_time"].cast(pa.int64()).to_numpy()
        complete = hourly["complete"].to_numpy()
        run, eligible = 0, []
        for index, value in enumerate(hour_times):
            contiguous = index == 0 or value == hour_times[index - 1] + HOUR_US
            run = run + 1 if complete[index] and contiguous else (1 if complete[index] else 0)
            signal_us = int(value + HOUR_US)
            if run >= 169 and signal_us <= CUTOFF_US:
                position = int(np.searchsorted(minute_times, signal_us))
                if position < len(minute_times) and minute_times[position] == signal_us:
                    eligible.append(index)
        return cls(
            minute_times,
            minute["open"].to_numpy(),
            minute["high"].to_numpy(),
            minute["low"].to_numpy(),
            minute["close"].to_numpy(),
            hour_times,
            hourly["close"].to_numpy(),
            hourly["high"].to_numpy(),
            np.asarray(eligible, dtype=np.int64),
        )


class FixedBaselineLab:
    def __init__(self, data: MarketData | None = None):
        self.data = data or MarketData.load()

    def run_trial(self, config: dict[str, Any], trial_id: str) -> dict[str, Any]:
        if config["rule"] == "BUYHOLD":
            return self._buyhold(config)
        seed = None
        if config["rule"] == "RANDOM":
            trial_index = int(trial_id.rsplit("-", 1)[1])
            seed = config["seeds"][trial_index]
            if seed != random_seed(trial_index):
                raise ValueError("random seed does not match the declared SHA-256 derivation")
        profile = (
            config["profiles"][int(trial_id.rsplit("-", 1)[1])]
            if "profiles" in config
            else config["cost"]
        )
        trades: list[dict[str, Any]] = []
        attempted = invalid = unresolved = 0
        blocked_until = -1
        for hour_index in self.data.eligible_indices:
            signal_us = int(self.data.hour_times[hour_index] + HOUR_US)
            if signal_us < blocked_until:
                continue
            emits = (
                random_draw(seed, signal_us) < 1 / 24
                if seed is not None
                else signal_for(
                    config["rule"], self.data.hour_close, self.data.hour_high, int(hour_index)
                )
            )
            if not emits:
                continue
            attempted += 1
            trade = self._trade(signal_us, float(self.data.hour_close[hour_index]), profile)
            trade["signal_us"] = signal_us
            trades.append(trade)
            if trade["status"] == "INVALID":
                invalid += 1
            elif trade["status"] == "UNRESOLVED":
                unresolved += 1
                blocked_until = signal_us + 1440 * MINUTE_US
            else:
                blocked_until = trade["exit_us"]
        metrics = calculate_metrics(trades, attempted, invalid, unresolved)
        return {"seed": seed or 0, "profile": profile["name"], "metrics": metrics, "trades": trades}

    def _trade(self, signal_us: int, reference: float, profile: dict[str, Any]) -> dict[str, Any]:
        index = int(np.searchsorted(self.data.minute_times, signal_us))
        if index >= len(self.data.minute_times) or self.data.minute_times[index] != signal_us:
            return {"status": "INVALID", "reason": "MISSING_ENTRY"}
        entry, stop, target = (
            float(self.data.minute_open[index]),
            reference * 0.98,
            reference * 1.04,
        )
        if entry <= stop or entry >= target:
            return {"status": "INVALID", "reason": "NON_TRADABLE"}
        end = min(index + 1440, len(self.data.minute_times))
        times = self.data.minute_times[index:end]
        gaps = np.flatnonzero(np.diff(times) != MINUTE_US)
        stop_hits = self.data.minute_low[index:end] <= stop
        target_hits = self.data.minute_high[index:end] >= target
        hits = np.flatnonzero(stop_hits | target_hits)
        event_offset = int(hits[0]) if len(hits) else len(times) - 1
        if len(gaps) and int(gaps[0]) + 1 <= event_offset:
            return {"status": "UNRESOLVED", "reason": "DATA_GAP"}
        if len(times) < 1440 and not len(hits):
            return {"status": "UNRESOLVED", "reason": "END_OF_DATA"}
        offset = event_offset
        raw_open = float(self.data.minute_open[index + offset])
        if len(hits):
            if raw_open < stop:
                exit_price, reason = raw_open, "STOP_GAP"
            elif raw_open >= target:
                exit_price, reason = target, "TARGET"
            elif stop_hits[offset]:
                exit_price, reason = stop, "STOP_FIRST"
            else:
                exit_price, reason = target, "TARGET"
            exit_us = int(times[offset])
        else:
            exit_price, reason, exit_us = (
                float(self.data.minute_close[index + offset]),
                "EXPIRY",
                int(times[offset] + MINUTE_US),
            )
        entry_fee = profile["entry_fee_bps"] / 10_000
        exit_fee = profile["exit_fee_bps"] / 10_000
        entry_effective = entry * (1 + profile["entry_friction_bps"] / 10_000)
        exit_effective = exit_price * (1 - profile["exit_friction_bps"] / 10_000)
        risk = entry - stop
        gross_r = (exit_price - entry) / risk
        net_r = (
            exit_effective
            - entry_effective
            - entry_effective * entry_fee
            - exit_effective * exit_fee
        ) / risk
        return {
            "status": "VALID",
            "reason": reason,
            "exit_us": exit_us,
            "gross_r": round(gross_r, 10),
            "net_r": round(net_r, 10),
            "cost_drag_r": round(gross_r - net_r, 10),
            "year": int(np.datetime64(signal_us, "us").astype("datetime64[Y]").astype(int) + 1970),
        }

    def _buyhold(self, config: dict[str, Any]) -> dict[str, Any]:
        entry, exit_price = float(self.data.minute_open[0]), float(self.data.minute_close[-1])
        profile = config["cost"]
        gross = exit_price / entry - 1
        net = (
            exit_price
            * (1 - profile["exit_friction_bps"] / 10_000)
            * (1 - profile["exit_fee_bps"] / 10_000)
            / (
                entry
                * (1 + profile["entry_friction_bps"] / 10_000)
                * (1 + profile["entry_fee_bps"] / 10_000)
            )
            - 1
        )
        return {
            "seed": 0,
            "profile": profile["name"],
            "metrics": {
                "net_total_return": round(net, 10),
                "gross_total_return": round(gross, 10),
                "cost_drag": round(gross - net, 10),
                "coverage_minutes": int(
                    (self.data.minute_times[-1] - self.data.minute_times[0]) / MINUTE_US
                )
                + 1,
                "first_timestamp_us": int(self.data.minute_times[0]),
                "last_timestamp_us": int(self.data.minute_times[-1]),
            },
            "trades": [],
        }


def calculate_metrics(
    trades: list[dict[str, Any]], attempted: int, invalid: int, unresolved: int
) -> dict[str, Any]:
    resolved = [x for x in trades if x["status"] == "VALID"]
    values = np.asarray([x["net_r"] for x in resolved], dtype=float)
    gross = np.asarray([x["gross_r"] for x in resolved], dtype=float)
    if not len(values):
        return {
            "attempted_setups": attempted,
            "trade_count": 0,
            "invalid_attempts": invalid,
            "unresolved_trades": unresolved,
            "unresolved_rate": unresolved / attempted if attempted else 0,
            "net_expectancy_r": None,
            "cumulative_net_r": None,
            "profit_factor": None,
            "maximum_drawdown_r": None,
            "hit_rate": None,
            "average_win_r": None,
            "average_loss_r": None,
            "cost_drag_r": None,
            "yearly": {},
        }
    equity = np.cumsum(values)
    peaks = np.maximum.accumulate(np.insert(equity, 0, 0))[1:]
    wins = values[values > 0]
    losses = values[values < 0]
    yearly = {}
    for year in sorted({x["year"] for x in resolved}):
        vals = [x["net_r"] for x in resolved if x["year"] == year]
        yearly[str(year)] = {
            "trades": len(vals),
            "expectancy_r": round(float(np.mean(vals)), 10),
            "cumulative_net_r": round(float(np.sum(vals)), 10),
        }
    return {
        "attempted_setups": attempted,
        "trade_count": len(resolved),
        "invalid_attempts": invalid,
        "unresolved_trades": unresolved,
        "unresolved_rate": round(unresolved / attempted, 10) if attempted else 0,
        "net_expectancy_r": round(float(values.mean()), 10),
        "cumulative_net_r": round(float(values.sum()), 10),
        "profit_factor": round(float(wins.sum() / -losses.sum()), 10) if len(losses) else None,
        "maximum_drawdown_r": round(float(np.max(peaks - equity)), 10),
        "hit_rate": round(float((values > 0).mean()), 10),
        "average_win_r": round(float(wins.mean()), 10) if len(wins) else None,
        "average_loss_r": round(float(losses.mean()), 10) if len(losses) else None,
        "cost_drag_r": round(float((gross - values).sum()), 10),
        "yearly": yearly,
    }
