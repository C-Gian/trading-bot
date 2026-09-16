"""ALIGNED_GATE_INTENSITY_COMMON_EFFECT_V1: frozen score and calendar randomization.

This module holds design constants, the frozen integer gate-intensity score, and the
deterministic calendar-synchronous randomization family. It contains no estimator for the
true (zero-shift) pooled effect: every shift vector it can produce is non-zero in every
development year by construction.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .cross_section import CROSS_SECTION_MESI_BPS, DAY_US
from .evaluation_protocol import HOUR_US

HYPOTHESIS_ID = "ALIGNED_GATE_INTENSITY_COMMON_EFFECT_V1"
PARENT_HYPOTHESIS_ID = "ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1"
STRATEGY_VERSION = "ALIGNED_PARTICIPATION_CONTINUATION_V1"

# --- frozen score (section D) --------------------------------------------------------
GATE_NAMES = ("DIRECTION_PERSISTENCE", "BREAKOUT", "PARTICIPATION_VOLUME")
GATE_INTENSITY_VALUES = (0, 1, 2, 3)
GATE_WEIGHTS: tuple[int, ...] = (1, 1, 1)  # unweighted integer sum; never tunable
GATE_SCORE_DEFINITION = (
    "GATE_INTENSITY = int(direction_pass) + int(breakout_pass) + int(participation_pass)"
)
ALIGNED_EQUIVALENCE_RULE = "ALIGNED_SIGNAL == 1 IFF GATE_INTENSITY == 3"
NEW_GATE_PARAMETERS = 0
CONTINUOUS_RESCALING = False
ASSET_SPECIFIC_NORMALIZATION = False
PARAMETER_FITTING = False

# --- frozen primary (section E) ------------------------------------------------------
PRIMARY_COEFFICIENT = "beta_gate"
PRIMARY_COUNT = 1
FIXED_EFFECTS = ("ASSET", "DECISION_TIME")
PRIMARY_CLAIM = "BETA_GATE_GREATER_THAN_ZERO"
OUTCOME_METRIC = "FORWARD_LOG_PRICE_RETURN_BPS"
OUTCOME_HORIZON_HOURS = 24
NONLINEAR_SCORE_MODEL = False
PER_BUCKET_COEFFICIENTS = False
GATE_INTERACTIONS = False

# --- frozen economic threshold (section F) -------------------------------------------
GATE_INTENSITY_MESI_BPS_PER_GATE = 8.0
MESI_DERIVATION = "ALIGNED_INFORMATION_MESI_24_BPS / 3_GATE_SPAN"

# --- frozen multiplicity / power (sections J, K) --------------------------------------
PROSPECTIVE_FAMILY_SIZE = 13
FAMILYWISE_ALPHA = 0.05
EFFECTIVE_ALPHA = FAMILYWISE_ALPHA / PROSPECTIVE_FAMILY_SIZE
TEST_SIDEDNESS = "ONE_SIDED_POSITIVE"
TARGET_POWER = 0.80
SYNTHETIC_SLOPES_BPS_PER_GATE = (0.0, 4.0, 8.0, 16.0, 32.0)
PRIMARY_INFERENCE = "EMPIRICAL_RANDOMIZATION"
ANALYTIC_CLUSTER_ROLE = "DIAGNOSTIC_ONLY_NEVER_OVERRIDES_RANDOMIZATION"

# --- frozen calendar-synchronous randomization (section H) ----------------------------
RANDOMIZATION_METHOD = "CALENDAR_SYNCHRONOUS_WHOLE_WEEK_YEAR_SHIFT_V1"
RANDOMIZATION_SEED = "ALIGNED_GATE_INTENSITY_CALENDAR_RANDOMIZATION_V1"
DEVELOPMENT_YEARS = (2019, 2020, 2021, 2022, 2023, 2024)
WEEK_US = 7 * DAY_US
MINIMUM_SHIFT_WEEKS = 2
MAXIMUM_SHIFT_WEEKS = 13
ZERO_SHIFT_ALLOWED = False
CIRCULAR_WRAP = False
REQUESTED_REPLICATE_VECTORS = 1024
LEGAL_SHIFT_WEEKS: tuple[int, ...] = tuple(
    weeks
    for magnitude in range(MINIMUM_SHIFT_WEEKS, MAXIMUM_SHIFT_WEEKS + 1)
    for weeks in (-magnitude, magnitude)
)

# --- frozen support gate (section I) --------------------------------------------------
MINIMUM_ROW_RETENTION = 0.70
MINIMUM_ASSET_CLUSTER_RETENTION = 0.80
REQUIRED_YEAR_COVERAGE = len(DEVELOPMENT_YEARS)
MINIMUM_ACCEPTED_VECTORS = 512

# --- family consequence (sections C, L) -----------------------------------------------
FINAL_AUTHORIZED_DESCENDANT = True
FAMILY_STATUS_ON_FAILURE = "PARKED_DEVELOPMENT_SEARCH_EXHAUSTED"


class ZeroShiftForbidden(ValueError):
    """The true zero-shift alignment may never be evaluated in this checkpoint."""


class GateScoreViolation(ValueError):
    """The frozen integer gate-intensity contract was broken."""


def mesi_bps_per_gate() -> float:
    """Rederive the frozen per-gate threshold from the governed ALIGNED information MESI."""
    derived = CROSS_SECTION_MESI_BPS / 3.0
    if round(derived, 10) != GATE_INTENSITY_MESI_BPS_PER_GATE:
        raise ValueError("per-gate MESI drifted from the frozen 8.0 bps/gate bound")
    return GATE_INTENSITY_MESI_BPS_PER_GATE


def validate_shift_weeks(weeks: int) -> int:
    """A legal displacement is a non-zero whole-week shift inside the frozen band."""
    if weeks == 0:
        raise ZeroShiftForbidden("calendar randomization may never use a zero displacement")
    if not MINIMUM_SHIFT_WEEKS <= abs(weeks) <= MAXIMUM_SHIFT_WEEKS:
        raise ZeroShiftForbidden("displacement is outside the frozen 2..13 week band")
    return weeks


def shift_microseconds(weeks: int) -> int:
    return validate_shift_weeks(weeks) * WEEK_US


@dataclass(frozen=True)
class ShiftVector:
    """One replicate: a single signed whole-week displacement per development year.

    The same displacement applies to every asset in that year, so the entire
    cross-sectional score field moves together and cross-asset synchrony is preserved.
    """

    index: int
    weeks_by_year: tuple[int, ...]

    def validate(self) -> ShiftVector:
        if len(self.weeks_by_year) != len(DEVELOPMENT_YEARS):
            raise ZeroShiftForbidden("a shift vector must cover every development year")
        for weeks in self.weeks_by_year:
            validate_shift_weeks(weeks)
        return self

    def mapping(self) -> dict[int, int]:
        return dict(zip(DEVELOPMENT_YEARS, self.weeks_by_year, strict=True))

    def as_list(self) -> list[int]:
        return list(self.weeks_by_year)


def _draw(seed: str, index: int, year: int) -> int:
    """Counter-based deterministic draw; depends only on the seed, index and calendar."""
    digest = hashlib.sha256(f"{seed}|{index}|{year}".encode()).digest()
    return LEGAL_SHIFT_WEEKS[int.from_bytes(digest[:8], "big") % len(LEGAL_SHIFT_WEEKS)]


def build_shift_vectors(count: int = REQUESTED_REPLICATE_VECTORS) -> list[ShiftVector]:
    """Deterministic unique shift family derived only from the seed and calendar geometry.

    No market data, outcome, signal or asset identity enters the construction, so the
    family is fixed before anything about the panel is measured.
    """
    vectors: list[ShiftVector] = []
    seen: set[tuple[int, ...]] = set()
    index = 0
    while len(vectors) < count:
        weeks = tuple(_draw(RANDOMIZATION_SEED, index, year) for year in DEVELOPMENT_YEARS)
        if weeks not in seen:
            seen.add(weeks)
            vectors.append(ShiftVector(len(vectors), weeks).validate())
        index += 1
        if index > 100 * count:
            raise ValueError("shift family failed to reach the requested unique count")
    return vectors


def shift_family_digest(vectors: list[ShiftVector]) -> str:
    payload = "\n".join(
        f"{vector.index}:" + ",".join(str(weeks) for weeks in vector.weeks_by_year)
        for vector in vectors
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def gate_intensity(direction: bool, breakout: bool, participation: bool) -> int:
    """The frozen unweighted integer score over the three existing ALIGNED gates."""
    score = int(bool(direction)) + int(bool(breakout)) + int(bool(participation))
    if score not in GATE_INTENSITY_VALUES:
        raise GateScoreViolation("gate intensity escaped the frozen 0..3 integer range")
    return score


def aligned_from_intensity(score: int) -> bool:
    """ALIGNED fires exactly when all three frozen gates pass."""
    return score == 3


def hour_year(open_us: int) -> int:
    """UTC calendar year of a decision hour, used only to select the year displacement."""
    from datetime import UTC, datetime

    return datetime.fromtimestamp(int(open_us) / 1_000_000, UTC).year


def design_summary() -> dict[str, Any]:
    """The frozen design, emitted into artifacts so drift is detectable."""
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
        "strategy_version": STRATEGY_VERSION,
        "aligned_modified": False,
        "score_definition": GATE_SCORE_DEFINITION,
        "gate_names": list(GATE_NAMES),
        "gate_weights": list(GATE_WEIGHTS),
        "gate_intensity_values": list(GATE_INTENSITY_VALUES),
        "aligned_equivalence_rule": ALIGNED_EQUIVALENCE_RULE,
        "new_gate_parameters": NEW_GATE_PARAMETERS,
        "continuous_rescaling": CONTINUOUS_RESCALING,
        "asset_specific_normalization": ASSET_SPECIFIC_NORMALIZATION,
        "parameter_fitting": PARAMETER_FITTING,
        "primary_coefficient": PRIMARY_COEFFICIENT,
        "primary_count": PRIMARY_COUNT,
        "fixed_effects": list(FIXED_EFFECTS),
        "primary_claim": PRIMARY_CLAIM,
        "outcome_metric": OUTCOME_METRIC,
        "outcome_horizon_hours": OUTCOME_HORIZON_HOURS,
        "nonlinear_score_model": NONLINEAR_SCORE_MODEL,
        "per_bucket_coefficients": PER_BUCKET_COEFFICIENTS,
        "gate_interactions": GATE_INTERACTIONS,
        "mesi_bps_per_gate": GATE_INTENSITY_MESI_BPS_PER_GATE,
        "mesi_derivation": MESI_DERIVATION,
        "prospective_family_size": PROSPECTIVE_FAMILY_SIZE,
        "effective_alpha": EFFECTIVE_ALPHA,
        "sidedness": TEST_SIDEDNESS,
        "target_power": TARGET_POWER,
        "primary_inference": PRIMARY_INFERENCE,
        "analytic_cluster_role": ANALYTIC_CLUSTER_ROLE,
        "randomization_method": RANDOMIZATION_METHOD,
        "randomization_seed": RANDOMIZATION_SEED,
        "development_years": list(DEVELOPMENT_YEARS),
        "minimum_shift_weeks": MINIMUM_SHIFT_WEEKS,
        "maximum_shift_weeks": MAXIMUM_SHIFT_WEEKS,
        "zero_shift_allowed": ZERO_SHIFT_ALLOWED,
        "circular_wrap": CIRCULAR_WRAP,
        "requested_replicate_vectors": REQUESTED_REPLICATE_VECTORS,
        "minimum_row_retention": MINIMUM_ROW_RETENTION,
        "minimum_asset_cluster_retention": MINIMUM_ASSET_CLUSTER_RETENTION,
        "required_year_coverage": REQUIRED_YEAR_COVERAGE,
        "minimum_accepted_vectors": MINIMUM_ACCEPTED_VECTORS,
        "synthetic_slopes_bps_per_gate": list(SYNTHETIC_SLOPES_BPS_PER_GATE),
        "final_authorized_descendant": FINAL_AUTHORIZED_DESCENDANT,
        "family_status_on_failure": FAMILY_STATUS_ON_FAILURE,
    }


HOURS_PER_WEEK = WEEK_US // HOUR_US
