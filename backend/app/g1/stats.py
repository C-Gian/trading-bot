"""Matured-only running statistics, computed by the backend (the UI never scores).

Only realizations whose `available_at` is not after the cursor count. Every hit rate is paired with
its sample size and coverage; nothing here is presented as a probability or as market evidence.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from .records import ClosedTrade, Direction, PredictionRealization, PredictionSnapshot, Side
from .store import EventStore

LABEL = "SYNTHETIC FIXTURE - NOT MARKET EVIDENCE"


def running_stats(store: EventStore, cursor: datetime) -> dict[str, Any]:
    predictions = {p.prediction_id: p for p in store.visible(PredictionSnapshot, cursor)}
    realizations = [r for r in store.of_type(PredictionRealization) if r.available_at <= cursor]
    valid = [r for r in realizations if r.resolution_validity == "VALID"]
    directional = [
        r
        for r in valid
        if predictions[r.prediction_id].predicted_direction in (Direction.UP, Direction.DOWN)
    ]
    correct = sum(1 for r in directional if r.direction_correct)
    errors = [r.magnitude_error for r in valid if r.magnitude_error is not None]
    covered = [r.interval_covered for r in valid if r.interval_covered is not None]
    by_conviction: dict[str, dict[str, int]] = {}
    for r in directional:
        conviction = predictions[r.prediction_id].conviction.value
        bucket = by_conviction.setdefault(conviction, {"matured": 0, "correct": 0})
        bucket["matured"] += 1
        bucket["correct"] += int(bool(r.direction_correct))
    trades = [t for t in store.of_type(ClosedTrade) if t.exit_time <= cursor]
    scorable = [t for t in trades if t.scorable]
    net = sum((t.net_pnl for t in scorable), Decimal(0))
    return {
        "label": LABEL,
        "predictions_issued": len(predictions),
        "predictions_unavailable": sum(
            1 for p in predictions.values() if p.predicted_direction is Direction.UNAVAILABLE
        ),
        "matured": len(realizations),
        "matured_valid": len(valid),
        "matured_unscorable": len(realizations) - len(valid),
        "directional_matured": len(directional),
        "directional_correct": correct,
        "directional_hit_rate": None if not directional else correct / len(directional),
        "directional_coverage": None if not valid else len(directional) / len(valid),
        "mean_absolute_return_error": None if not errors else sum(errors) / len(errors),
        "interval_coverage": None if not covered else sum(covered) / len(covered),
        "by_conviction": by_conviction,
        "probability_scores": "NOT_SCORED_UNCALIBRATED_SYNTHETIC",
        "closed_trades": len(trades),
        "scorable_trades": len(scorable),
        "long_trades": sum(1 for t in scorable if t.side is Side.LONG),
        "short_trades": sum(1 for t in scorable if t.side is Side.SHORT),
        "winning_trades": sum(1 for t in scorable if t.net_pnl > 0),
        "net_pnl": format(net.quantize(Decimal("0.01")), "f"),
    }
