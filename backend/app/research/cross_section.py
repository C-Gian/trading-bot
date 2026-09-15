"""CROSS_SECTION_COMMON_EFFECT_V1 frozen policy: universe, eligibility, outcome, power.

This module holds design constants only. It never observes a cross-sectional market
effect and contains no estimator for the true (zero-alignment) pooled ALIGNED beta.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .evaluation_protocol import HOUR_US, utc_us

# --- development window ------------------------------------------------------------
DEVELOPMENT_START = "2019-01-01T00:00:00Z"
DEVELOPMENT_END = "2024-12-31T23:59:00Z"
DEVELOPMENT_START_US = utc_us(DEVELOPMENT_START)
DEVELOPMENT_END_US = utc_us(DEVELOPMENT_END)
DAY_US = 24 * HOUR_US

# --- frozen universe policy (section E) --------------------------------------------
HYPOTHESIS_ID = "ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1"
UNIVERSE_SOURCE = "BINANCE_SPOT_MONTHLY_KLINE_ARCHIVE_1H"
UNIVERSE_DERIVATION = "HISTORICAL_ARCHIVE_EVIDENCE_NOT_CURRENT_EXCHANGE_INFO"
QUOTE_ASSET = "USDT"
LEVERAGED_TOKEN_SUFFIXES = ("UP", "DOWN", "BULL", "BEAR")
ARCHIVE_BASE = "https://data.binance.vision"
ARCHIVE_LISTING_BASE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
ARCHIVE_PREFIX = "data/spot/monthly/klines"
KLINE_INTERVAL = "1h"
MONTH_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")

# --- frozen causal eligibility (section F) -----------------------------------------
MINIMUM_HISTORY_DAYS = 30
LIQUIDITY_LOOKBACK_DAYS = 30
MINIMUM_MEDIAN_DAILY_QUOTE_VOLUME_USDT = 10_000_000.0
PLANNING_ORDER_NOTIONAL_USDT = 5_000.0
ELIGIBILITY_RATIONALE = "CAPACITY_AND_DATA_QUALITY_NOT_PERFORMANCE_OPTIMIZATION"
INTERPOLATION_POLICY = "CANONICAL_GAPS_NEVER_INTERPOLATED"

# --- frozen outcome (section H) -----------------------------------------------------
OUTCOME_HORIZON_HOURS = 24
OUTCOME_METRIC = "FORWARD_LOG_PRICE_RETURN_BPS"
OUTCOME_START_RULE = "NEXT_COMPLETED_TRADABLE_HOURLY_OPEN_AFTER_DECISION"
OUTCOME_TERMINAL_RULE = "LATEST_LEGITIMATE_TRADABLE_PRICE_AT_OR_BEFORE_PLUS_24H"

# --- frozen pooled estimand (section I) ---------------------------------------------
PRIMARY_ESTIMAND = "TWO_WAY_FIXED_EFFECTS_POOLED_ALIGNED_BETA"
PRIMARY_COUNT = 1
FIXED_EFFECTS = ("ASSET", "DECISION_TIME")
PRIMARY_CLAIM = "BETA_GREATER_THAN_ZERO"
PER_ASSET_ROLE = "DESCRIPTIVE_DIAGNOSTIC_NEVER_PRIMARY_NEVER_SELECTION"

# --- frozen economic threshold (section J) ------------------------------------------
CROSS_SECTION_MESI_BPS = 24.0
OWNER_ANNUAL_MESI_BPS = 500.0
HISTORICAL_ALIGNED_TRADES = 125
HISTORICAL_ALIGNED_YEARS = 6

# --- frozen inference design (section K) --------------------------------------------
CLUSTER_DIMENSIONS = ("ASSET_INSTRUMENT_EPOCH", "UTC_CALENDAR_WEEK")
CLUSTER_METHOD = "TWO_WAY_CAMERON_GELBACH_MILLER_INCLUSION_EXCLUSION"
MINIMUM_ASSET_CLUSTERS = 30
MINIMUM_WEEK_CLUSTERS = 100
DEGREES_OF_FREEDOM_RULE = "CONSERVATIVE_MINIMUM_CLUSTER_DIMENSION_MINUS_ONE"

# --- frozen multiplicity (section L) ------------------------------------------------
OBSERVED_FAMILY_SIZE = 12
PROSPECTIVE_FAMILY_SIZE = 13
FAMILYWISE_ALPHA = 0.05
EFFECTIVE_ALPHA = FAMILYWISE_ALPHA / PROSPECTIVE_FAMILY_SIZE
TEST_SIDEDNESS = "ONE_SIDED_POSITIVE"
UNQUANTIFIED_PRE_REPO_EXPOSURE = True

# --- frozen placebo calibration (section M) -----------------------------------------
PLACEBO_METHOD = "DETERMINISTIC_CIRCULAR_SHIFT_WITHIN_CAUSALLY_ELIGIBLE_HISTORY"
PLACEBO_MINIMUM_ABS_SHIFT_POSITIONS = 168
PLACEBO_ZERO_SHIFT_ALLOWED = False

# --- frozen power gate (section N/O) ------------------------------------------------
TARGET_POWER = 0.80
SYNTHETIC_INJECTION_BPS = (0.0, 12.0, 24.0, 48.0, 96.0)
GATE_KEYS = (
    "DATA_SOURCE_STATUS",
    "UNIVERSE_FEASIBILITY_STATUS",
    "DATA_FEASIBILITY_STATUS",
    "SURVIVORSHIP_STATUS",
    "CLUSTER_SUPPORT_STATUS",
    "PLACEBO_CALIBRATION_STATUS",
    "DEPENDENCE_INFERENCE_STATUS",
)

# --- product boundary (section B) ---------------------------------------------------
PRODUCT_UNIVERSE = "BTCUSDT_SPOT_V1"
CROSS_SECTION_ROLE = "SCIENTIFIC_GENERALIZATION_ONLY"
CROSS_SECTION_PRODUCT_AUTHORIZED = False
REAL_MONEY_AUTHORIZED = False

FORBIDDEN_RESULT_KEYS = (
    "pooled_beta",
    "beta",
    "t_statistic",
    "p_value",
    "zero_shift_beta",
    "zero_alignment_beta",
    "per_asset_beta",
    "per_asset_effect",
    "cross_section_verdict",
)


class UniversePolicyViolation(ValueError):
    """A symbol or event violates the frozen point-in-time universe policy."""


def is_leveraged_token(symbol: str) -> bool:
    """Frozen mechanical rule: a leveraged suffix immediately precedes the quote asset.

    The rule is deliberately literal and non-discretionary. It is applied to the symbol
    string alone so that no post-hoc judgement about individual assets can enter the
    universe. Symbols it removes are enumerated in the survivorship audit.
    """
    if not symbol.endswith(QUOTE_ASSET):
        return False
    base = symbol[: -len(QUOTE_ASSET)]
    return any(base.endswith(suffix) for suffix in LEVERAGED_TOKEN_SUFFIXES)


def is_candidate_symbol(symbol: str) -> bool:
    """USDT-quoted archive symbol that is not excluded by the frozen leveraged rule."""
    return (
        symbol.endswith(QUOTE_ASSET)
        and len(symbol) > len(QUOTE_ASSET)
        and not is_leveraged_token(symbol)
    )


def month_in_development(month: str) -> bool:
    """A monthly archive partition whose first instant is inside the development window."""
    matched = MONTH_PATTERN.match(month)
    if not matched:
        raise ValueError(f"malformed archive month partition: {month}")
    year, index = int(matched.group(1)), int(matched.group(2))
    if not 1 <= index <= 12:
        raise ValueError(f"malformed archive month partition: {month}")
    start = utc_us(f"{year:04d}-{index:02d}-01T00:00:00Z")
    return DEVELOPMENT_START_US <= start <= DEVELOPMENT_END_US


def monthly_object_key(symbol: str, month: str) -> str:
    return f"{ARCHIVE_PREFIX}/{symbol}/{KLINE_INTERVAL}/{symbol}-{KLINE_INTERVAL}-{month}.zip"


def monthly_object_url(symbol: str, month: str) -> str:
    return f"{ARCHIVE_BASE}/{monthly_object_key(symbol, month)}"


@dataclass(frozen=True)
class ArchiveObject:
    """One official monthly 1h kline archive object as listed by the source bucket."""

    symbol: str
    month: str
    key: str
    url: str
    size_bytes: int
    quote_asset: str = QUOTE_ASSET

    def within_development(self) -> bool:
        return month_in_development(self.month)


def effective_alpha() -> float:
    return EFFECTIVE_ALPHA


def mesi_bps() -> float:
    """The frozen informational lower bound, rederived from the governed Owner MESI."""
    derived = OWNER_ANNUAL_MESI_BPS / (HISTORICAL_ALIGNED_TRADES / HISTORICAL_ALIGNED_YEARS)
    if round(derived, 6) != CROSS_SECTION_MESI_BPS:
        raise ValueError("MESI derivation drifted from the frozen 24.0 bps/event bound")
    return CROSS_SECTION_MESI_BPS


def assert_no_real_effect_leakage(payload: object, path: str = "$") -> None:
    """Fail closed if an artifact ever carries a real zero-alignment cross-sectional effect."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in FORBIDDEN_RESULT_KEYS:
                raise UniversePolicyViolation(f"forbidden real-effect key at {path}.{key}")
            assert_no_real_effect_leakage(value, f"{path}.{key}")
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            assert_no_real_effect_leakage(value, f"{path}[{index}]")
