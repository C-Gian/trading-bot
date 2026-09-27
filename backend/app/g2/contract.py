"""Frozen G2-V0 constants, transcribed from the Gate-A contract set (never tuned here).

Sources:
- `docs/canonical/G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1.md` (sections cited inline);
- `research/g2/G2_DATA_EXPOSURE_AND_EXECUTION_MANIFEST_V1.md`;
- `research/g2/G2_CYCLE_CAUSALITY_CHECKPOINT_V1.md`.

Changing any value here is a scientific revision (contract section 25), not an engineering fix.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

SYSTEM_VERSION = "G2-V0"
CONTRACT_ID = "G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1"
IMPLEMENTATION_VERSION = "G2-01-CAUSAL-TRADER-VERTICAL-SLICE-V1"
INSTRUMENT = "BTCUSDT_USDM_PERPETUAL"

MINUTE = timedelta(minutes=1)
DECISION_MINUTES = 15  # section 2: every completed 15m candle
HORIZON = timedelta(hours=4)  # section 2: r4h(T) = log(P(T+4h) / P(T))
HORIZON_BARS_15M = 16

# Section 3/4: causal EWM half-lives (bars of their own timeframe) and warm-up multiple.
WARMUP_MULTIPLE = 4
LOCAL_FAST_HL, LOCAL_SLOW_HL = 4, 16  # completed 1h
CONTEXT_FAST_HL, CONTEXT_SLOW_HL = 6, 24  # completed 4h
PARTICIPATION_HL = 96  # completed 15m
VOL_FAST_HL, VOL_SLOW_HL = 16, 96  # completed 15m
EPS = 1e-12
ATR_PERIOD = 14  # section 11

COLUMNS = (
    "LOCAL_STRUCTURE",
    "CONTEXT_STRUCTURE",
    "PRICE_EXTENSION",
    "RELATIVE_PARTICIPATION",
    "TAKER_IMBALANCE",
    "VOLATILITY_STATE",
    "LOCAL_STRUCTURE_X_PARTICIPATION",
    "IMBALANCE_X_PRICE_RESPONSE",
)
MAIN_COLUMNS = COLUMNS[:6]

# Section 5: training-only robust scaling.
MAD_FACTOR = 1.4826
CONSTANT_SCALE = 1e-8
CLIP = 8.0

# Section 6: ridge penalties (main / interactions), intercept unpenalized.
PENALTIES = (0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 1.00, 1.00)

# Section 7: fit calendar and training window.
MAX_TRAINING_SPAN = timedelta(days=730)
MIN_TRAINING_SPAN = timedelta(days=180)
MIN_TRAINING_ROWS = 10_000

# Section 8/16: prequential residual archives.
MIN_RESIDUALS = 2_000
MIN_RESIDUAL_SPAN = timedelta(days=30)
MAX_RESIDUAL_AGE = timedelta(days=730)
QUANTILES = (0.10, 0.50, 0.90)
QUANTILE_METHOD = "linear"  # numpy.quantile default (Hyndman-Fan type 7)

# Section 9/10: display-only strength labels and direction tolerance.
STRENGTH_MODERATE, STRENGTH_STRONG = 0.25, 0.75
DIRECTION_TOLERANCE = 1e-12

# Section 12: shadow geometry.
BASE_LATENCY = timedelta(minutes=1)
STOP_ATR_MULTIPLE = 2.0
# Implementation convention: every shadow label (and utility residual) becomes available at the
# close of the exact expiry bar, T+4h+1m, whether or not the stop was hit earlier.
LABEL_HORIZON = HORIZON + MINUTE

# Section 13: historical adverse friction per executed side (scenario data, not constants of
# the simulator): base plus the predeclared stresses.
FRICTION_SCENARIOS = {"BASE": 0.0012, "STRESS_1_5X": 0.0018, "STRESS_2X": 0.0024}
BASE_FRICTION_SCENARIO = "BASE"
LATENCY_STRESS_EXTRA = timedelta(minutes=5)

# Section 14: settled funding; the historical price proxy is the 1m last-price close.
FUNDING_INTERVAL = timedelta(hours=8)
FUNDING_PRICE_PROXY = "USDM_1M_LAST_PRICE_CLOSE_AT_FUNDING_TIME_HISTORICAL_APPROXIMATION"

# Section 17: prudential margin tie tolerance.
MARGIN_TIE = 1e-6

# Section 18: risk governor.
INITIAL_EQUITY = 10_000.0
RISK_FRACTION = 0.0025
MAX_GROSS_NOTIONAL = 1.0
PATH_DRAWDOWN_STOP = 0.05

# Data exposure manifest section 10/16: the G2-01 observation ceiling.
OBSERVATION_CEILING = datetime(2024, 12, 31, 23, 59, 59, 999000, tzinfo=UTC)
PROTECTED_START = datetime(2025, 1, 1, tzinfo=UTC)


def frozen_identity() -> dict[str, object]:
    """Every frozen value, for manifests and the validation artifact."""
    return {
        "system_version": SYSTEM_VERSION,
        "contract": CONTRACT_ID,
        "instrument": INSTRUMENT,
        "decision_minutes": DECISION_MINUTES,
        "horizon_minutes": int(HORIZON.total_seconds() // 60),
        "half_lives": {
            "local": [LOCAL_FAST_HL, LOCAL_SLOW_HL],
            "context": [CONTEXT_FAST_HL, CONTEXT_SLOW_HL],
            "participation": PARTICIPATION_HL,
            "volatility": [VOL_FAST_HL, VOL_SLOW_HL],
        },
        "warmup_multiple": WARMUP_MULTIPLE,
        "columns": list(COLUMNS),
        "penalties": list(PENALTIES),
        "mad_factor": MAD_FACTOR,
        "clip": CLIP,
        "training": {"max_days": 730, "min_days": 180, "min_rows": MIN_TRAINING_ROWS},
        "residuals": {"min_records": MIN_RESIDUALS, "min_days": 30, "max_age_days": 730},
        "quantiles": list(QUANTILES),
        "quantile_method": QUANTILE_METHOD,
        "stop_atr_multiple": STOP_ATR_MULTIPLE,
        "atr_period": ATR_PERIOD,
        "friction": FRICTION_SCENARIOS,
        "margin_tie": MARGIN_TIE,
        "initial_equity": INITIAL_EQUITY,
        "risk_fraction": RISK_FRACTION,
        "max_gross_notional": MAX_GROSS_NOTIONAL,
        "path_drawdown_stop": PATH_DRAWDOWN_STOP,
        "funding_price_proxy": FUNDING_PRICE_PROXY,
    }
