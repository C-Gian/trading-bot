"""Generate deterministic WP-008 comparison, lessons, and sealed eligibility."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.research.sealed_eligibility import write_eligibility_table
from app.research.wp008_views import build_wp008_comparison


def write(relative: str, payload: object) -> None:
    path = ROOT / relative
    if path.exists():
        raise FileExistsError(f"immutable WP-008 record already exists: {relative}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n")


def main() -> None:
    comparison = build_wp008_comparison(ROOT)
    full = comparison["variants"]["LINEAR_FULL"]
    no_flow = comparison["variants"]["LINEAR_NO_FLOW"]
    lessons = {
        "schema_version": 1,
        "work_package": "WP-008",
        "root_family": "FAM-SUPERVISED-LINEAR",
        "hypothesis_id": "LINEAR_NET_R_SELECTION_V1",
        "primary_experiment_id": "EXP-ML-014-LINEAR-NET-R-FULL",
        "family_terminal_classification": full["terminal_classification"],
        "experiments": {
            full["experiment_id"]: full,
            no_flow["experiment_id"]: no_flow,
        },
        "key_lesson": "The fixed supervised combination barely clears zero costs but loses materially under default and doubled friction; learning does not rescue the exposed descriptors.",
        "ablation_lesson": "Removing F7/F8 changes default expectancy by only -0.0029985450 R and leaves the same cost-dominated rejection.",
        "stability_lesson": "FULL is nonnegative in only 1/6 folds; 2023 is the sole positive year and positive-fold profit concentration is 100%.",
        "prediction_lesson": "Foldwise isolated-label correlations range from -0.0330652157 to +0.1090860500 and change sign, consistent with weak unstable ranking rather than robust OOS prediction.",
        "family_disposition": "Park FAM-SUPERVISED-LINEAR. Do not tune its features, threshold, regularization, algorithm, interactions, label, stop, target, or horizon.",
        "blocked_directions": [
            "LINEAR_NET_R_SELECTION_V1 threshold or feature rescue",
            "LINEAR_NO_FLOW promotion over the preselected primary",
            "model zoo or regularization search",
            "automatic sealed query, Champion promotion, or paper trading",
        ],
        "legitimate_revisit": "Only a genuinely distinct preregistered Research Director allocation with cumulative model-family accounting; no result-driven descendant is implied.",
        "new_trial_allocation": 0,
    }
    write("reports/research/WP-008-COMPARISON.json", comparison)
    write("research/memory/WP-008-LESSONS.json", lessons)
    write_eligibility_table(ROOT)
    print("WP-008 comparison, lessons, and sealed eligibility projection generated.")


if __name__ == "__main__":
    main()
