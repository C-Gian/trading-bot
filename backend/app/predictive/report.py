"""Deterministic baseline report for `PREDICTIVE-BASELINES-V1`.

Builds the label set, the folds and the four baselines from the governed hourly artifact,
scores them under the frozen contract, and emits one JSON document. The document is a
reference report, not an experiment result: no hypothesis is tested, nothing is promoted,
and no Champion is created.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import (
    EVALUATION_CONTRACT,
    EVALUATION_CONTRACT_AMENDMENT,
    HORIZON_HOURS,
    PREDICTIVE_FOUNDATION_VERSION,
    PROTOCOL_PATH,
)
from .baselines import (
    ALWAYS_UP,
    BASELINE_NAMES,
    DECLARATIONS,
    PREVIOUS_24H_SIGN_PERSISTENCE,
    TRAINING_UP_BASE_RATE,
    ZERO_RETURN_MAGNITUDE,
    always_up_predictions,
    fit_training_up_base_rate,
    previous_24h_sign_predictions,
    training_up_base_rate_predictions,
    zero_return_magnitude_predictions,
)
from .evaluation import (
    BLOCK_LENGTH_HOURS,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    MAGNITUDE_EPSILON,
    RELIABILITY_BIN_EDGES,
    Outcome,
    Prediction,
    score,
)
from .folds import (
    FOLD_BOUNDARIES,
    FOLD_DESIGN,
    PURGE_EMBARGO_HOURS,
    Fold,
    FoldSet,
    assert_no_boundary_leak,
    build_folds,
)
from .labels import Bar, Label, LabelSet, build_labels, index_bars, load_hourly_bars

ROOT = Path(__file__).resolve().parents[3]
REPORT_PATH = "reports/research/PREDICTIVE-BASELINES-V1.json"


def _outcomes(labels: Sequence[Label]) -> list[Outcome]:
    return [
        Outcome(open_time=label.open_time, r_24h=label.r_24h, direction=label.direction)
        for label in labels
    ]


def _predictions(
    name: str, fold: Fold, bars_by_open: dict[int, Bar]
) -> tuple[list[Prediction], dict[str, Any] | None]:
    if name == TRAINING_UP_BASE_RATE:
        fit = fit_training_up_base_rate(fold.training)
        return training_up_base_rate_predictions(fit, fold.evaluation), fit.as_record()
    if name == ALWAYS_UP:
        return always_up_predictions(fold.evaluation), None
    if name == PREVIOUS_24H_SIGN_PERSISTENCE:
        return previous_24h_sign_predictions(fold.evaluation, bars_by_open), None
    if name == ZERO_RETURN_MAGNITUDE:
        return zero_return_magnitude_predictions(fold.evaluation), None
    raise ValueError(f"unknown baseline: {name}")


def _score_baseline(name: str, predictions: Sequence[Prediction], labels: Sequence[Label]):
    declares = DECLARATIONS[name]
    return score(
        predictions,
        _outcomes(labels),
        declares_direction=declares["direction"],
        declares_probability=declares["probability"],
        declares_magnitude=declares["magnitude"],
    )


def build_report(root: Path = ROOT, bars: Sequence[Bar] | None = None) -> dict[str, Any]:
    """Compute the frozen baseline report. Deterministic given the governed artifact."""
    resolved = tuple(bars) if bars is not None else load_hourly_bars(root)
    bars_by_open = index_bars(resolved)
    label_set: LabelSet = build_labels(resolved, horizon_hours=HORIZON_HOURS)
    fold_set: FoldSet = build_folds(
        label_set.labels, horizon_hours=HORIZON_HOURS, purge_embargo_hours=PURGE_EMBARGO_HOURS
    )
    assert_no_boundary_leak(fold_set)

    baselines: dict[str, Any] = {}
    for name in BASELINE_NAMES:
        per_fold: dict[str, Any] = {}
        pooled_predictions: list[Prediction] = []
        pooled_labels: list[Label] = []
        for fold in fold_set.folds:
            predictions, fit = _predictions(name, fold, bars_by_open)
            record = _score_baseline(name, predictions, fold.evaluation)
            if fit is not None:
                record["fit"] = fit
            record["training_labels"] = len(fold.training)
            per_fold[fold.name] = record
            pooled_predictions.extend(predictions)
            pooled_labels.extend(fold.evaluation)
        baselines[name] = {
            "declares": DECLARATIONS[name],
            "pooled": _score_baseline(name, pooled_predictions, pooled_labels),
            "by_fold": per_fold,
        }

    return {
        "version": PREDICTIVE_FOUNDATION_VERSION,
        "classification": "BASELINE_REFERENCE_REPORT_NOT_AN_EXPERIMENT_RESULT",
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": EVALUATION_CONTRACT_AMENDMENT,
        "protocol": PROTOCOL_PATH,
        "target": {
            "symbol": "BTCUSDT",
            "horizon_hours": HORIZON_HOURS,
            "decision_cadence_hours": 1,
            "label": "r_24h = log(close[T + 24h] / close[T])",
        },
        "labels": label_set.accounting(),
        "folds": {
            "design": FOLD_DESIGN,
            "random_k_fold": False,
            "purge_embargo_hours": PURGE_EMBARGO_HOURS,
            "boundary_leak_checked": True,
            "eligible_decision_timestamps": fold_set.eligible_total(),
            "admissible_not_assigned": fold_set.unassigned,
            "by_fold": {
                fold.name: {
                    "start": start,
                    "end": end,
                    "training_labels": len(fold.training),
                    "eligible_decision_timestamps": len(fold.evaluation),
                }
                for fold, (_, start, end) in zip(fold_set.folds, FOLD_BOUNDARIES, strict=True)
            },
        },
        "scoring": {
            "magnitude_epsilon": MAGNITUDE_EPSILON,
            "reliability_bin_edges": list(RELIABILITY_BIN_EDGES),
            "bootstrap": {
                "method": "MOVING_BLOCK_BOOTSTRAP",
                "block_length_hours": BLOCK_LENGTH_HOURS,
                "replicates": BOOTSTRAP_REPLICATES,
                "seed": BOOTSTRAP_SEED,
                "pooled_sequence": "FOLD_EVALUATION_SETS_CONCATENATED_IN_CHRONOLOGICAL_ORDER",
            },
        },
        "baselines": baselines,
        "boundaries": {
            "model_fits": 0,
            "parameter_search": False,
            "external_data": False,
            "sealed_queries": 0,
            "post_cutoff_market_data": False,
            "champion_created": False,
            "baseline_promoted_to_candidate": False,
            "real_money": False,
        },
    }


def report_bytes(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def load_report(root: Path = ROOT) -> dict[str, Any]:
    return json.loads((root / REPORT_PATH).read_text(encoding="utf-8"))


def validate_report(root: Path = ROOT, *, data_available: bool = False) -> dict[str, Any]:
    """Check the committed report against the frozen protocol, and the data when present.

    Without the market data installed this proves the report is internally consistent and
    still matches the frozen protocol. With the data installed it additionally proves the
    committed bytes are exactly what the current code recomputes.
    """
    report = load_report(root)
    protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    findings: dict[str, Any] = {"status": "PASS", "data_replayed": False}

    if report["version"] != PREDICTIVE_FOUNDATION_VERSION:
        raise ValueError("the baseline report version drifted from the implementation")
    if report["classification"] != "BASELINE_REFERENCE_REPORT_NOT_AN_EXPERIMENT_RESULT":
        raise ValueError("a baseline report may never be reclassified as a result")
    if report["evaluation_contract_amendment"] != protocol["evaluation_contract_amendment"]:
        raise ValueError("the report and the protocol disagree about the contract amendment")

    scoring, frozen = report["scoring"], protocol["scoring"]
    if scoring["magnitude_epsilon"] != frozen["magnitude_match_epsilon"]:
        raise ValueError("the magnitude epsilon drifted from the frozen protocol")
    if scoring["reliability_bin_edges"] != frozen["reliability_bin_edges"]:
        raise ValueError("the reliability bins drifted from the frozen protocol")
    bootstrap, declared = scoring["bootstrap"], protocol["uncertainty"]
    for key, expected in (
        ("block_length_hours", declared["block_length_hours"]),
        ("replicates", declared["replicates"]),
        ("seed", declared["seed"]),
    ):
        if bootstrap[key] != expected:
            raise ValueError(f"the bootstrap {key} drifted from the frozen protocol")
    if report["folds"]["purge_embargo_hours"] != protocol["folds"]["purge_embargo_hours"]:
        raise ValueError("the purge/embargo width drifted from the frozen protocol")
    if report["folds"]["random_k_fold"]:
        raise ValueError("random K-fold is forbidden for overlapping labels")

    accounting = report["labels"]
    total = accounting["admissible_labels"] + accounting["excluded_total"]
    if total != accounting["grid_decision_instants"]:
        raise ValueError("the label accounting does not close")
    if sum(accounting["exclusions"].values()) != accounting["excluded_total"]:
        raise ValueError("the typed exclusions do not sum to the excluded total")
    directions = accounting["direction_counts"]
    if sum(directions.values()) != accounting["admissible_labels"]:
        raise ValueError("the direction counts do not cover the admissible labels")

    assigned = report["folds"]["eligible_decision_timestamps"]
    unassigned = sum(report["folds"]["admissible_not_assigned"].values())
    if assigned + unassigned != accounting["admissible_labels"]:
        raise ValueError("the fold assignment does not cover the admissible labels")

    names = set(report["baselines"])
    if names != set(BASELINE_NAMES):
        raise ValueError("the report does not carry exactly the four required baselines")
    for name, record in report["baselines"].items():
        declares = record["declares"]
        if declares != DECLARATIONS[name]:
            raise ValueError(f"{name}: declared quantities drifted from the contract")
        pooled = record["pooled"]
        if declares["probability"]:
            if pooled["brier_score"] is None or pooled["reliability_table"] is None:
                raise ValueError(f"{name}: a probabilistic baseline lost its calibration")
        elif pooled["brier_score"] is not None or pooled["reliability_table"] is not None:
            raise ValueError(f"{name}: a deterministic baseline was given a Brier score")
        if not declares["direction"] and pooled["win_rate"] is not None:
            raise ValueError(f"{name}: a magnitude-only baseline was given a win rate")
        if declares["direction"] and pooled["eligible_decision_timestamps"] != assigned:
            raise ValueError(f"{name}: scored on a different eligible universe")

    if report["boundaries"]["model_fits"] or report["boundaries"]["sealed_queries"]:
        raise ValueError("the baseline report claims a model fit or a sealed query")

    if data_available:
        recomputed = report_bytes(build_report(root))
        committed = (root / REPORT_PATH).read_bytes().replace(b"\r\n", b"\n")
        if recomputed != committed:
            raise ValueError("the committed baseline report is not what the code recomputes")
        findings["data_replayed"] = True
    return findings


__all__ = [
    "REPORT_PATH",
    "build_report",
    "load_report",
    "report_bytes",
    "validate_report",
]
