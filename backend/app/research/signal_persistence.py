"""Design-only power analysis for ALIGNED_SIGNAL_PERSISTS_TO_120H_V1 (P1A).

This module prepares, but never executes, the future material hypothesis. It builds a
matched calendar-time placebo distribution by circularly shifting the frozen ALIGNED raw
signal sequence inside each fixed annual validation fold, and derives the prospective
minimum detectable effect and power at the frozen event-level MESI from that
distribution alone.

The true zero-shift ALIGNED 120h statistic is never computed here. Every aggregation
path runs through `placebo_pooled_mean_bps`, which rejects any displacement smaller than
the frozen minimum, zero included.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from typing import Any

from .evaluation_protocol import HOUR_US

DESIGN_ID = "ALIGNED_SIGNAL_PERSISTENCE_V1"
HYPOTHESIS_ID = "ALIGNED_SIGNAL_PERSISTS_TO_120H_V1"
GATE_ID = "P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-V1"
NULL_ID = "P1A-ALIGNED-SIGNAL-PERSISTENCE-NULL-DISTRIBUTION-V1"
STRATEGY_VERSION = "ALIGNED_PARTICIPATION_CONTINUATION_V1"
VARIANT = "ALIGNED"

PRIMARY_HORIZON_HOURS = 120
HORIZON_MINUTES = PRIMARY_HORIZON_HOURS * 60
MINUTE_US = 60_000_000
START_PRICE_CONVENTION = "GOVERNED_NEXT_1M_OPEN_AT_SIGNAL_INSTANT"
TERMINAL_PRICE_CONVENTION = "CLOSE_OF_THE_1M_BAR_OPENING_AT_SIGNAL_PLUS_7199_MINUTES"
PRIMARY_METRIC = "FORWARD_120H_BTCUSDT_PRICE_RETURN_BPS"

MATCHED_CONTROL_METHOD = "DETERMINISTIC_WITHIN_FOLD_CIRCULAR_CALENDAR_SHIFT_V1"
MINIMUM_SHIFT_HOURS = 168
CENTRAL_ESTIMATOR = "ARITHMETIC_MEAN_OF_PLACEBO_EVENT_MEAN_RETURNS"

FAMILY_ALPHA = 0.05
PROSPECTIVE_FAMILY_SIZE = 13
EFFECTIVE_ALPHA = FAMILY_ALPHA / PROSPECTIVE_FAMILY_SIZE
MULTIPLICITY_BASIS = (
    "HOLM_FIRST_RANK_FAMILYWISE_THRESHOLD_ALPHA_0.05/13_"
    "TWELVE_OBSERVED_MATERIAL_HYPOTHESES_PLUS_P1A"
)
MULTIPLICITY_WARNING = (
    "The documented material family is a lower bound; pre-repository exposure remains "
    "unquantified and is not converted into a numeric family size."
)
POWER_TARGET = 0.80

OWNER_ANNUAL_MESI_BPS = 500.0
REFERENCE_RESOLVED_TRADES = 125
REFERENCE_FOLDS = 6
MESI_BPS_PER_EVENT = 24.0
MESI_TRANSLATION = "500 bps per year / (125 resolved DEFAULT trades / 6 annual folds) = 24.0 bps"

MDE_REPORTING_TICK_BPS = Decimal("0.000001")
READY = "READY_FOR_PREREGISTRATION"
REDESIGN = "REDESIGN_REQUIRED"

FORBIDDEN_ARTIFACT_KEYS = frozenset(
    {
        "actual_aligned_mean_bps",
        "actual_excess_bps",
        "aligned_120h_mean_bps",
        "aligned_minus_placebo_bps",
        "observed_excess_bps",
        "p1a_classification",
        "p1a_effect_bps",
        "p1a_p_value",
        "unshifted_mean_bps",
        "zero_shift_mean_bps",
    }
)


class PrepModeViolation(ValueError):
    """A caller attempted an aggregation that could expose the P1A outcome."""


def _rounded(value: float) -> float:
    return round(value, 10)


@dataclass(frozen=True)
class FoldSignalSeries:
    """One fold's eligible decision grid, forward outcomes, and raw ALIGNED events.

    `decision_times_us` holds every hourly decision instant of the fold that carries a
    complete causal ALIGNED feature history and a complete contiguous 120h forward
    outcome. Positions index that sequence, so a circular shift of `d` positions always
    displaces an event by at least `d` hours of calendar time. Signal positions are raw:
    portfolio occupancy never removes one.
    """

    fold_id: str
    decision_times_us: tuple[int, ...]
    forward_bps: tuple[float, ...]
    signal_positions: tuple[int, ...]
    grid_span_hours: int
    feature_ineligible_clocks: int
    outcome_ineligible_clocks: int
    emitted_conditions_on_span: int

    def __post_init__(self) -> None:
        size = len(self.decision_times_us)
        if size < 2 * MINIMUM_SHIFT_HOURS + 1:
            raise ValueError("fold decision grid is too short for the frozen displacement rule")
        if len(self.forward_bps) != size:
            raise ValueError("forward outcome series must cover every decision instant")
        for previous, current in zip(
            self.decision_times_us, self.decision_times_us[1:], strict=False
        ):
            if current - previous < HOUR_US or current % HOUR_US or previous % HOUR_US:
                raise ValueError("decision instants must be strictly increasing hourly boundaries")
        if any(not math.isfinite(value) for value in self.forward_bps):
            raise ValueError("forward outcome series contains a non-finite return")
        positions = self.signal_positions
        if any(not 0 <= position < size for position in positions):
            raise ValueError("signal position is outside the eligible decision grid")
        if any(later <= earlier for earlier, later in zip(positions, positions[1:], strict=False)):
            raise ValueError("signal positions must be strictly increasing and unique")

    @property
    def grid_size(self) -> int:
        return len(self.decision_times_us)

    @property
    def signal_count(self) -> int:
        return len(self.signal_positions)


def circular_displacement(shift: int, grid_size: int) -> int:
    """Smallest number of grid positions separating a position from its shifted image."""
    if grid_size <= 0:
        raise ValueError("grid size must be positive")
    residue = shift % grid_size
    return min(residue, grid_size - residue)


def validate_prep_shift(shift: int, grid_size: int) -> None:
    """Reject zero shift and any displacement that could retain 120h alignment."""
    if isinstance(shift, bool) or not isinstance(shift, int):
        raise PrepModeViolation("shift must be an integer number of grid positions")
    displacement = circular_displacement(shift, grid_size)
    if displacement < MINIMUM_SHIFT_HOURS:
        raise PrepModeViolation(
            "prep mode forbids a displacement below "
            f"{MINIMUM_SHIFT_HOURS} positions; received {displacement}"
        )


def shifted_positions(series: FoldSignalSeries, shift: int) -> tuple[int, ...]:
    """Circularly shifted event positions, preserving count and cyclic order structure."""
    validate_prep_shift(shift, series.grid_size)
    return tuple((position + shift) % series.grid_size for position in series.signal_positions)


def placebo_event_returns(series: FoldSignalSeries, shift: int) -> tuple[float, ...]:
    return tuple(series.forward_bps[position] for position in shifted_positions(series, shift))


def placebo_pooled_mean_bps(folds: tuple[FoldSignalSeries, ...], shift: int) -> float:
    """The only aggregator in this module; it cannot be reached with a zero shift."""
    if not folds:
        raise ValueError("at least one fold is required")
    values: list[float] = []
    for series in folds:
        values.extend(placebo_event_returns(series, shift))
    if not values:
        raise ValueError("matched control requires at least one event")
    return math.fsum(values) / len(values)


def admissible_shifts(folds: tuple[FoldSignalSeries, ...]) -> tuple[int, ...]:
    """Every deterministic shift whose displacement clears the rule in all folds."""
    smallest = min(series.grid_size for series in folds)
    candidates = range(MINIMUM_SHIFT_HOURS, smallest - MINIMUM_SHIFT_HOURS + 1)
    return tuple(
        shift
        for shift in candidates
        if all(
            circular_displacement(shift, series.grid_size) >= MINIMUM_SHIFT_HOURS
            for series in folds
        )
    )


def build_null_distribution(folds: tuple[FoldSignalSeries, ...]) -> dict[str, Any]:
    """Enumerate the complete admissible placebo distribution, never shift zero."""
    shifts = admissible_shifts(folds)
    if not shifts or 0 in shifts:
        raise PrepModeViolation("admissible shift set is empty or contains zero")
    means = [_rounded(placebo_pooled_mean_bps(folds, shift)) for shift in shifts]
    return {
        "schema_version": 1,
        "artifact_id": NULL_ID,
        "design_id": DESIGN_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "matched_control_method": MATCHED_CONTROL_METHOD,
        "minimum_shift_hours": MINIMUM_SHIFT_HOURS,
        "primary_horizon_hours": PRIMARY_HORIZON_HOURS,
        "primary_metric": PRIMARY_METRIC,
        "shift_enumeration": "ALL_DETERMINISTIC_ADMISSIBLE_SHIFTS_NO_RANDOM_SEED",
        "raw_signal_count": sum(series.signal_count for series in folds),
        "folds": [
            {
                "fold_id": series.fold_id,
                "decision_grid_span_hours": series.grid_span_hours,
                "eligible_decision_instants": series.grid_size,
                "feature_ineligible_clocks": series.feature_ineligible_clocks,
                "outcome_ineligible_clocks": series.outcome_ineligible_clocks,
                "emitted_conditions_on_span": series.emitted_conditions_on_span,
                "raw_signal_count": series.signal_count,
            }
            for series in folds
        ],
        "placebo_shift_count": len(shifts),
        "shifts": list(shifts),
        "placebo_pooled_mean_bps": means,
        "zero_shift_present": False,
    }


def _ceiling_tick(value: float) -> float:
    """Smallest reporting tick strictly greater than `value`; deterministic everywhere."""
    steps = (Decimal(repr(value)) / MDE_REPORTING_TICK_BPS).to_integral_value(rounding=ROUND_FLOOR)
    return float((steps + 1) * MDE_REPORTING_TICK_BPS)


def empirical_power(required_displacements: list[float], effect_bps: float) -> float:
    """Fraction of admissible placebo draws that the injected effect pushes past the gate."""
    if not required_displacements:
        raise ValueError("power requires a non-empty null distribution")
    return sum(value < effect_bps for value in required_displacements) / len(required_displacements)


def evaluate_power_gate(null: dict[str, Any]) -> dict[str, Any]:
    """Derive the prospective critical value, power and MDE from placebo draws only."""
    if null.get("zero_shift_present"):
        raise PrepModeViolation("null distribution claims a zero-shift draw")
    shifts = [int(value) for value in null["shifts"]]
    means = [float(value) for value in null["placebo_pooled_mean_bps"]]
    if len(shifts) != len(means) or not means:
        raise ValueError("null distribution is malformed")
    if 0 in shifts:
        raise PrepModeViolation("zero shift entered the admissible set")
    if any(not math.isfinite(value) for value in means):
        raise ValueError("null distribution contains a non-finite placebo mean")
    count = len(means)

    center = _rounded(math.fsum(means) / count)
    minimum_attainable_p = 1.0 / (count + 1)
    resolution_sufficient = minimum_attainable_p <= EFFECTIVE_ALPHA
    rejection_budget = math.floor(EFFECTIVE_ALPHA * (count + 1)) - 1

    critical_mean: float | None = None
    critical_excess: float | None = None
    mde: float | None = None
    power_at_mesi: float | None = None
    power_at_mde: float | None = None
    if resolution_sufficient:
        critical_mean = sorted(means, reverse=True)[rejection_budget]
        required = sorted(critical_mean - value for value in means)
        mde = _ceiling_tick(required[math.ceil(POWER_TARGET * count) - 1])
        power_at_mesi = empirical_power(required, MESI_BPS_PER_EVENT)
        power_at_mde = empirical_power(required, mde)
        if power_at_mde < POWER_TARGET:
            raise ValueError("reported MDE failed its own power verification")
        critical_excess = _rounded(critical_mean - center)

    integrity = {
        "event_count_preserved_under_every_shift": True,
        "all_shifts_exceed_primary_horizon": all(shift >= MINIMUM_SHIFT_HOURS for shift in shifts)
        and MINIMUM_SHIFT_HOURS > PRIMARY_HORIZON_HOURS,
        "zero_shift_excluded": 0 not in shifts,
        "deterministic_shift_enumeration": shifts == list(range(shifts[0], shifts[-1] + 1)),
        "randomization_resolution_sufficient": resolution_sufficient,
    }
    integrity_pass = all(integrity.values())

    gate_status = (
        READY
        if integrity_pass and power_at_mesi is not None and power_at_mesi >= POWER_TARGET
        else REDESIGN
    )

    return {
        "schema_version": 1,
        "artifact_id": GATE_ID,
        "design_id": DESIGN_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis_status": "DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED",
        "strategy_version": STRATEGY_VERSION,
        "variant": VARIANT,
        "aligned_semantics_changed": False,
        "primary_design": {
            "primary_horizon_hours": PRIMARY_HORIZON_HOURS,
            "horizon_minutes": HORIZON_MINUTES,
            "primary_metric": PRIMARY_METRIC,
            "start_price_convention": START_PRICE_CONVENTION,
            "terminal_price_convention": TERMINAL_PRICE_CONVENTION,
            "stop_loss": False,
            "profit_target": False,
            "trailing_logic": False,
            "one_position_at_a_time": False,
            "r_denominator": False,
            "cost_treatment": "IDENTICAL_FOR_SIGNAL_AND_PLACEBO_DIFFERENTIAL_IN_EXCESS_BPS",
            "retained_reference_horizon_hours": 24,
            "horizon_search_performed": False,
        },
        "signal": {
            "raw_signal_count": null["raw_signal_count"],
            "signals_per_fold": {
                fold["fold_id"]: fold["raw_signal_count"] for fold in null["folds"]
            },
            "emitted_conditions_per_fold": {
                fold["fold_id"]: fold["emitted_conditions_on_span"] for fold in null["folds"]
            },
            "eligible_decision_instants_per_fold": {
                fold["fold_id"]: fold["eligible_decision_instants"] for fold in null["folds"]
            },
            "reference_signals_per_year": _rounded(REFERENCE_RESOLVED_TRADES / REFERENCE_FOLDS),
            "observed_signals_per_year": _rounded(null["raw_signal_count"] / REFERENCE_FOLDS),
            "occupancy_suppression_applied": False,
        },
        "matched_control": {
            "method": MATCHED_CONTROL_METHOD,
            "central_estimator": CENTRAL_ESTIMATOR,
            "minimum_shift_hours": MINIMUM_SHIFT_HOURS,
            "placebo_shift_count": count,
            "smallest_shift": shifts[0],
            "largest_shift": shifts[-1],
            "placebo_center_bps": center,
            "placebo_minimum_bps": min(means),
            "placebo_maximum_bps": max(means),
            "preserves_event_count": True,
            "preserves_within_fold_clustering": True,
            "preserves_annual_exposure": True,
            "preserves_horizon": True,
            "preserves_sparsity": True,
        },
        "economic_threshold": {
            "owner_annual_net_excess_mesi_bps": OWNER_ANNUAL_MESI_BPS,
            "reference_resolved_trades": REFERENCE_RESOLVED_TRADES,
            "reference_folds": REFERENCE_FOLDS,
            "mesi_translation": MESI_TRANSLATION,
            "P1A_INFORMATION_MESI_BPS": MESI_BPS_PER_EVENT,
            "interpretation": (
                "24 bps per event is a NECESSARY informational lower bound at roughly the "
                "historical ALIGNED product cadence. It is not sufficient evidence that a "
                "120h execution strategy would earn five percentage points per year; "
                "execution feasibility under longer holding belongs to P1B."
            ),
        },
        "multiplicity": {
            "alpha_family": FAMILY_ALPHA,
            "prospective_family_size": PROSPECTIVE_FAMILY_SIZE,
            "effective_alpha": EFFECTIVE_ALPHA,
            "basis": MULTIPLICITY_BASIS,
            "observed_material_hypotheses": PROSPECTIVE_FAMILY_SIZE - 1,
            "documented_family_is_lower_bound": True,
            "warning": MULTIPLICITY_WARNING,
        },
        "power": {
            "power_target": POWER_TARGET,
            "MESI_bps_per_event": MESI_BPS_PER_EVENT,
            "critical_placebo_pooled_mean_bps": critical_mean,
            "critical_excess_bps_per_event": critical_excess,
            "rejection_budget_draws": rejection_budget,
            "empirical_MDE_bps_per_event": mde,
            "power_at_MESI": power_at_mesi,
            "power_at_MDE": power_at_mde,
            "minimum_attainable_randomization_p": minimum_attainable_p,
            "randomization_resolution_sufficient": resolution_sufficient,
            "search_rules": {
                "critical_value": (
                    "reject when the statistic strictly exceeds the (K+1)-th largest placebo "
                    "pooled mean, with K = floor(effective_alpha * (M + 1)) - 1"
                ),
                "power": (
                    "fraction of admissible placebo draws whose required displacement is "
                    "strictly below the injected event-level effect"
                ),
                "mde": (
                    "smallest multiple of 1e-6 bps strictly greater than the "
                    "ceil(0.80 * M)-th smallest required displacement"
                ),
            },
        },
        "integrity": integrity,
        "integrity_pass": integrity_pass,
        "leakage_guard": {
            "zero_shift_statistic_computed": False,
            "actual_aligned_120h_mean_present": False,
            "actual_minus_placebo_effect_present": False,
            "p1a_p_value_present": False,
            "p1a_performance_classified": False,
            "prep_mode_rejects_zero_shift": True,
            "new_material_experiment_consumed": False,
            "sealed_data_inspected": False,
            "post_cutoff_data_used": False,
        },
        "power_gate_status": gate_status,
        "preregistration_authorized": False,
        "runner_candidate_registered": False,
        "next_action": "RESEARCH_DIRECTOR_REVIEW",
    }


def assert_no_result_leakage(value: Any, pointer: str = "") -> None:
    """Fail closed if any artifact key could carry the unobserved P1A outcome."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_ARTIFACT_KEYS:
                raise PrepModeViolation(f"forbidden P1A outcome key at {pointer}/{key}")
            assert_no_result_leakage(child, f"{pointer}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_result_leakage(child, f"{pointer}/{index}")


def _percent(value: float | None) -> str:
    return "UNAVAILABLE" if value is None else f"{value * 100:.4f}%"


def render_power_gate_markdown(gate: dict[str, Any]) -> str:
    signal = gate["signal"]
    control = gate["matched_control"]
    power = gate["power"]
    economics = gate["economic_threshold"]
    multiplicity = gate["multiplicity"]
    design = gate["primary_design"]
    folds = "; ".join(f"{fold_id} {count}" for fold_id, count in signal["signals_per_fold"].items())
    mde = power["empirical_MDE_bps_per_event"]
    lines = [
        f"# {gate['artifact_id']}",
        "",
        f"Design: `{gate['design_id']}`. Future hypothesis: `{gate['hypothesis_id']}`.",
        "",
        "Prospective design and power analysis only. The unshifted 120h ALIGNED result was",
        "not computed, no material experiment was executed, and P1A is not preregistered.",
        "",
        "## Signal",
        "",
        f"- raw ALIGNED signal events: {signal['raw_signal_count']}",
        f"- per fold: {folds}",
        f"- frozen reference cadence: {signal['reference_signals_per_year']} events/year",
        f"- observed prep cadence: {signal['observed_signals_per_year']} events/year",
        "- portfolio occupancy suppression: not applied (information study)",
        f"- ALIGNED semantics changed: {gate['aligned_semantics_changed']}",
        "",
        "## Primary design",
        "",
        f"- horizon: {design['primary_horizon_hours']}h ({design['horizon_minutes']} minutes)",
        f"- metric: {design['primary_metric']}",
        f"- start price: {design['start_price_convention']}",
        f"- terminal price: {design['terminal_price_convention']}",
        (
            f"- stop / target / trailing: {design['stop_loss']}"
            f" / {design['profit_target']} / {design['trailing_logic']}"
        ),
        f"- one position at a time: {design['one_position_at_a_time']}",
        f"- R denominator: {design['r_denominator']}",
        f"- costs: {design['cost_treatment']}",
        "",
        "## Matched timing control",
        "",
        f"- method: {control['method']}",
        f"- central estimator: {control['central_estimator']}",
        f"- minimum displacement: {control['minimum_shift_hours']}h",
        (
            f"- admissible shifts: {control['placebo_shift_count']}"
            f" ({control['smallest_shift']}..{control['largest_shift']})"
        ),
        f"- placebo centre: {control['placebo_center_bps']} bps/event",
        (
            f"- placebo range: {control['placebo_minimum_bps']}"
            f" .. {control['placebo_maximum_bps']} bps/event"
        ),
        "- event count, clustering, exposure, horizon and sparsity preserved",
        "",
        "## Economic threshold",
        "",
        f"- Owner annual MESI: {economics['owner_annual_net_excess_mesi_bps']} bps/year",
        f"- translation: {economics['mesi_translation']}",
        f"- P1A event-level MESI: {economics['P1A_INFORMATION_MESI_BPS']} bps/event",
        f"- {economics['interpretation']}",
        "",
        "## Power",
        "",
        f"- prospective family size: {multiplicity['prospective_family_size']}",
        f"- effective alpha: {multiplicity['effective_alpha']}",
        f"- basis: {multiplicity['basis']}",
        f"- target power: {power['power_target']}",
        f"- empirical MDE: {mde if mde is not None else 'UNAVAILABLE'} bps/event",
        (
            f"- power at MESI ({economics['P1A_INFORMATION_MESI_BPS']} bps):"
            f" {_percent(power['power_at_MESI'])}"
        ),
        f"- minimum attainable randomization p: {power['minimum_attainable_randomization_p']}",
        f"- randomization resolution sufficient: {power['randomization_resolution_sufficient']}",
        "",
        f"## POWER_GATE_STATUS: {gate['power_gate_status']}",
        "",
        f"- integrity tests pass: {gate['integrity_pass']}",
        f"- preregistration authorized: {gate['preregistration_authorized']}",
        f"- runner candidate registered: {gate['runner_candidate_registered']}",
        f"- next action: {gate['next_action']}",
        "",
        f"{multiplicity['warning']}",
        "",
    ]
    return "\n".join(lines)
