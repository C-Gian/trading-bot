"""Deterministic reporting and validation for `PREDICTIVE-INTERNAL-STRUCTURE-V1`.

The JSON result is the truth. The Markdown is generated from it, so the two can never drift,
and the validator re-derives the advancement gate from the reported numbers instead of
trusting the classification string that was written next to them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .baselines import ALWAYS_UP
from .internal_features import FEATURE_NAMES, FEATURE_SET_VERSION
from .internal_model import LINEAR_MODEL_VERSION
from .internal_structure import (
    ADMISSION_PATH,
    ADVANCE,
    EXPERIMENT_ID,
    GATE_NAMES,
    MINIMUM_IMPORTANT_EFFECT,
    NO_ADVANCE,
    PREREGISTRATION_PATH,
    REPORT_JSON_PATH,
    REPORT_MARKDOWN_PATH,
    RESULT_PATH,
    SEARCH_PLAN_PATH,
    STAGE1_FAMILY_SIZE,
    ExperimentError,
    admission,
    advancement_gate,
    canonical_bytes,
    preregistration,
    run_experiment,
    search_plan,
)

ROOT = Path(__file__).resolve().parents[3]


def _number(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def _signed(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):+.{digits}f}"


def build_markdown(result: dict[str, Any]) -> str:
    """Render the committed result. Every number here is copied, never recomputed."""
    pooled = result["candidate"]["pooled_directional"]
    magnitude = result["candidate"]["pooled_magnitude"]
    comparison = result["primary_comparison"]
    paired = comparison["paired_interval"]
    gate = result["advancement_gate"]
    features = result["features"]

    lines: list[str] = []
    lines.append("# Predictive internal structure V1")
    lines.append("")
    lines.append(
        f"`{result['experiment_id']}` — `{result['hypothesis_id']}` / "
        f"`{result['model_version']}`, the first result-bearing experiment of "
        f"`{result['research_generation']}`."
    )
    lines.append("")
    lines.append(
        f"Terminal classification: **{result['terminal_classification']}**. "
        f"Stage-1 budget consumed: "
        f"{result['search_budget']['stage1_configurations_consumed']} of "
        f"{result['search_budget']['stage1_configurations_planned']}."
    )
    lines.append("")
    lines.append("## Candidate against the matched control")
    lines.append("")
    lines.append(
        f"Pooled candidate win rate **{_number(pooled['win_rate'])}** on "
        f"{pooled['actionable_directional_predictions']} actionable predictions at coverage "
        f"{_number(pooled['coverage'], 5)} over "
        f"{pooled['eligible_decision_timestamps']} eligible decision timestamps, with "
        f"{pooled['abstentions']} counted abstentions and "
        f"{pooled['declared_side_on_neutral_truth']} declared sides on NEUTRAL truth."
    )
    lines.append("")
    lines.append(
        f"Matched `{ALWAYS_UP}` on the identical timestamps: "
        f"**{_number(comparison['pooled']['matched_always_up_win_rate'])}**. "
        f"Primary delta **{_signed(comparison['pooled']['delta'])}** against a minimum "
        f"important effect of {_signed(MINIMUM_IMPORTANT_EFFECT, 3)}."
    )
    lines.append("")
    lines.append(
        f"Paired {100 * paired['interval_mass']:g}% "
        f"{paired['method'].lower().replace('_', ' ')} interval "
        f"[{_signed(paired['interval'][0])}, {_signed(paired['interval'][1])}] "
        f"from {paired['replicates']} replicates of "
        f"{paired['block_length_hours']}h blocks at seed {paired['seed']}, "
        f"alpha {paired['alpha']}."
    )
    lines.append("")
    lines.append(
        "The canonical full-universe reference bar is "
        f"{_number(result['baseline_context']['reference_bar'])} "
        f"(`{ALWAYS_UP}`, PREDICTIVE-BASELINES-V1, unchanged)."
    )
    lines.append("")
    lines.append("## Per fold")
    lines.append("")
    lines.append(
        "| fold | eligible | actionable | abstentions | coverage | candidate | "
        "matched ALWAYS_UP | delta |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for name, record in result["candidate"]["by_fold"].items():
        directional = record["directional"]
        matched = record["matched_baseline"]
        lines.append(
            f"| {name} | {directional['eligible_decision_timestamps']} | "
            f"{directional['actionable_directional_predictions']} | "
            f"{directional['abstentions']} | {_number(directional['coverage'], 5)} | "
            f"{_number(directional['win_rate'])} | "
            f"{_number(matched['matched_always_up_win_rate'])} | "
            f"{_signed(matched['delta'])} |"
        )
    lines.append("")
    lines.append("## Calibration")
    lines.append("")
    lines.append(f"Pooled Brier score **{_number(pooled['brier_score'])}**.")
    lines.append("")
    lines.append("| bin | count | mean predicted | empirical correct |")
    lines.append("| --- | --- | --- | --- |")
    for row in pooled["reliability_table"]:
        lines.append(
            f"| {row['bin']} | {row['count']} | "
            f"{_number(row['mean_predicted_probability'])} | "
            f"{_number(row['empirical_frequency_correct'])} |"
        )
    lines.append("")
    lines.append("## Magnitude")
    lines.append("")
    universe = result["candidate"]["pooled_magnitude_universe"]
    lines.append(
        f"Signed 24h return MAE **{_number(magnitude['magnitude_mae_percentage_points'])} pp** "
        f"({_number(magnitude['magnitude_mae_basis_points'], 2)} bps), median absolute error "
        f"{_number(magnitude['magnitude_median_absolute_error_percentage_points'])} pp, over "
        f"{universe['feature_available_rows_scored']} feature-available rows; "
        f"{universe['abstained_rows_excluded_and_counted']} abstained rows declare no "
        "magnitude and are excluded and counted."
    )
    lines.append("")
    exclusions = magnitude["magnitude_match_exclusions"]
    lines.append(
        f"Signed magnitude-match mean **{_number(magnitude['magnitude_match_mean'], 2)}** over "
        f"{magnitude['magnitude_match_included']} included records; exclusions "
        + ", ".join(f"`{name}` {count}" for name, count in sorted(exclusions.items()))
        + "."
    )
    lines.append("")
    lines.append("## Advancement gate")
    lines.append("")
    lines.append("| condition | threshold | observed | passed |")
    lines.append("| --- | --- | --- | --- |")
    for name in GATE_NAMES:
        condition = gate["conditions"][name]
        lines.append(
            f"| `{name}` | {condition['threshold']} | "
            f"{_number(condition['observed'], 5)} | "
            f"{'yes' if condition['passed'] else 'no'} |"
        )
    lines.append("")
    if gate["failed_conditions"]:
        lines.append(
            "Failed conditions: "
            + ", ".join(f"`{name}`" for name in gate["failed_conditions"])
            + ". Secondary calibration or magnitude performance cannot rescue a failed "
            "primary directional gate, and no tuned descendant is authorized."
        )
    else:
        lines.append("Every predeclared condition holds.")
    lines.append("")
    lines.append("## Features and fits")
    lines.append("")
    lines.append(
        f"`{features['version']}`, {features['count']} causal features: "
        + ", ".join(f"`{name}`" for name in features["ordered_names"])
        + "."
    )
    lines.append("")
    lines.append(
        f"{features['available_vectors']} available vectors, "
        f"{features['unavailable_vectors']} unavailable and typed: "
        + ", ".join(
            f"`{name}` {count}"
            for name, count in sorted(features["unavailability_by_reason"].items())
        )
        + "."
    )
    lines.append("")
    fits = result["model_fits"]
    lines.append(
        f"Model fits {fits['total']}: {fits['direction_base']} direction base, "
        f"{fits['direction_calibration']} training-only Platt calibration, "
        f"{fits['magnitude']} magnitude. No hyperparameter search, no threshold search, no "
        "feature search."
    )
    lines.append("")
    lines.append("## Accounting")
    lines.append("")
    lines.append(
        f"Sealed queries {result['boundaries']['sealed_queries']}. Champion NONE. Real money "
        f"{str(result['boundaries']['real_money']).lower()}. "
        f"External information family "
        f"{str(result['boundaries']['external_information_family']).lower()}. "
        f"Post-cutoff market data "
        f"{str(result['boundaries']['post_cutoff_market_data']).lower()}. "
        "PREDICTIVE-BASELINES-V1 results unchanged."
    )
    lines.append("")
    return "\n".join(lines)


def report_bytes(result: dict[str, Any]) -> bytes:
    return canonical_bytes(result)


def markdown_bytes(result: dict[str, Any]) -> bytes:
    return build_markdown(result).encode("utf-8")


def load_result(root: Path = ROOT) -> dict[str, Any]:
    return json.loads((root / RESULT_PATH).read_text(encoding="utf-8"))


def validate_internal_structure(
    root: Path = ROOT, *, data_available: bool = False
) -> dict[str, Any]:
    """Check the committed experiment against its own frozen records, and the data if present.

    Without market data this proves the frozen records still match the code, the admission
    hashes still match the implementation, the gate follows from the reported numbers, and
    the Markdown is generated from the committed JSON. With the data installed it also
    proves the committed bytes are exactly what the current code recomputes.
    """
    findings: dict[str, Any] = {"status": "PASS", "data_replayed": False}

    plan = json.loads((root / SEARCH_PLAN_PATH).read_text(encoding="utf-8"))
    prereg = json.loads((root / PREREGISTRATION_PATH).read_text(encoding="utf-8"))
    admitted = json.loads((root / ADMISSION_PATH).read_text(encoding="utf-8"))
    if plan != search_plan():
        raise ExperimentError("the committed Stage-1 search plan drifted from the code")
    if prereg != preregistration():
        raise ExperimentError("the committed preregistration drifted from the code")
    if admitted != admission(root):
        raise ExperimentError("the admission artifact no longer matches the frozen files")
    if admitted["status"] != "PASS":
        raise ExperimentError("the pre-execution admission gate did not pass")
    if admitted["model_fits_executed"] or admitted["market_results_observed"]:
        raise ExperimentError("the admission artifact claims a result it preceded")
    if plan["family_size"] != STAGE1_FAMILY_SIZE:
        raise ExperimentError("the Stage-1 family size drifted from the frozen plan")

    result = load_result(root)
    committed = (root / REPORT_JSON_PATH).read_bytes().replace(b"\r\n", b"\n")
    if committed != report_bytes(result):
        raise ExperimentError("the research report and the experiment result disagree")
    markdown = (root / REPORT_MARKDOWN_PATH).read_bytes().replace(b"\r\n", b"\n")
    if markdown != markdown_bytes(result):
        raise ExperimentError("the Markdown report is not generated from the committed result")

    if result["experiment_id"] != EXPERIMENT_ID:
        raise ExperimentError("the result carries the wrong experiment identity")
    if result["model_version"] != LINEAR_MODEL_VERSION:
        raise ExperimentError("the result carries the wrong model version")
    if result["features"]["version"] != FEATURE_SET_VERSION:
        raise ExperimentError("the result carries the wrong feature set version")
    if result["features"]["ordered_names"] != list(FEATURE_NAMES):
        raise ExperimentError("the frozen feature order changed after the result")
    if result["preregistration"] != PREREGISTRATION_PATH:
        raise ExperimentError("the result does not point at its own preregistration")

    comparison = result["primary_comparison"]
    if comparison["minimum_important_effect"] != MINIMUM_IMPORTANT_EFFECT:
        raise ExperimentError("the minimum important effect changed after the result")
    inference = prereg["inference"]
    paired = comparison["paired_interval"]
    for key in ("block_length_hours", "replicates", "seed", "alpha"):
        if paired[key] != inference[key]:
            raise ExperimentError(f"the paired {key} drifted from the preregistration")

    pooled = result["candidate"]["pooled_directional"]
    recomputed = advancement_gate(
        float(pooled["coverage"]),
        {name: float(value) for name, value in comparison["fold_coverage"].items()},
        float(comparison["pooled"]["delta"]),
        paired["interval"],
        {name: float(value) for name, value in comparison["fold_deltas"].items()},
    )
    if recomputed != result["advancement_gate"]:
        raise ExperimentError("the advancement gate does not follow from the reported numbers")
    if result["terminal_classification"] not in {ADVANCE, NO_ADVANCE}:
        raise ExperimentError("the terminal classification is not one of the two declared")
    if result["terminal_classification"] != recomputed["terminal_classification"]:
        raise ExperimentError("the terminal classification contradicts the gate")

    budget = result["search_budget"]
    if budget["stage1_configurations_consumed"] != 1:
        raise ExperimentError("this checkpoint may consume exactly one Stage-1 configuration")
    if budget["stage1_configurations_remaining"] != STAGE1_FAMILY_SIZE - 1:
        raise ExperimentError("the Stage-1 remaining budget does not close")
    if any(budget[key] for key in ("hyperparameter_search", "threshold_search", "feature_search")):
        raise ExperimentError("the result claims a search the plan forbids")
    if budget["result_dependent_forks"]:
        raise ExperimentError("a result-dependent fork entered a frozen experiment")

    boundaries = result["boundaries"]
    for key in (
        "external_information_family",
        "post_cutoff_market_data",
        "champion_created",
        "real_money",
        "baselines_v1_results_changed",
        "historical_terminal_classifications_changed",
        "previous_24h_sign_persistence_inverted",
        "outer_evaluation_used_in_fitting",
        "post_result_tuning",
    ):
        if boundaries[key]:
            raise ExperimentError(f"a frozen boundary was crossed: {key}")
    if boundaries["sealed_queries"] != 0:
        raise ExperimentError("the experiment claims a sealed query")

    fits = result["model_fits"]
    folds = len(result["candidate"]["by_fold"])
    if fits != {
        "direction_base": folds,
        "direction_calibration": folds,
        "magnitude": folds,
        "total": 3 * folds,
    }:
        raise ExperimentError("the model-fit accounting does not close")

    labels, fold_record = result["labels"], result["folds"]
    if labels["admissible_labels"] + labels["excluded_total"] != labels["grid_decision_instants"]:
        raise ExperimentError("the label accounting does not close")
    if (
        fold_record["eligible_decision_timestamps"]
        + sum(fold_record["admissible_not_assigned"].values())
        != labels["admissible_labels"]
    ):
        raise ExperimentError("the fold assignment does not cover the admissible labels")
    features = result["features"]
    if (
        features["available_vectors"] + features["unavailable_vectors"]
        != (labels["admissible_labels"])
    ):
        raise ExperimentError("the feature availability accounting does not close")
    if sum(features["unavailability_by_reason"].values()) != features["unavailable_vectors"]:
        raise ExperimentError("the typed feature exclusions do not sum to the total")

    for name, record in result["candidate"]["by_fold"].items():
        directional = record["directional"]
        total = (
            directional["actionable_directional_predictions"]
            + directional["declared_side_on_neutral_truth"]
            + directional["abstentions"]
        )
        if total != directional["eligible_decision_timestamps"]:
            raise ExperimentError(f"{name}: the directional sample accounting does not close")
        if directional["brier_score"] is None or not directional["reliability_table"]:
            raise ExperimentError(f"{name}: a probabilistic candidate lost its calibration")
        universe = record["magnitude_universe"]
        if (
            universe["feature_available_rows_scored"]
            + universe["abstained_rows_excluded_and_counted"]
            != universe["eligible_decision_timestamps"]
        ):
            raise ExperimentError(f"{name}: the magnitude universe accounting does not close")

    context = result["baseline_context"]
    baseline_report = json.loads((root / context["source"]).read_text(encoding="utf-8"))
    if context["reference_bar"] != baseline_report["baselines"][ALWAYS_UP]["pooled"]["win_rate"]:
        raise ExperimentError("the quoted reference bar is not the committed baseline")

    if data_available:
        replayed = report_bytes(run_experiment(root))
        if replayed != report_bytes(result):
            raise ExperimentError("the committed experiment result is not what the code recomputes")
        findings["data_replayed"] = True

    findings["terminal_classification"] = result["terminal_classification"]
    findings["stage1_configurations_consumed"] = budget["stage1_configurations_consumed"]
    return findings


__all__ = [
    "build_markdown",
    "load_result",
    "markdown_bytes",
    "report_bytes",
    "validate_internal_structure",
]
