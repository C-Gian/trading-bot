"""Reporting and deterministic replay for the V2 internal-structure selective family."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .internal_selective import (
    ADMISSION_PATH,
    CONFIGURATION_ORDER,
    PREREGISTRATION_PATHS,
    REPORT_JSON_PATH,
    RESULT_PATHS,
    SEARCH_PLAN_PATH,
    TRIAL_PATHS,
    InternalSelectiveExperimentError,
    admission,
    admission_identity,
    canonical_bytes,
    family_summary,
    preregistration,
    run_family,
    search_plan,
)

ROOT = Path(__file__).resolve().parents[3]


def _number(value: Any, digits: int = 6) -> str:
    return "n/a" if value is None else f"{float(value):.{digits}f}"


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Predictive V2 internal structure selective V1",
        "",
        f"Family disposition: **{report['family_disposition']}**.",
        "",
        (
            "The eighteen causal internal features are inherited unchanged from the frozen "
            "Generation V1 definition and reconciled against it; the 169-hour availability "
            "rule is reused, not repaired. No V1 fitted model, probability, score tail or "
            "reliability bin was read. Magnitude is deferred, sealed queries are 0, Champion "
            "is `NONE`, and real money is false."
        ),
        "",
        "## Configuration results",
        "",
        (
            "| configuration | feature-valid N | coverage | actionable N | action coverage "
            "| selective win rate | full-fold UP | enrichment | 97.5% interval "
            "| classification |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for model in CONFIGURATION_ORDER:
        record = report["configuration_results"][model]
        candidate = record["candidate"]
        availability = record["feature_availability"]
        interval = record["primary_inference"]["interval"]
        lines.append(
            f"| `{model}` | {availability['feature_valid_timestamps']} | "
            f"{_number(availability['pooled_feature_valid_coverage'])} | "
            f"{candidate['actionable_long_predictions']} | "
            f"{_number(candidate['action_coverage'])} | "
            f"{_number(candidate['selective_long_win_rate'])} | "
            f"{_number(candidate['full_fold_up_rate'])} | "
            f"{_number(candidate['enrichment'])} | "
            f"[{_number(interval[0])}, {_number(interval[1])}] | "
            f"`{record['terminal_classification']}` |"
        )
    for model in CONFIGURATION_ORDER:
        record = report["configuration_results"][model]
        candidate = record["candidate"]
        availability = record["feature_availability"]
        interval = record["primary_inference"]
        gate = record["advancement_gate"]
        lines.extend(
            [
                "",
                f"## {model}",
                "",
                (
                    f"Pooled feature-valid UP rate "
                    f"`{_number(availability['pooled_feature_valid_fold_up_rate'])}` over "
                    f"`{availability['feature_valid_directionally_scorable_timestamps']}` "
                    f"feature-valid scorable rows; pooled full-fold UP rate "
                    f"`{_number(candidate['full_fold_up_rate'])}`."
                ),
                "",
                (
                    f"Full-probability Brier "
                    f"`{_number(candidate['full_probability_brier'], 9)}`; matched "
                    f"training-base-rate Brier "
                    f"`{_number(candidate['matched_training_up_base_rate_brier'], 9)}`. "
                    f"Action mean p_up "
                    f"`{_number(candidate['mean_predicted_p_up_on_actions'], 9)}`; empirical "
                    f"LONG win rate `{_number(candidate['selective_long_win_rate'], 9)}`; "
                    f"calibration gap `{_number(candidate['action_calibration_gap'], 9)}`."
                ),
                "",
                (
                    f"Bootstrap retained `{interval['retained_replicates']}` and discarded "
                    f"`{interval['discarded_replicates_without_an_actionable_long']}` "
                    f"(`{_number(interval['discarded_replicate_share'], 6)}`); support "
                    f"`{interval['resample_support']}`."
                ),
                "",
                (
                    "| fold | feature-valid N | feature-valid coverage | LONG N "
                    "| action coverage | win rate | full-fold UP | feature-valid UP "
                    "| enrichment |"
                ),
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for fold, values in candidate["by_fold"].items():
            available = availability["by_fold"][fold]
            lines.append(
                f"| {fold} | {available['feature_valid_timestamps']} | "
                f"{_number(available['feature_valid_coverage'])} | "
                f"{values['actionable_long_predictions']} | "
                f"{_number(values['action_coverage'])} | "
                f"{_number(values['selective_long_win_rate'])} | "
                f"{_number(values['full_fold_up_rate'])} | "
                f"{_number(values['feature_valid_fold_up_rate'])} | "
                f"{_number(values['enrichment'])} |"
            )
        lines.extend(["", "Advancement gates:", ""])
        for name, condition in gate["conditions"].items():
            lines.append(
                f"- `{name}`: {'PASS' if condition['passed'] else 'FAIL'} "
                f"(observed `{condition['observed']}`, threshold `{condition['threshold']}`)."
            )
        lines.extend(["", "Actionable reliability bins:", ""])
        for bucket in candidate["action_reliability_table"]:
            lines.append(
                f"- `{bucket['bin']}`: n={bucket['count']}, "
                f"mean_p={bucket['mean_predicted_probability']}, "
                f"empirical={bucket['empirical_frequency_correct']}."
            )
    lines.extend(
        [
            "",
            "## Integrity and boundaries",
            "",
            (
                f"Admission identity: `{report['admission_identity_sha256']}`. Both planned "
                "configurations were consumed; none remains and no fork was taken. The ten "
                "Generation V1 result files, the two first-family V2 result files and the "
                "V2 calendar family report all replay byte-identically. No V1 model output "
                "was loaded and the Stage-1 substrate debt remains unrepaired."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def report_bytes(report: dict[str, Any]) -> bytes:
    return canonical_bytes(report)


def markdown_bytes(report: dict[str, Any]) -> bytes:
    return build_markdown(report).encode("utf-8")


def load_results(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    return {
        model: json.loads((root / RESULT_PATHS[model]).read_text(encoding="utf-8"))
        for model in CONFIGURATION_ORDER
    }


def validate_internal_selective(root: Path = ROOT, *, data_available: bool) -> dict[str, Any]:
    """Validate immutable inputs and optionally replay the entire family byte-for-byte."""
    stored_admission = json.loads((root / ADMISSION_PATH).read_text(encoding="utf-8"))
    if stored_admission != admission(root):
        raise InternalSelectiveExperimentError("the admission no longer matches the frozen files")
    if json.loads((root / SEARCH_PLAN_PATH).read_text(encoding="utf-8")) != search_plan():
        raise InternalSelectiveExperimentError("the search plan no longer matches the design")
    for model in CONFIGURATION_ORDER:
        stored = json.loads((root / PREREGISTRATION_PATHS[model]).read_text(encoding="utf-8"))
        if stored != preregistration(model):
            raise InternalSelectiveExperimentError(f"{model}: preregistration mismatch")

    results = load_results(root)
    report = family_summary(results)
    if canonical_bytes(report) != (root / REPORT_JSON_PATH).read_bytes():
        raise InternalSelectiveExperimentError("the family report does not match the results")
    identities = {
        results[model]["integrity"]["admission_identity_sha256"] for model in CONFIGURATION_ORDER
    }
    if identities != {admission_identity(root)}:
        raise InternalSelectiveExperimentError("the result admission identity is not current")

    replayed = False
    if data_available:
        replay = run_family(root)
        for model in CONFIGURATION_ORDER:
            replay_result, replay_trials = replay[model]
            if canonical_bytes(replay_result) != (root / RESULT_PATHS[model]).read_bytes():
                raise InternalSelectiveExperimentError(f"{model}: result replay is not identical")
            if canonical_bytes(replay_trials) != (root / TRIAL_PATHS[model]).read_bytes():
                raise InternalSelectiveExperimentError(f"{model}: trial replay is not identical")
        replayed = True
    return {
        "status": "PASS",
        "data_replayed": replayed,
        "deterministic_result_replay": "PASS_BYTE_IDENTICAL" if replayed else "NOT_REQUESTED",
        "family_disposition": report["family_disposition"],
        "terminal_classifications": {
            model: results[model]["terminal_classification"] for model in CONFIGURATION_ORDER
        },
        "admission_identity_sha256": admission_identity(root),
    }


__all__ = [
    "build_markdown",
    "load_results",
    "markdown_bytes",
    "report_bytes",
    "validate_internal_selective",
]
