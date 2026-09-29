"""The fixed G2-02 batch: G2-V0, the four frozen references and the two diagnostic ablations.

Definitions are transcriptions of the frozen contracts, not choices:
- G2-V0: contract sections 4-18 exactly (eight columns, utility heads, prudential margin);
- TREND_ONLY_FORECAST: contract section 23 (LOCAL_STRUCTURE, CONTEXT_STRUCTURE, PRICE_EXTENSION;
  same calendar, scaling, target, ridge penalties and residual-distribution rule);
- TREND_REFERENCE_POLICY: LONG iff TREND_ONLY q10 > 0, SHORT iff q90 < 0, otherwise NO_TRADE, under
  the same entry/stop/expiry/friction/funding/risk contract (it shares the TREND_ONLY run);
- NULL_FORECAST: location zero (mu_z = 0, no conditional term) with the same causal residual
  distribution rule and SIGMA_4H scale estimated only from past mature data;
- CASH_REFERENCE: zero exposure (no simulation needed; its equity path is constant);
- ABL-G2-01 / ABL-G2-02: protocol section 7 (column removal, same ridge/calendar/window/penalties).

Common state support: every system is gated by the identical eight-column G2-V0 state availability
and the identical training-row finiteness rule, so paired comparisons share one decision timeline
and differ only in the model dictionary / policy (no system gains rows by dropping a column).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ..contract import COLUMNS, MAIN_COLUMNS, PENALTIES

INITIALIZATION_START = datetime(2020, 1, 1, tzinfo=UTC)
ECONOMIC_START = datetime(2021, 1, 1, tzinfo=UTC)  # scored exposed development begins
OBSERVATION_END = datetime(2025, 1, 1, tzinfo=UTC)  # exclusive; 2025+ is forbidden

BASELINE = "BASELINE"
REFERENCE = "FIXED_REFERENCE"
ABLATION = "DIAGNOSTIC_ABLATION"

TREND_COLUMNS = ("LOCAL_STRUCTURE", "CONTEXT_STRUCTURE", "PRICE_EXTENSION")
ABL_01_REMOVED = (
    "RELATIVE_PARTICIPATION",
    "TAKER_IMBALANCE",
    "LOCAL_STRUCTURE_X_PARTICIPATION",
    "IMBALANCE_X_PRICE_RESPONSE",
)


@dataclass(frozen=True)
class Variant:
    run_key: str
    systems: tuple[str, ...]  # the scored system identities this simulation produces
    role: str
    active: tuple[str, ...]
    forecast_mode: str  # RIDGE / NULL
    policy_mode: str  # UTILITY / TREND_QUANTILE / NONE
    utility_heads: bool
    cycle_shadow: bool
    definition: str

    @property
    def mask(self) -> tuple[bool, ...]:
        return tuple(column in self.active for column in COLUMNS)

    @property
    def system_version(self) -> str:
        return self.systems[0]

    def identity(self) -> dict[str, object]:
        return {
            "run_key": self.run_key,
            "systems": list(self.systems),
            "role": self.role,
            "active_columns": list(self.active),
            "removed_columns": [c for c in COLUMNS if c not in self.active],
            "penalties_of_active_columns": [
                p for c, p in zip(COLUMNS, PENALTIES, strict=True) if c in self.active
            ],
            "forecast_mode": self.forecast_mode,
            "policy_mode": self.policy_mode,
            "utility_heads": self.utility_heads,
            "cycle_role": "SHADOW_ONLY" if self.cycle_shadow else "NOT_COMPUTED_ZERO_ROLE",
            "definition": self.definition,
        }


G2_V0 = Variant(
    "G2-V0",
    ("G2-V0",),
    BASELINE,
    COLUMNS,
    "RIDGE",
    "UTILITY",
    True,
    True,
    "Frozen Gate-A/B G2-V0: eight-column forecast ridge, LONG/SHORT NET_R utility heads, "
    "prudential margin, one-position risk governor; cycle SHADOW_ONLY.",
)
ABL_G2_01 = Variant(
    "ABL-G2-01",
    ("ABL-G2-01",),
    ABLATION,
    tuple(c for c in COLUMNS if c not in ABL_01_REMOVED),
    "RIDGE",
    "UTILITY",
    True,
    False,
    "FULL_MINUS_PARTICIPATION_FLOW_RESPONSE: remove RELATIVE_PARTICIPATION, TAKER_IMBALANCE, "
    "LOCAL_STRUCTURE_X_PARTICIPATION, IMBALANCE_X_PRICE_RESPONSE; same ridge/calendar/window/"
    "penalties in forecast and both utility heads. Diagnostic only; not promotable.",
)
ABL_G2_02 = Variant(
    "ABL-G2-02",
    ("ABL-G2-02",),
    ABLATION,
    MAIN_COLUMNS,
    "RIDGE",
    "UTILITY",
    True,
    False,
    "FULL_ADDITIVE_ONLY: retain the six main observables, remove both interaction terms; same "
    "ridge/calendar/window/penalties in forecast and both utility heads. Diagnostic only.",
)
TREND = Variant(
    "TREND-REFERENCE",
    ("TREND_ONLY_FORECAST", "TREND_REFERENCE_POLICY"),
    REFERENCE,
    TREND_COLUMNS,
    "RIDGE",
    "TREND_QUANTILE",
    False,
    False,
    "TREND_ONLY_FORECAST (LOCAL_STRUCTURE, CONTEXT_STRUCTURE, PRICE_EXTENSION; same calendar, "
    "scaling, target, ridge and residual rule) and TREND_REFERENCE_POLICY (LONG iff q10 > 0, "
    "SHORT iff q90 < 0, else NO_TRADE; identical entry/stop/expiry/friction/funding/risk).",
)
NULL = Variant(
    "NULL-FORECAST",
    ("NULL_FORECAST",),
    REFERENCE,
    (),
    "NULL",
    "NONE",
    False,
    False,
    "NULL_FORECAST: location zero (mu_z = 0) with the same causal residual rule (training-target "
    "baseline, then the prequential archive) and the same SIGMA_4H scale; forecast reference only.",
)
CASH_SYSTEM = "CASH_REFERENCE"
BATCH = (G2_V0, ABL_G2_01, ABL_G2_02, TREND, NULL)
VARIANTS = {variant.run_key: variant for variant in BATCH}

FORECAST_SYSTEMS = ("G2-V0", "NULL_FORECAST", "TREND_ONLY_FORECAST", "ABL-G2-01", "ABL-G2-02")
POLICY_SYSTEMS = ("G2-V0", "TREND_REFERENCE_POLICY", CASH_SYSTEM, "ABL-G2-01", "ABL-G2-02")
SYSTEM_RUN = {
    "G2-V0": "G2-V0",
    "ABL-G2-01": "ABL-G2-01",
    "ABL-G2-02": "ABL-G2-02",
    "TREND_ONLY_FORECAST": "TREND-REFERENCE",
    "TREND_REFERENCE_POLICY": "TREND-REFERENCE",
    "NULL_FORECAST": "NULL-FORECAST",
}
# Eligible paired comparisons: G2-V0 against each applicable reference and each ablation.
FORECAST_COMPARISONS = tuple(("G2-V0", other) for other in FORECAST_SYSTEMS[1:])
POLICY_COMPARISONS = tuple(("G2-V0", other) for other in POLICY_SYSTEMS[1:])
