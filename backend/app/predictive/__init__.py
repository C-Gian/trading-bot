"""Predictive foundation for `PREDICTIVE_RESEARCH_GENERATION_V1`.

Labels, chronological folds, the frozen scorer and the four required naive baselines.
Nothing here fits a model, searches a parameter, or reads anything beyond the canonical
BTCUSDT development data inside the development cutoff.
"""

from __future__ import annotations

PREDICTIVE_FOUNDATION_VERSION = "PREDICTIVE_BASELINES_V1"
EVALUATION_CONTRACT = "docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md"
EVALUATION_CONTRACT_AMENDMENT = "A1"
PROTOCOL_PATH = "research/protocols/PREDICTIVE-BASELINES-V1.json"

HORIZON_HOURS = 24
DECISION_CADENCE_HOURS = 1

UP = "UP"
DOWN = "DOWN"
NEUTRAL = "NEUTRAL"
ABSTAIN = "NEUTRAL_UNCERTAIN"

__all__ = [
    "ABSTAIN",
    "DECISION_CADENCE_HOURS",
    "DOWN",
    "EVALUATION_CONTRACT",
    "EVALUATION_CONTRACT_AMENDMENT",
    "HORIZON_HOURS",
    "NEUTRAL",
    "PREDICTIVE_FOUNDATION_VERSION",
    "PROTOCOL_PATH",
    "UP",
]
