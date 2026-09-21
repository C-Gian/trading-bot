"""The frozen Generation V2 scorer: selective `LONG` / `NO_TRADE` with an enrichment control.

`docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V2.md` replaces the Generation V1 question
"was the declared direction right on every hour" with "when the model chose to act, did it
act on a genuinely better-than-ambient set of hours". This module implements that scorer and
nothing else. It fits no model, reads no market data, and produces no candidate result.

Three ideas do the work.

**Selection is an action, not an abstention.** A candidate emits a calibrated `p_up` at every
feature-valid eligible timestamp. `LONG` iff `p_up >= 0.60`, otherwise `NO_TRADE`. The
threshold is a frozen product/scientific choice made before any Generation V2 candidate ran
and may never be tuned on development results.

**A selective win rate means nothing without the ambient rate.** The primary control,
`FULL_FOLD_UP_RATE`, is the UP frequency over every directionally scorable eligible timestamp
in the same fold. It never sees the candidate's action selection, so a candidate that simply
acts inside an up-trending fold shows no enrichment. Evaluation-fold truth enters this control
for scoring only; it is never visible to fitting, calibration or thresholding.

**A tiny sample is not a result.** Coverage and count floors precede the directional
conditions, so a cosmetically perfect win rate over a handful of cherry-picked hours fails
before its win rate is ever considered.

Overlapping 24h labels at a 1h cadence make independence false by construction, so the
enrichment interval is a fold-stratified moving-block bootstrap that recomputes *both* the
selected LONG win rate and the same-fold full-universe UP rate on every resample.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import DOWN, NEUTRAL, UP
from .evaluation import RELIABILITY_BIN_EDGES, reliability_table
from .labels import HOUR_SECONDS
from .paired_inference import block_sums

GENERATION = "PREDICTIVE_RESEARCH_GENERATION_V2"
EVALUATION_CONTRACT = "docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V2.md"
CONTRACT_AMENDMENT = "B1"

LONG = "LONG"
NO_TRADE = "NO_TRADE"
ACTIONS = (LONG, NO_TRADE)

# Frozen before any Generation V2 candidate exists. Never tuned on development results.
ACTION_THRESHOLD = 0.60

PRIMARY_METRIC = "SELECTIVE_LONG_WIN_RATE"
PRIMARY_CONTROL = "FULL_FOLD_UP_RATE"
SECONDARY_REFERENCES = (
    "TRAINING_UP_BASE_RATE",
    "ALWAYS_UP",
    "PREVIOUS_24H_SIGN_PERSISTENCE",
)

# Advancement thresholds, frozen in PREDICTIVE-GENERATION-V2-SELECTIVE-LONG-REBASELINE-V1.
MINIMUM_POOLED_ACTION_COVERAGE = 0.02
MINIMUM_FOLD_ACTION_COVERAGE = 0.005
MINIMUM_POOLED_ACTIONABLE_LONGS = 500
MINIMUM_FOLD_ACTIONABLE_LONGS = 30
MINIMUM_POOLED_SELECTIVE_WIN_RATE = 0.60
MINIMUM_POOLED_ENRICHMENT = 0.05
MAXIMUM_ACTION_CALIBRATION_GAP = 0.05

# Dependence-aware inference, frozen. The seed is declared per family before execution.
SELECTIVE_METHOD = "FOLD_STRATIFIED_MOVING_BLOCK_BOOTSTRAP_PAIRED_ENRICHMENT"
SELECTIVE_BLOCK_LENGTH_HOURS = 48
SELECTIVE_REPLICATES = 10_000
SELECTIVE_FAMILYWISE_ALPHA = 0.05
REPLICATE_CHUNK = 500
# A replicate that draws no actionable LONG has no selective win rate to report. It is
# discarded and counted rather than imputed; too many of them fail the interval closed.
MAXIMUM_DISCARDED_REPLICATE_SHARE = 0.01
UNSTABLE_SUPPORT = "UNSTABLE_RESAMPLE_SUPPORT"

GATE_NAMES = (
    "POOLED_ACTION_COVERAGE_AT_LEAST_0_02",
    "EVERY_FOLD_ACTION_COVERAGE_AT_LEAST_0_005",
    "POOLED_ACTIONABLE_LONGS_AT_LEAST_500",
    "EVERY_FOLD_ACTIONABLE_LONGS_AT_LEAST_30",
    "POOLED_SELECTIVE_LONG_WIN_RATE_AT_LEAST_0_60",
    "POOLED_ENRICHMENT_OVER_FULL_FOLD_UP_RATE_AT_LEAST_0_05",
    "ENRICHMENT_INTERVAL_LOWER_BOUND_ABOVE_ZERO",
    "AT_LEAST_TWO_THIRDS_OF_FOLDS_NON_NEGATIVE_ENRICHMENT",
    "FULL_PROBABILITY_BRIER_AT_MOST_MATCHED_TRAINING_UP_BASE_RATE_BRIER",
    "ACTION_CALIBRATION_GAP_AT_MOST_0_05",
)

MAGNITUDE_STATUS = "DEFERRED_UNTIL_FIRST_DIRECTIONAL_ADMISSION"


class SelectiveScoringError(RuntimeError):
    """The Generation V2 scorer was asked for something the frozen contract does not allow."""


@dataclass(frozen=True)
class SelectiveRecord:
    """One eligible decision instant, as a Generation V2 candidate leaves it.

    `truth` is the realized direction of the frozen 24h terminal label. `p_up` is the
    calibrated probability that `r_24h > 0`; it is `None` exactly when the candidate's
    feature vector was unavailable at that instant, which makes the row feature-invalid.
    A feature-invalid row is excluded from every rate and counted, never imputed.
    """

    open_time: int
    truth: str
    p_up: float | None = None

    def __post_init__(self) -> None:
        if self.truth not in {UP, DOWN, NEUTRAL}:
            raise SelectiveScoringError(f"unknown truth direction: {self.truth}")
        if self.p_up is not None and not 0.0 <= self.p_up <= 1.0:
            raise SelectiveScoringError("a calibrated probability must lie in [0, 1]")

    @property
    def feature_valid(self) -> bool:
        return self.p_up is not None

    @property
    def scorable(self) -> bool:
        """Directionally scorable: the realized truth is UP or DOWN."""
        return self.truth in {UP, DOWN}

    @property
    def action(self) -> str | None:
        return None if self.p_up is None else action_for(self.p_up)


@dataclass(frozen=True)
class SelectiveFold:
    """One evaluation fold's records laid on the hourly timeline its eligible instants span."""

    name: str
    first_open_time: int
    last_open_time: int
    records: tuple[SelectiveRecord, ...]

    @property
    def span_hours(self) -> int:
        return (self.last_open_time - self.first_open_time) // HOUR_SECONDS + 1


def action_for(p_up: float) -> str:
    """The frozen action policy. Exactly 0.60 acts LONG; Generation V2 never shorts."""
    if not 0.0 <= p_up <= 1.0:
        raise SelectiveScoringError("a calibrated probability must lie in [0, 1]")
    return LONG if p_up >= ACTION_THRESHOLD else NO_TRADE


def build_selective_fold(
    name: str, eligible_open_times: Sequence[int], records: Sequence[SelectiveRecord]
) -> SelectiveFold:
    if not eligible_open_times:
        raise SelectiveScoringError(f"{name}: the fold has no eligible decision instant")
    first, last = min(eligible_open_times), max(eligible_open_times)
    for record in records:
        if not first <= record.open_time <= last:
            raise SelectiveScoringError(f"{name}: a record sits outside the fold timeline")
        if (record.open_time - first) % HOUR_SECONDS:
            raise SelectiveScoringError(f"{name}: a record is not on the hourly grid")
    ordered = tuple(sorted(records, key=lambda item: item.open_time))
    if len({item.open_time for item in ordered}) != len(ordered):
        raise SelectiveScoringError(f"{name}: duplicate decision instants in one fold")
    return SelectiveFold(name=name, first_open_time=first, last_open_time=last, records=ordered)


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def fold_summary(fold: SelectiveFold, training_p_up: float) -> dict[str, Any]:
    """Every count and rate one fold contributes, with nothing imputed and nothing dropped.

    `training_p_up` is the fold's training-only UP base rate, used as the matched
    `TRAINING_UP_BASE_RATE` probability of UP for the full-probability Brier comparison.
    """
    if not 0.0 <= training_p_up <= 1.0:
        raise SelectiveScoringError("the training UP base rate must lie in [0, 1]")
    eligible = len(fold.records)
    feature_valid = [record for record in fold.records if record.feature_valid]
    long_actions = [record for record in feature_valid if record.action == LONG]
    actionable = [record for record in long_actions if record.scorable]
    wins = [record for record in actionable if record.truth == UP]
    scorable = [record for record in fold.records if record.scorable]
    scorable_up = [record for record in scorable if record.truth == UP]
    feature_valid_scorable = [record for record in feature_valid if record.scorable]
    feature_valid_up = [record for record in feature_valid_scorable if record.truth == UP]

    win_rate = _rate(len(wins), len(actionable))
    full_fold_up_rate = _rate(len(scorable_up), len(scorable))
    enrichment = (
        None if win_rate is None or full_fold_up_rate is None else win_rate - full_fold_up_rate
    )
    probabilities = [float(record.p_up) for record in feature_valid_scorable]  # type: ignore[arg-type]
    truths = [1.0 if record.truth == UP else 0.0 for record in feature_valid_scorable]
    candidate_brier = (
        None
        if not probabilities
        else sum((p - y) ** 2 for p, y in zip(probabilities, truths, strict=True))
        / len(probabilities)
    )
    control_brier = (
        None if not truths else sum((training_p_up - y) ** 2 for y in truths) / len(truths)
    )
    action_probabilities = [float(record.p_up) for record in actionable]  # type: ignore[arg-type]
    mean_action_probability = (
        sum(action_probabilities) / len(action_probabilities) if action_probabilities else None
    )
    return {
        "fold": fold.name,
        "timeline_hours": fold.span_hours,
        "eligible_decision_timestamps": eligible,
        "feature_valid_timestamps": len(feature_valid),
        "feature_invalid_timestamps": eligible - len(feature_valid),
        "long_actions": len(long_actions),
        "no_trade_actions": len(feature_valid) - len(long_actions),
        "long_actions_on_neutral_truth": len(long_actions) - len(actionable),
        "actionable_long_predictions": len(actionable),
        "selective_long_wins": len(wins),
        "action_coverage": _rate(len(long_actions), len(feature_valid)),
        "selective_long_win_rate": win_rate,
        "directionally_scorable_timestamps": len(scorable),
        "neutral_truths": eligible - len(scorable),
        "full_fold_up_rate": full_fold_up_rate,
        "feature_valid_fold_up_rate": _rate(len(feature_valid_up), len(feature_valid_scorable)),
        "enrichment": enrichment,
        "training_up_base_rate": training_p_up,
        "full_probability_brier": candidate_brier,
        "matched_training_up_base_rate_brier": control_brier,
        "mean_predicted_p_up_on_actions": mean_action_probability,
        "action_calibration_gap": (
            None
            if mean_action_probability is None or win_rate is None
            else abs(mean_action_probability - win_rate)
        ),
    }


def pooled_summary(
    folds: Sequence[SelectiveFold], training_p_up: Mapping[str, float]
) -> dict[str, Any]:
    """Pool the folds without ever averaging rates: counts add, rates are recomputed."""
    if not folds:
        raise SelectiveScoringError("the pooled summary needs at least one fold")
    missing = [fold.name for fold in folds if fold.name not in training_p_up]
    if missing:
        raise SelectiveScoringError(f"missing training UP base rate for folds: {missing}")
    by_fold = {fold.name: fold_summary(fold, training_p_up[fold.name]) for fold in folds}

    def total(key: str) -> int:
        return sum(int(record[key]) for record in by_fold.values())

    eligible = total("eligible_decision_timestamps")
    feature_valid = total("feature_valid_timestamps")
    long_actions = total("long_actions")
    actionable = total("actionable_long_predictions")
    wins = total("selective_long_wins")
    scorable = total("directionally_scorable_timestamps")
    # Counted, never reconstructed from a rate: pooling rates is exactly the error the
    # per-fold/pooled distinction exists to prevent.
    scorable_up = sum(1 for fold in folds for record in fold.records if record.truth == UP)
    win_rate = _rate(wins, actionable)
    full_fold_up_rate = _rate(scorable_up, scorable)
    enrichment = (
        None if win_rate is None or full_fold_up_rate is None else win_rate - full_fold_up_rate
    )

    probabilities: list[float] = []
    truths: list[float] = []
    control_truths: list[tuple[float, float]] = []
    action_probabilities: list[float] = []
    action_correct: list[bool] = []
    for fold in folds:
        rate = training_p_up[fold.name]
        for record in fold.records:
            if not record.feature_valid or not record.scorable:
                continue
            probabilities.append(float(record.p_up))  # type: ignore[arg-type]
            truths.append(1.0 if record.truth == UP else 0.0)
            control_truths.append((rate, 1.0 if record.truth == UP else 0.0))
            if record.action == LONG:
                action_probabilities.append(float(record.p_up))  # type: ignore[arg-type]
                action_correct.append(record.truth == UP)
    candidate_brier = (
        None
        if not probabilities
        else sum((p - y) ** 2 for p, y in zip(probabilities, truths, strict=True))
        / len(probabilities)
    )
    control_brier = (
        None
        if not control_truths
        else sum((p - y) ** 2 for p, y in control_truths) / len(control_truths)
    )
    mean_action_probability = (
        sum(action_probabilities) / len(action_probabilities) if action_probabilities else None
    )
    return {
        "generation": GENERATION,
        "evaluation_contract": EVALUATION_CONTRACT,
        "primary_metric": PRIMARY_METRIC,
        "primary_control": PRIMARY_CONTROL,
        "action_threshold": ACTION_THRESHOLD,
        "included_folds": [fold.name for fold in folds],
        "included_fold_count": len(folds),
        "eligible_decision_timestamps": eligible,
        "feature_valid_timestamps": feature_valid,
        "feature_invalid_timestamps": eligible - feature_valid,
        "long_actions": long_actions,
        "no_trade_actions": feature_valid - long_actions,
        "long_actions_on_neutral_truth": long_actions - actionable,
        "actionable_long_predictions": actionable,
        "selective_long_wins": wins,
        "action_coverage": _rate(long_actions, feature_valid),
        "selective_long_win_rate": win_rate,
        "directionally_scorable_timestamps": scorable,
        "neutral_truths": eligible - scorable,
        "full_fold_up_rate": full_fold_up_rate,
        "enrichment": enrichment,
        "full_probability_brier": candidate_brier,
        "matched_training_up_base_rate_brier": control_brier,
        "mean_predicted_p_up_on_actions": mean_action_probability,
        "action_calibration_gap": (
            None
            if mean_action_probability is None or win_rate is None
            else abs(mean_action_probability - win_rate)
        ),
        "action_reliability_table": reliability_table(action_probabilities, action_correct),
        "reliability_bin_edges": list(RELIABILITY_BIN_EDGES),
        "magnitude_declared": False,
        "magnitude_status": MAGNITUDE_STATUS,
        "by_fold": by_fold,
    }


def _slot_arrays(fold: SelectiveFold) -> tuple[Any, Any, Any, Any]:
    """Hour-slot indicators: actionable LONGs, their wins, scorable rows and their UPs."""
    import numpy as np

    span = fold.span_hours
    actionable = np.zeros(span, dtype=np.float64)
    wins = np.zeros(span, dtype=np.float64)
    scorable = np.zeros(span, dtype=np.float64)
    scorable_up = np.zeros(span, dtype=np.float64)
    for record in fold.records:
        slot = (record.open_time - fold.first_open_time) // HOUR_SECONDS
        if record.scorable:
            scorable[slot] = 1.0
            if record.truth == UP:
                scorable_up[slot] = 1.0
            if record.action == LONG:
                actionable[slot] = 1.0
                if record.truth == UP:
                    wins[slot] = 1.0
    return actionable, wins, scorable, scorable_up


def enrichment_interval(
    folds: Sequence[SelectiveFold],
    *,
    seed: int,
    alpha: float = SELECTIVE_FAMILYWISE_ALPHA,
    block_length: int = SELECTIVE_BLOCK_LENGTH_HOURS,
    replicates: int = SELECTIVE_REPLICATES,
    chunk: int = REPLICATE_CHUNK,
) -> dict[str, Any]:
    """Central `1 - alpha` percentile interval for the pooled enrichment.

    Each replicate resamples whole hourly blocks inside every fold independently, never
    across a fold boundary, and recomputes **both** the selected LONG win rate and the
    same-fold full-universe UP rate on that resample. An abstention or a canonical gap keeps
    its hour slot and simply contributes no record, so nothing is pulled into adjacency.
    """
    import numpy as np

    if not folds:
        raise SelectiveScoringError("the enrichment interval needs at least one fold")
    if replicates <= 0 or chunk <= 0:
        raise SelectiveScoringError("the replicate budget must be strictly positive")
    if not 0.0 < alpha < 1.0:
        raise SelectiveScoringError("alpha must lie strictly inside (0, 1)")

    actionable_totals = np.zeros(replicates, dtype=np.float64)
    win_totals = np.zeros(replicates, dtype=np.float64)
    scorable_totals = np.zeros(replicates, dtype=np.float64)
    up_totals = np.zeros(replicates, dtype=np.float64)
    generator = np.random.default_rng(seed)
    geometry: list[dict[str, int]] = []

    for fold in folds:
        actionable, wins, scorable, scorable_up = _slot_arrays(fold)
        full_a, partial_a, draws, block = block_sums(actionable, block_length)
        full_w, partial_w, _, _ = block_sums(wins, block_length)
        full_s, partial_s, _, _ = block_sums(scorable, block_length)
        full_u, partial_u, _, _ = block_sums(scorable_up, block_length)
        starts_available = int(full_a.shape[0])
        geometry.append(
            {
                "timeline_hours": fold.span_hours,
                "effective_block_hours": block,
                "blocks_per_replicate": draws,
                "block_start_positions": starts_available,
                "actionable_long_predictions": int(actionable.sum()),
                "directionally_scorable_timestamps": int(scorable.sum()),
            }
        )
        done = 0
        while done < replicates:
            size = min(chunk, replicates - done)
            starts = generator.integers(0, starts_available, size=(size, draws))
            head, tail = starts[:, : draws - 1], starts[:, draws - 1]
            actionable_totals[done : done + size] += full_a[head].sum(axis=1) + partial_a[tail]
            win_totals[done : done + size] += full_w[head].sum(axis=1) + partial_w[tail]
            scorable_totals[done : done + size] += full_s[head].sum(axis=1) + partial_s[tail]
            up_totals[done : done + size] += full_u[head].sum(axis=1) + partial_u[tail]
            done += size

    if not np.all(scorable_totals > 0):
        raise SelectiveScoringError("a replicate resampled no directionally scorable row at all")
    retained = actionable_totals > 0
    discarded = int(replicates - int(retained.sum()))
    discarded_share = discarded / replicates
    if not retained.any():
        raise SelectiveScoringError("no replicate drew a single actionable LONG")
    selected = win_totals[retained] / actionable_totals[retained]
    ambient = up_totals[retained] / scorable_totals[retained]
    deltas = selected - ambient
    lower, upper = np.quantile(deltas, [alpha / 2, 1 - alpha / 2])
    stable = discarded_share <= MAXIMUM_DISCARDED_REPLICATE_SHARE
    return {
        "method": SELECTIVE_METHOD,
        "block_length_hours": block_length,
        "replicates": replicates,
        "retained_replicates": int(retained.sum()),
        "discarded_replicates_without_an_actionable_long": discarded,
        "discarded_replicate_share": discarded_share,
        "maximum_discarded_replicate_share": MAXIMUM_DISCARDED_REPLICATE_SHARE,
        "resample_support": "STABLE" if stable else UNSTABLE_SUPPORT,
        "seed": seed,
        "alpha": alpha,
        "interval_mass": 1.0 - alpha,
        "interval": [float(lower), float(upper)],
        "interval_lower_bound_above_zero": bool(stable and lower > 0.0),
        "blocks_cross_fold_boundaries": False,
        "abstentions_compressed_into_adjacency": False,
        "recomputes_control_on_every_replicate": True,
        "fold_geometry": {fold.name: record for fold, record in zip(folds, geometry, strict=True)},
    }


def required_non_negative_folds(fold_count: int) -> int:
    return math.ceil(2 / 3 * fold_count)


def advancement_gate(summary: Mapping[str, Any], interval: Mapping[str, Any]) -> dict[str, Any]:
    """The ten predeclared conditions. All must hold; no secondary metric ever rescues one.

    Conditions 1-4 refuse a cosmetically high win rate built from a handful of actions.
    Conditions 5-8 test directional enrichment over the ambient fold environment. Conditions
    9-10 require the displayed probabilities to mean what they claim.
    """
    by_fold = summary["by_fold"]
    fold_coverage = {name: (record["action_coverage"] or 0.0) for name, record in by_fold.items()}
    fold_actionable = {
        name: int(record["actionable_long_predictions"]) for name, record in by_fold.items()
    }
    fold_enrichment = {name: record["enrichment"] for name, record in by_fold.items()}
    non_negative = sum(
        1 for value in fold_enrichment.values() if value is not None and value >= 0.0
    )
    required = required_non_negative_folds(len(by_fold))

    coverage = summary["action_coverage"]
    win_rate = summary["selective_long_win_rate"]
    enrichment = summary["enrichment"]
    candidate_brier = summary["full_probability_brier"]
    control_brier = summary["matched_training_up_base_rate_brier"]
    gap = summary["action_calibration_gap"]

    conditions: dict[str, dict[str, Any]] = {
        GATE_NAMES[0]: {
            "threshold": MINIMUM_POOLED_ACTION_COVERAGE,
            "observed": coverage,
            "passed": coverage is not None and coverage >= MINIMUM_POOLED_ACTION_COVERAGE,
        },
        GATE_NAMES[1]: {
            "threshold": MINIMUM_FOLD_ACTION_COVERAGE,
            "observed": min(fold_coverage.values()) if fold_coverage else None,
            "passed": bool(fold_coverage)
            and all(value >= MINIMUM_FOLD_ACTION_COVERAGE for value in fold_coverage.values()),
        },
        GATE_NAMES[2]: {
            "threshold": MINIMUM_POOLED_ACTIONABLE_LONGS,
            "observed": int(summary["actionable_long_predictions"]),
            "passed": int(summary["actionable_long_predictions"])
            >= MINIMUM_POOLED_ACTIONABLE_LONGS,
        },
        GATE_NAMES[3]: {
            "threshold": MINIMUM_FOLD_ACTIONABLE_LONGS,
            "observed": min(fold_actionable.values()) if fold_actionable else None,
            "passed": bool(fold_actionable)
            and all(value >= MINIMUM_FOLD_ACTIONABLE_LONGS for value in fold_actionable.values()),
        },
        GATE_NAMES[4]: {
            "threshold": MINIMUM_POOLED_SELECTIVE_WIN_RATE,
            "observed": win_rate,
            "passed": win_rate is not None and win_rate >= MINIMUM_POOLED_SELECTIVE_WIN_RATE,
        },
        GATE_NAMES[5]: {
            "threshold": MINIMUM_POOLED_ENRICHMENT,
            "observed": enrichment,
            "passed": enrichment is not None and enrichment >= MINIMUM_POOLED_ENRICHMENT,
        },
        GATE_NAMES[6]: {
            "threshold": 0.0,
            "observed": float(interval["interval"][0]),
            "passed": bool(interval["interval_lower_bound_above_zero"]),
        },
        GATE_NAMES[7]: {
            "threshold": required,
            "observed": non_negative,
            "passed": non_negative >= required,
        },
        GATE_NAMES[8]: {
            "threshold": control_brier,
            "observed": candidate_brier,
            "passed": candidate_brier is not None
            and control_brier is not None
            and candidate_brier <= control_brier,
        },
        GATE_NAMES[9]: {
            "threshold": MAXIMUM_ACTION_CALIBRATION_GAP,
            "observed": gap,
            "passed": gap is not None and gap <= MAXIMUM_ACTION_CALIBRATION_GAP,
        },
    }
    failed = [name for name, record in conditions.items() if not record["passed"]]
    return {
        "all_must_hold": True,
        "conditions": conditions,
        "failed_conditions": failed,
        "advances": not failed,
        "secondary_metric_used_to_rescue": False,
        "required_non_negative_folds": required,
        "non_negative_enrichment_folds": non_negative,
        "included_fold_count": len(by_fold),
        "fold_action_coverage": fold_coverage,
        "fold_actionable_long_predictions": fold_actionable,
        "fold_enrichment": fold_enrichment,
    }


def frozen_semantics() -> dict[str, Any]:
    """The machine-readable freeze, so a record and the code cannot silently disagree."""
    return {
        "generation": GENERATION,
        "evaluation_contract": EVALUATION_CONTRACT,
        "evaluation_contract_amendment": CONTRACT_AMENDMENT,
        "target": "BTCUSDT_SPOT_24H_TERMINAL_DIRECTION",
        "prediction_target": "r_24h = log(close[T+24h] / close[T])",
        "decision_cadence": "1h",
        "primary_horizon": "24h",
        "horizon_searched": False,
        "actions": list(ACTIONS),
        "short_authorized": False,
        "action_rule": "LONG_IFF_CALIBRATED_P_UP_AT_LEAST_0_60_ELSE_NO_TRADE",
        "action_threshold": ACTION_THRESHOLD,
        "action_threshold_tunable_on_development": False,
        "probability_required_for_participation": True,
        "primary_metric": PRIMARY_METRIC,
        "primary_metric_definition": "UP_TRUTHS_OVER_ACTIONABLE_LONG_PREDICTIONS",
        "primary_control": PRIMARY_CONTROL,
        "primary_control_definition": (
            "UP_FREQUENCY_OVER_EVERY_DIRECTIONALLY_SCORABLE_ELIGIBLE_TIMESTAMP_IN_THE_FOLD"
        ),
        "primary_control_uses_candidate_action_selection": False,
        "primary_control_visible_to_fitting_or_calibration": False,
        "primary_effect": "SELECTIVE_LONG_WIN_RATE_MINUS_FULL_FOLD_UP_RATE",
        "secondary_references": list(SECONDARY_REFERENCES),
        "previous_24h_sign_persistence_inverted": False,
        "neutral_truth_rule": "COUNTED_EXPLICITLY_EXCLUDED_FROM_WINS_AND_FROM_DENOMINATORS",
        "feature_invalid_row_rule": "EXCLUDED_FROM_EVERY_RATE_AND_COUNTED_NEVER_IMPUTED",
        "thresholds": {
            GATE_NAMES[0]: MINIMUM_POOLED_ACTION_COVERAGE,
            GATE_NAMES[1]: MINIMUM_FOLD_ACTION_COVERAGE,
            GATE_NAMES[2]: MINIMUM_POOLED_ACTIONABLE_LONGS,
            GATE_NAMES[3]: MINIMUM_FOLD_ACTIONABLE_LONGS,
            GATE_NAMES[4]: MINIMUM_POOLED_SELECTIVE_WIN_RATE,
            GATE_NAMES[5]: MINIMUM_POOLED_ENRICHMENT,
            GATE_NAMES[6]: 0.0,
            GATE_NAMES[7]: "CEIL_TWO_THIRDS_OF_INCLUDED_FOLDS",
            GATE_NAMES[8]: "MATCHED_TRAINING_UP_BASE_RATE_BRIER",
            GATE_NAMES[9]: MAXIMUM_ACTION_CALIBRATION_GAP,
        },
        "gate_names": list(GATE_NAMES),
        "all_conditions_must_hold": True,
        "thresholds_weakenable_after_a_result": False,
        "inference": {
            "method": SELECTIVE_METHOD,
            "block_length_hours": SELECTIVE_BLOCK_LENGTH_HOURS,
            "replicates": SELECTIVE_REPLICATES,
            "seed": "DECLARED_PER_FAMILY_BEFORE_EXECUTION",
            "familywise_alpha": SELECTIVE_FAMILYWISE_ALPHA,
            "multiplicity_correction": "BONFERRONI_OVER_THE_DECLARED_FAMILY_SIZE",
            "replicate_chunk": REPLICATE_CHUNK,
            "recomputes_control_on_every_replicate": True,
            "blocks_cross_fold_boundaries": False,
            "empty_action_replicate_rule": "DISCARDED_AND_COUNTED_NEVER_IMPUTED",
            "maximum_discarded_replicate_share": MAXIMUM_DISCARDED_REPLICATE_SHARE,
            "unstable_support_classification": UNSTABLE_SUPPORT,
        },
        "reliability_bin_edges": list(RELIABILITY_BIN_EDGES),
        "reliability_bins_inherited_from_v1": True,
        "magnitude_declared": False,
        "magnitude_status": MAGNITUDE_STATUS,
        "real_money": False,
        "sealed_queries": 0,
    }


__all__ = [
    "ACTIONS",
    "ACTION_THRESHOLD",
    "CONTRACT_AMENDMENT",
    "EVALUATION_CONTRACT",
    "GATE_NAMES",
    "GENERATION",
    "LONG",
    "MAGNITUDE_STATUS",
    "MAXIMUM_ACTION_CALIBRATION_GAP",
    "MAXIMUM_DISCARDED_REPLICATE_SHARE",
    "MINIMUM_FOLD_ACTIONABLE_LONGS",
    "MINIMUM_FOLD_ACTION_COVERAGE",
    "MINIMUM_POOLED_ACTIONABLE_LONGS",
    "MINIMUM_POOLED_ACTION_COVERAGE",
    "MINIMUM_POOLED_ENRICHMENT",
    "MINIMUM_POOLED_SELECTIVE_WIN_RATE",
    "NO_TRADE",
    "PRIMARY_CONTROL",
    "PRIMARY_METRIC",
    "REPLICATE_CHUNK",
    "SECONDARY_REFERENCES",
    "SELECTIVE_BLOCK_LENGTH_HOURS",
    "SELECTIVE_FAMILYWISE_ALPHA",
    "SELECTIVE_METHOD",
    "SELECTIVE_REPLICATES",
    "UNSTABLE_SUPPORT",
    "SelectiveFold",
    "SelectiveRecord",
    "SelectiveScoringError",
    "action_for",
    "advancement_gate",
    "build_selective_fold",
    "enrichment_interval",
    "fold_summary",
    "frozen_semantics",
    "pooled_summary",
    "required_non_negative_folds",
]
