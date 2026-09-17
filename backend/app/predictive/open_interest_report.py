"""Deterministic reporting and validation for `PREDICTIVE-STAGE2-OPEN-INTEREST-V1`.

The JSON result is the truth. The Markdown is generated from it, and the validator re-derives
all seven advancement conditions for both configurations from the reported numbers instead of
trusting the classification strings written beside them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .baselines import ALWAYS_UP, PREVIOUS_24H_SIGN_PERSISTENCE, ZERO_RETURN_MAGNITUDE
from .internal_structure import ExperimentError, canonical_bytes
from .open_interest import (
    ADMISSION_PATH,
    ADVANCE,
    CONFIGURATION_ORDER,
    EXPERIMENT_IDS,
    FAMILY,
    FAMILY_REJECTED,
    FAMILY_SIGNAL,
    FAMILY_SIZE,
    GATE_NAMES,
    MINIMUM_IMPORTANT_EFFECT,
    NO_ADVANCE,
    NOT_ELIGIBLE,
    PAIRED_SEED,
    REPORT_JSON_PATH,
    REPORT_MARKDOWN_PATH,
    SEARCH_PLAN_PATH,
    admission,
    advancement_gate,
    director_decisions,
    preregistration,
    preregistration_path,
    required_non_negative_folds,
    result_path,
    run_experiment,
    search_plan,
    trials_path,
)
from .open_interest_audit import AUDIT_PATH, PASS
from .open_interest_source import FEATURE_NAMES, FEATURE_SET_VERSION

ROOT = Path(__file__).resolve().parents[3]

CALIBRATION_CONTROL = "TRAINING_UP_BASE_RATE"


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
    lines: list[str] = []
    disposition = result["family_disposition"]
    source = result["source"]
    features = result["features"]
    folds = result["folds"]

    lines.append("# Predictive Stage 2 — open interest V1")
    lines.append("")
    lines.append(
        f"`{result['family']}`, the second Stage-2 information family of "
        f"`{result['research_generation']}`: whether the **quantity** of leveraged BTCUSDT "
        "perpetual positioning carries 24h directional information."
    )
    lines.append("")
    lines.append(
        f"Family disposition: **{disposition['disposition']}**. Configurations executed: "
        f"{result['search_budget']['configurations_consumed']} of "
        f"{result['search_budget']['configurations_planned']}; "
        f"{result['search_budget']['configurations_remaining']} remaining."
    )
    lines.append("")
    lines.append("## Source, provenance and point-in-time semantics")
    lines.append("")
    lines.append(
        f"`{source['manifest_id']}`: {source['records']} records from "
        f"{source['first_record']} to {source['last_record']}, "
        f"{source['archive_days']} official daily objects, every one verified against the "
        f"archive's own checksum (`{source['official_checksums_verified']}` verified). "
        f"Source `{source['source']}`, class `{source['source_class']}`, credential-free. "
        f"No third-party vendor, no REST snapshot history, no reconstruction or backfill."
    )
    lines.append("")
    lines.append(
        "Fields read: "
        + ", ".join(f"`{name}`" for name in source["fields_read"])
        + f". `sum_open_interest_value` is excluded because notional embeds BTC price, and "
        "every long/short, top-trader and taker ratio column is excluded. Availability rule "
        f"`{source['availability_rule']}` with a "
        f"{source['maximum_state_age_seconds'] // 60}-minute staleness bound — a record "
        "stamped exactly at the decision instant is unavailable, and there is no "
        "interpolation or forward fill."
    )
    lines.append("")
    lines.append(
        f"Source audit `{result['source_audit_status']}`. Included folds "
        f"{', '.join(folds['included_folds'])}; excluded candidate folds "
        f"{', '.join(folds['excluded_candidate_folds']) or 'none'}. The fold set is the "
        f"deterministic output of the pre-result source audit "
        f"(`{folds['fold_selection']}`), and no return value entered that choice "
        f"(`fold_selection_used_return_values: "
        f"{str(folds['fold_selection_used_return_values']).lower()}`)."
    )
    lines.append("")
    lines.append(
        f"`{features['version']}`, {features['count']} features: "
        + ", ".join(f"`{name}`" for name in features["ordered_names"])
        + f". {features['available_vectors']} available vectors, "
        f"{features['unavailable_vectors']} unavailable and typed: "
        + ", ".join(
            f"`{name}` {count}"
            for name, count in sorted(features["unavailability_by_reason"].items())
        )
        + "."
    )
    lines.append("")

    for model_version in CONFIGURATION_ORDER:
        configuration = result["configurations"][model_version]
        pooled = configuration["candidate"]["pooled_directional"]
        magnitude = configuration["candidate"]["pooled_magnitude"]
        primary = configuration["primary_comparison"]
        base_rate = configuration["base_rate_comparison"]
        paired = primary["paired_interval"]
        gate = configuration["advancement_gate"]
        controls = configuration["controls"]

        lines.append(f"## {model_version}")
        lines.append("")
        lines.append(
            f"`{configuration['experiment_id']}` — `{configuration['hypothesis_id']}`. "
            f"Terminal classification: **{configuration['terminal_classification']}**."
        )
        lines.append("")
        lines.append(
            f"Pooled win rate **{_number(pooled['win_rate'])}** on "
            f"{pooled['actionable_directional_predictions']} actionable predictions at "
            f"coverage {_number(pooled['coverage'], 5)} over "
            f"{pooled['eligible_decision_timestamps']} eligible decision timestamps, with "
            f"{pooled['abstentions']} counted abstentions and "
            f"{pooled['declared_side_on_neutral_truth']} declared sides on NEUTRAL truth."
        )
        lines.append("")
        lines.append(
            f"Matched `{ALWAYS_UP}` on the identical timestamps "
            f"**{_number(primary['matched_always_up_win_rate'])}**; primary delta "
            f"**{_signed(primary['pooled_delta'])}** against a minimum important effect of "
            f"{_signed(MINIMUM_IMPORTANT_EFFECT, 3)}, paired "
            f"{100 * paired['interval_mass']:g}% interval "
            f"[{_signed(paired['interval'][0])}, {_signed(paired['interval'][1])}] "
            f"at alpha {paired['alpha']}, seed {paired['seed']}."
        )
        lines.append("")
        lines.append(
            f"Matched `{CALIBRATION_CONTROL}` win rate "
            f"{_number(base_rate['matched_win_rate'])} and Brier "
            f"{_number(base_rate['matched_brier_score'])}; the candidate's Brier is "
            f"{_number(base_rate['candidate_brier_score'])}. Matched "
            f"`{PREVIOUS_24H_SIGN_PERSISTENCE}` "
            f"{_number(controls[PREVIOUS_24H_SIGN_PERSISTENCE]['win_rate'])} at coverage "
            f"{_number(controls[PREVIOUS_24H_SIGN_PERSISTENCE]['coverage'], 5)} "
            "(descriptive only, never inverted)."
        )
        lines.append("")
        lines.append(
            "| fold | eligible | actionable | abstentions | coverage | candidate | "
            f"{ALWAYS_UP} | delta |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for name in folds["included_folds"]:
            record = configuration["candidate"]["by_fold"][name]
            directional = record["directional"]
            lines.append(
                f"| {name} | {directional['eligible_decision_timestamps']} | "
                f"{directional['actionable_directional_predictions']} | "
                f"{directional['abstentions']} | "
                f"{_number(directional['coverage'], 5)} | "
                f"{_number(directional['win_rate'])} | "
                f"{_number(record['controls'][ALWAYS_UP]['win_rate'])} | "
                f"{_signed(record['delta_versus_always_up'])} |"
            )
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
        universe = configuration["candidate"]["pooled_magnitude_universe"]
        zero_magnitude = controls[ZERO_RETURN_MAGNITUDE]
        exclusions = magnitude["magnitude_match_exclusions"]
        lines.append(
            f"Magnitude MAE **{_number(magnitude['magnitude_mae_percentage_points'])} pp** "
            f"({_number(magnitude['magnitude_mae_basis_points'], 2)} bps), median absolute "
            f"error {_number(magnitude['magnitude_median_absolute_error_percentage_points'])} "
            f"pp over {universe['source_eligible_rows_scored']} source-eligible rows; "
            f"{universe['abstained_rows_excluded_and_counted']} abstained rows declare no "
            f"magnitude and are excluded and counted. Matched `{ZERO_RETURN_MAGNITUDE}` "
            f"{_number(zero_magnitude['magnitude_mae_percentage_points'])} pp. Signed "
            f"magnitude-match mean {_number(magnitude['magnitude_match_mean'], 2)} over "
            f"{magnitude['magnitude_match_included']} included records; exclusions "
            + ", ".join(f"`{name}` {count}" for name, count in sorted(exclusions.items()))
            + "."
        )
        lines.append("")
        lines.append("| condition | threshold | observed | passed |")
        lines.append("| --- | --- | --- | --- |")
        for name in GATE_NAMES:
            condition = gate["conditions"][name]
            threshold = condition["threshold"]
            rendered = (
                _number(threshold, 5) if isinstance(threshold, int | float) else str(threshold)
            )
            lines.append(
                f"| `{name}` | {rendered} | {_number(condition['observed'], 5)} | "
                f"{'yes' if condition['passed'] else 'no'} |"
            )
        lines.append("")
        if gate["failed_conditions"]:
            lines.append(
                "Failed conditions: "
                + ", ".join(f"`{name}`" for name in gate["failed_conditions"])
                + ". Magnitude MAE and the signed magnitude-match diagnostic are mandatory "
                "companions and never rescue a failed directional gate."
            )
        else:
            lines.append("Every predeclared condition holds.")
        lines.append("")
        fits = configuration["model_fits"]
        lines.append(
            f"Model fits {fits['total']}: {fits['direction_base']} direction base, "
            f"{fits['direction_calibration']} training-only Platt calibration, "
            f"{fits['magnitude']} magnitude."
        )
        lines.append("")

    lines.append("## Family disposition")
    lines.append("")
    lines.append(
        f"Both configurations were executed as preregistered and neither was chosen post hoc "
        f"(`post_hoc_winner_selected: "
        f"{str(disposition['post_hoc_winner_selected']).lower()}`). Family "
        f"`{disposition['disposition']}`. Sealed eligibility: "
        + ", ".join(
            f"`{experiment}` {value}"
            for experiment, value in sorted(disposition["sealed_eligibility"].items())
        )
        + "."
    )
    lines.append("")
    lines.append("## Accounting")
    lines.append("")
    lines.append(
        f"Base-rate controls refit per fold: {result['base_rate_control_fits']['fits']} "
        f"(`{result['base_rate_control_fits']['classification']}`). Sealed queries "
        f"{result['boundaries']['sealed_queries']}. Champion NONE. Real money "
        f"{str(result['boundaries']['real_money']).lower()}. No asset-universe expansion, no "
        "additional information family, no combination with the rejected Stage-1 or funding "
        "features, no Stage-1 substrate repair, no post-cutoff data. Every prior predictive "
        "experiment result is unchanged."
    )
    lines.append("")
    return "\n".join(lines)


def report_bytes(result: dict[str, Any]) -> bytes:
    return canonical_bytes(result)


def markdown_bytes(result: dict[str, Any]) -> bytes:
    return build_markdown(result).encode("utf-8")


def configuration_result_document(result: dict[str, Any], model_version: str) -> dict[str, Any]:
    """The immutable per-experiment record, carved out of the shared run."""
    configuration = dict(result["configurations"][model_version])
    configuration.pop("trials")
    return {
        "version": result["version"],
        "classification": "PREDICTIVE_EXPERIMENT_RESULT",
        "experiment_id": EXPERIMENT_IDS[model_version],
        "family": result["family"],
        "hypothesis_id": configuration["hypothesis_id"],
        "research_generation": result["research_generation"],
        "evaluation_contract": result["evaluation_contract"],
        "evaluation_contract_amendment": result["evaluation_contract_amendment"],
        "preregistration": preregistration_path(model_version),
        "search_plan": result["search_plan"],
        "admission": result["admission"],
        "source_audit": result["source_audit"],
        "source": result["source"],
        "labels": result["labels"],
        "folds": result["folds"],
        "features": result["features"],
        "base_rate_control_fits": result["base_rate_control_fits"],
        "configuration": configuration,
        "baseline_context": result["baseline_context"],
        "terminal_classification": configuration["terminal_classification"],
        "family_disposition": result["family_disposition"],
        "search_budget": result["search_budget"],
        "scoring": result["scoring"],
        "boundaries": result["boundaries"],
    }


def trials_document(result: dict[str, Any], model_version: str) -> list[dict[str, Any]]:
    return list(result["configurations"][model_version]["trials"])


def load_result(root: Path = ROOT) -> dict[str, Any]:
    return json.loads((root / REPORT_JSON_PATH).read_text(encoding="utf-8"))


def validate_open_interest(root: Path = ROOT, *, data_available: bool = False) -> dict[str, Any]:
    """Check the committed experiments against their frozen records, and the data if present."""
    findings: dict[str, Any] = {"status": "PASS", "data_replayed": False}

    plan = json.loads((root / SEARCH_PLAN_PATH).read_text(encoding="utf-8"))
    admitted = json.loads((root / ADMISSION_PATH).read_text(encoding="utf-8"))
    audit = json.loads((root / AUDIT_PATH).read_text(encoding="utf-8"))
    if plan != search_plan():
        raise ExperimentError("the committed search plan drifted from the code")
    if admitted != admission(root):
        raise ExperimentError("the admission artifact no longer matches the frozen files")
    if admitted["status"] != "PASS":
        raise ExperimentError("the pre-execution admission gate did not pass")
    if admitted["model_fits_executed"] or admitted["market_results_observed"]:
        raise ExperimentError("the admission artifact claims a result it preceded")
    if audit["status"] != PASS:
        raise ExperimentError("the source audit did not pass its own gates")
    if audit["target_bearing_model_fitted"]:
        raise ExperimentError("the source audit claims a model fit it must precede")
    if audit["coverage"]["return_values_inspected"]:
        raise ExperimentError("the fold selection inspected return values")
    if admitted["director_decisions"] != director_decisions():
        raise ExperimentError("the admitted Research Director decisions drifted from the code")
    if plan["family_size"] != FAMILY_SIZE or len(plan["configurations"]) != FAMILY_SIZE:
        raise ExperimentError("the family size drifted from the frozen plan")
    if plan["inference"]["seed"] != PAIRED_SEED:
        raise ExperimentError("the family's paired bootstrap seed drifted")

    for model_version in CONFIGURATION_ORDER:
        committed = json.loads(
            (root / preregistration_path(model_version)).read_text(encoding="utf-8")
        )
        if committed != preregistration(model_version, root):
            raise ExperimentError(f"{model_version}: the preregistration drifted from the code")

    result = load_result(root)
    committed_bytes = (root / REPORT_JSON_PATH).read_bytes().replace(b"\r\n", b"\n")
    if committed_bytes != report_bytes(result):
        raise ExperimentError("the research report is not canonical bytes of its own content")
    markdown = (root / REPORT_MARKDOWN_PATH).read_bytes().replace(b"\r\n", b"\n")
    if markdown != markdown_bytes(result):
        raise ExperimentError("the Markdown report is not generated from the committed result")

    if result["family"] != FAMILY:
        raise ExperimentError("the result carries the wrong family identity")
    if result["features"]["version"] != FEATURE_SET_VERSION:
        raise ExperimentError("the result carries the wrong feature set version")
    if result["features"]["ordered_names"] != list(FEATURE_NAMES):
        raise ExperimentError("the frozen feature order changed after the result")
    if result["features"]["price_derived_feature_present"]:
        raise ExperimentError("a price-derived feature entered the open-interest family")
    if result["features"]["combined_with_rejected_families"]:
        raise ExperimentError("the family was combined with a rejected family")
    if result["folds"]["included_folds"] != admitted["included_folds"]:
        raise ExperimentError("the included folds are not the audited source-admissible set")
    if result["source"]["open_interest_value_admitted"]:
        raise ExperimentError("the notional column was admitted")
    if result["source"]["post_cutoff_records"]:
        raise ExperimentError("the source claims a post-cutoff record")

    labels = result["labels"]
    if labels["admissible_labels"] + labels["excluded_total"] != labels["grid_decision_instants"]:
        raise ExperimentError("the label accounting does not close")
    features = result["features"]
    if (
        features["available_vectors"] + features["unavailable_vectors"]
        != (labels["admissible_labels"])
    ):
        raise ExperimentError("the open-interest availability accounting does not close")

    advancing: list[str] = []
    for model_version in CONFIGURATION_ORDER:
        configuration = result["configurations"][model_version]
        pooled = configuration["candidate"]["pooled_directional"]
        primary = configuration["primary_comparison"]
        base_rate = configuration["base_rate_comparison"]
        paired = primary["paired_interval"]
        prereg = preregistration(model_version, root)

        if configuration["experiment_id"] != EXPERIMENT_IDS[model_version]:
            raise ExperimentError(f"{model_version}: wrong experiment identity")
        if primary["minimum_important_effect"] != MINIMUM_IMPORTANT_EFFECT:
            raise ExperimentError(f"{model_version}: the MESI changed after the result")
        for key in ("block_length_hours", "replicates", "seed", "alpha"):
            if paired[key] != prereg["inference"][key]:
                raise ExperimentError(f"{model_version}: the paired {key} drifted")

        recomputed = advancement_gate(
            model_version,
            float(pooled["coverage"]),
            {name: float(value) for name, value in primary["fold_coverage"].items()},
            float(primary["pooled_delta"]),
            paired["interval"],
            float(primary["candidate_win_rate"]),
            float(base_rate["matched_win_rate"]),
            float(base_rate["candidate_brier_score"]),
            float(base_rate["matched_brier_score"]),
            {name: float(value) for name, value in primary["fold_deltas"].items()},
        )
        if recomputed != configuration["advancement_gate"]:
            raise ExperimentError(
                f"{model_version}: the gate does not follow from the reported numbers"
            )
        if configuration["terminal_classification"] not in {
            ADVANCE[model_version],
            NO_ADVANCE[model_version],
        }:
            raise ExperimentError(f"{model_version}: undeclared terminal classification")
        if configuration["terminal_classification"] != recomputed["terminal_classification"]:
            raise ExperimentError(f"{model_version}: the classification contradicts the gate")
        if recomputed["magnitude_used_to_rescue"]:
            raise ExperimentError(f"{model_version}: magnitude was used to rescue the gate")
        expected_required = required_non_negative_folds(len(result["folds"]["included_folds"]))
        if recomputed["required_non_negative_folds"] != expected_required:
            raise ExperimentError(f"{model_version}: the two-thirds fold rule drifted")

        fits = configuration["model_fits"]
        count = len(configuration["candidate"]["by_fold"])
        if count != len(result["folds"]["included_folds"]):
            raise ExperimentError(f"{model_version}: wrong number of included folds")
        if fits != {
            "direction_base": count,
            "direction_calibration": count,
            "magnitude": count,
            "total": 3 * count,
        }:
            raise ExperimentError(f"{model_version}: the model-fit accounting does not close")

        for name, record in configuration["candidate"]["by_fold"].items():
            directional = record["directional"]
            total = (
                directional["actionable_directional_predictions"]
                + directional["declared_side_on_neutral_truth"]
                + directional["abstentions"]
            )
            if total != directional["eligible_decision_timestamps"]:
                raise ExperimentError(f"{model_version}/{name}: sample accounting does not close")
            if directional["brier_score"] is None or not directional["reliability_table"]:
                raise ExperimentError(f"{model_version}/{name}: lost its calibration")
            if (
                record["controls"][ALWAYS_UP]["eligible_decision_timestamps"]
                != (record["matched_universe"]["records"])
            ):
                raise ExperimentError(
                    f"{model_version}/{name}: a control was scored on a different universe"
                )

        document = json.loads((root / result_path(model_version)).read_text(encoding="utf-8"))
        if document != configuration_result_document(result, model_version):
            raise ExperimentError(f"{model_version}: the experiment record disagrees with the run")
        trials = json.loads((root / trials_path(model_version)).read_text(encoding="utf-8"))
        if trials != trials_document(result, model_version):
            raise ExperimentError(f"{model_version}: the trials record disagrees with the run")
        if len(trials) != len(result["folds"]["included_folds"]):
            raise ExperimentError(f"{model_version}: one trial per included fold is required")

        if not recomputed["failed_conditions"]:
            advancing.append(model_version)

    disposition = result["family_disposition"]
    expected = FAMILY_SIGNAL if advancing else FAMILY_REJECTED
    if disposition["disposition"] != expected:
        raise ExperimentError("the family disposition does not follow from the two gates")
    if disposition["post_hoc_winner_selected"]:
        raise ExperimentError("a winner was selected post hoc")
    if disposition["sealed_queried"] or disposition["champion_created"]:
        raise ExperimentError("the family disposition claims a sealed query or a Champion")
    if disposition["descendant_tuned"] or disposition["prospective_observer_created"]:
        raise ExperimentError("the family disposition claims an unauthorized follow-on")
    if not advancing:
        for experiment, value in disposition["sealed_eligibility"].items():
            if value != NOT_ELIGIBLE:
                raise ExperimentError(f"{experiment}: a rejected family may not be sealed-eligible")

    budget = result["search_budget"]
    if budget["configurations_consumed"] != FAMILY_SIZE or budget["configurations_remaining"] != 0:
        raise ExperimentError("the family budget does not close")
    if budget["result_dependent_early_stop"] or budget["result_dependent_forks"]:
        raise ExperimentError("a result-dependent decision entered a frozen family")
    if any(budget[key] for key in ("hyperparameter_search", "threshold_search", "feature_search")):
        raise ExperimentError("the result claims a search the plan forbids")

    boundaries = result["boundaries"]
    for key in (
        "asset_universe_expanded",
        "additional_information_family",
        "combined_with_rejected_families",
        "stage1_substrate_repair",
        "post_cutoff_market_data",
        "champion_created",
        "real_money",
        "historical_results_changed",
        "baselines_v1_results_changed",
        "previous_24h_sign_persistence_inverted",
        "outer_evaluation_used_in_fitting",
        "post_result_tuning",
        "post_hoc_winner_selection",
    ):
        if boundaries[key]:
            raise ExperimentError(f"a frozen boundary was crossed: {key}")
    if boundaries["sealed_queries"] != 0:
        raise ExperimentError("the experiment claims a sealed query")

    if data_available:
        replayed = report_bytes(run_experiment(root))
        if replayed != report_bytes(result):
            raise ExperimentError("the committed result is not what the code recomputes")
        findings["data_replayed"] = True

    findings["family_disposition"] = disposition["disposition"]
    findings["included_folds"] = list(result["folds"]["included_folds"])
    findings["classifications"] = {
        model_version: result["configurations"][model_version]["terminal_classification"]
        for model_version in CONFIGURATION_ORDER
    }
    return findings


__all__ = [
    "build_markdown",
    "configuration_result_document",
    "load_result",
    "markdown_bytes",
    "report_bytes",
    "trials_document",
    "validate_open_interest",
]
