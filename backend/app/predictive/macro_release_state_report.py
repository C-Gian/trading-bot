"""Deterministic reporting and validation for `PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1`.

The JSON result is the truth. The Markdown is generated from it, and the validator re-derives
all seven advancement conditions for both configurations from the reported numbers instead of
trusting the classification strings written beside them. It also re-checks that the frozen
predecessor records named by the admission still hash to what the admission recorded, so this
checkpoint cannot quietly edit the source block it descends from.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .baselines import PREVIOUS_24H_SIGN_PERSISTENCE
from .internal_structure import ExperimentError, canonical_bytes, content_hash
from .macro_release_state import (
    ABSOLUTE_REFERENCE,
    ADMISSION_PATH,
    ADVANCE,
    CONFIGURATION_ORDER,
    EXPERIMENT_IDS,
    FAMILY,
    FAMILY_REJECTED,
    FAMILY_SIGNAL,
    FAMILY_SIZE,
    GATE_NAMES,
    MATCHED_CONTROL,
    MINIMUM_IMPORTANT_EFFECT,
    NO_ADVANCE,
    NOT_ELIGIBLE,
    PAIRED_SEED,
    PREDECESSOR_CHECKPOINT,
    PREDECESSOR_RECORDS,
    PRIOR_EXPERIMENT_RESULTS,
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
from .macro_release_state_audit import AUDIT_PATH, PASS
from .macro_release_state_source import FEATURE_NAMES, FEATURE_SET_VERSION

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
    lines: list[str] = []
    disposition = result["family_disposition"]
    source = result["source"]
    features = result["features"]
    folds = result["folds"]
    integrity = result["source_cadence_integrity"]
    persistence = result["release_state_accounting"]

    lines.append("# Predictive Stage 3 — macro release state V1")
    lines.append("")
    lines.append(
        f"`{result['family']}`, the one authorized prospective source-semantics remediation of "
        f"the ALFRED macro information family inside `{result['research_generation']}`: whether "
        "strict point-in-time U.S. macro and financial-condition release state carries 24h "
        "directional information about BTCUSDT."
    )
    lines.append("")
    lines.append(
        f"Family disposition: **{disposition['disposition']}**. Configurations executed: "
        f"{result['search_budget']['configurations_consumed']} of "
        f"{result['search_budget']['configurations_planned']}; "
        f"{result['search_budget']['configurations_remaining']} remaining. Source-semantics "
        f"versions consumed: {result['search_budget']['source_semantics_versions_consumed']} of "
        f"{result['search_budget']['source_semantics_versions_authorized']}; "
        f"{result['search_budget']['source_semantics_versions_remaining']} remaining."
    )
    lines.append("")
    lines.append("## The predecessor, and what changed")
    lines.append("")
    lines.append(
        f"`{PREDECESSOR_CHECKPOINT}` stays exactly as it was recorded: disposition "
        f"`{result['predecessor']['disposition']}`, {result['predecessor']['model_fits']} model "
        f"fits, {result['predecessor']['outer_predictions']} outer predictions, "
        f"{result['predecessor']['configurations_consumed']} configurations consumed. It is not "
        f"reclassified (`reclassified: {str(result['predecessor']['reclassified']).lower()}`) and "
        f"its records are unmodified (`records_modified: "
        f"{str(result['predecessor']['records_modified']).lower()}`), which the admission proves "
        "by hash."
    )
    lines.append("")
    lines.append(
        "The predecessor judged a current level stale when its *observation period* date was "
        "more than a fixed number of days older than the decision date. A monthly release "
        "describes a month that closed before it was published, so that rule discarded the "
        "genuinely latest-known CPI for most of every month. This contract keeps strict "
        "availability and replaces the per-decision expiry with state persistence: the current "
        f"known level is the value on the greatest observation date in the as-of-`T` snapshot "
        f"(`{source['current_state_rule']}`), and it persists until a newer observation becomes "
        f"available. `current_state_expiry_relative_to_decision_time: "
        f"{str(source['current_state_expiry_relative_to_decision_time']).lower()}`; "
        f"`interpolation: {str(source['interpolation']).lower()}`; "
        f"`nearest_future_substitution: {str(source['nearest_future_substitution']).lower()}`; "
        f"`current_revised_substitution: "
        f"{str(source['current_revised_substitution']).lower()}`; post-2024 vintages "
        f"{source['post_2024_vintages']}."
    )
    lines.append("")
    lines.append("## Source identity and release-calendar integrity")
    lines.append("")
    lines.append(
        f"`{source['manifest_id']}`, the same hash-pinned substrate the blocked predecessor "
        f"used: `{source['substrate_artifact']}`, {source['substrate_rows']} vintage rows over "
        f"the eight frozen series {', '.join(f'`{name}`' for name in source['series'])}, "
        f"availability rule `{source['availability_rule']}`."
    )
    lines.append("")
    lines.append(
        "Persistence is only safe if the release calendar itself is not frozen, so the audit "
        "walks the observation-date sequence of every series before any outcome is read."
    )
    lines.append("")
    lines.append("| series | frequency | observation dates | max gap (days) | limit | passed |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for name, record in sorted(integrity["by_series"].items()):
        lines.append(
            f"| `{name}` | {record['frequency']} | {record['observation_dates']} | "
            f"{record['maximum_observation_gap_days']} | "
            f"{record['maximum_allowed_gap_days']} | "
            f"{'yes' if record['passed'] else 'no'} |"
        )
    lines.append("")
    lines.append(
        f"Source audit `{result['source_audit_status']}`. Included folds "
        f"{', '.join(folds['included_folds'])}; excluded candidate folds "
        f"{', '.join(folds['excluded_candidate_folds']) or 'none'}. The fold set is the "
        f"deterministic output of the pre-result source audit (`{folds['fold_selection']}`), and "
        f"no return value entered that choice (`fold_selection_used_return_values: "
        f"{str(folds['fold_selection_used_return_values']).lower()}`)."
    )
    lines.append("")
    lines.append(
        f"`{features['version']}` supersedes `{features['supersedes']}` and holds the same "
        f"{features['count']} economic quantities in the same order "
        f"(`identical_quantities_and_order_to_v1: "
        f"{str(features['identical_quantities_and_order_to_v1']).lower()}`): "
        + ", ".join(f"`{name}`" for name in features["ordered_names"])
        + f". {features['available_vectors']} available vectors, "
        f"{features['unavailable_vectors']} unavailable and typed: "
        + ", ".join(
            f"`{name}` {count}"
            for name, count in sorted(features["unavailability_by_reason"].items())
            if count
        )
        + ". Direction and calibrated probability only; no magnitude is declared."
    )
    lines.append("")
    lines.append(
        "How long a current level actually persists over the included folds, as source "
        f"accounting and never as a feature (`current_release_age_is_a_model_feature: "
        f"{str(persistence['current_release_age_is_a_model_feature']).lower()}`):"
    )
    lines.append("")
    lines.append("| series | min age (days) | median | max |")
    lines.append("| --- | --- | --- | --- |")
    for name, record in sorted(persistence["by_series"].items()):
        lines.append(
            f"| `{name}` | {record['minimum_current_release_age_days']} | "
            f"{record['median_current_release_age_days']} | "
            f"{record['maximum_current_release_age_days']} |"
        )
    lines.append("")

    for model_version in CONFIGURATION_ORDER:
        configuration = result["configurations"][model_version]
        pooled = configuration["candidate"]["pooled_directional"]
        primary = configuration["primary_comparison"]
        reference = configuration["absolute_reference_comparison"]
        calibration = configuration["calibration_comparison"]
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
            f"Matched `{MATCHED_CONTROL}` on the identical timestamps "
            f"**{_number(primary['matched_base_rate_win_rate'])}**; primary delta "
            f"**{_signed(primary['pooled_delta'])}** against a minimum important effect of "
            f"{_signed(MINIMUM_IMPORTANT_EFFECT, 3)}, paired "
            f"{100 * paired['interval_mass']:g}% interval "
            f"[{_signed(paired['interval'][0])}, {_signed(paired['interval'][1])}] "
            f"at alpha {paired['alpha']}, seed {paired['seed']}."
        )
        lines.append("")
        lines.append(
            f"Matched `{ABSOLUTE_REFERENCE}` win rate "
            f"{_number(reference['matched_win_rate'])} "
            f"({_signed(reference['delta_versus_always_up'])} against the candidate). "
            f"Candidate Brier {_number(calibration['candidate_brier_score'])} against the "
            f"control's {_number(calibration['matched_brier_score'])}. Matched "
            f"`{PREVIOUS_24H_SIGN_PERSISTENCE}` "
            f"{_number(controls[PREVIOUS_24H_SIGN_PERSISTENCE]['win_rate'])} at coverage "
            f"{_number(controls[PREVIOUS_24H_SIGN_PERSISTENCE]['coverage'], 5)} "
            "(descriptive only, never inverted)."
        )
        lines.append("")
        lines.append(
            "| fold | eligible | actionable | abstentions | coverage | candidate | "
            f"{MATCHED_CONTROL} | delta | {ABSOLUTE_REFERENCE} |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for name in folds["included_folds"]:
            record = configuration["candidate"]["by_fold"][name]
            directional = record["directional"]
            lines.append(
                f"| {name} | {directional['eligible_decision_timestamps']} | "
                f"{directional['actionable_directional_predictions']} | "
                f"{directional['abstentions']} | "
                f"{_number(directional['coverage'], 5)} | "
                f"{_number(directional['win_rate'])} | "
                f"{_number(record['controls'][MATCHED_CONTROL]['win_rate'])} | "
                f"{_signed(record['delta_versus_training_base_rate'])} | "
                f"{_number(record['controls'][ABSOLUTE_REFERENCE]['win_rate'])} |"
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
                + ". No secondary metric rescues a failed directional gate."
            )
        else:
            lines.append("Every predeclared condition holds.")
        lines.append("")
        fits = configuration["model_fits"]
        lines.append(
            f"Model fits {fits['total']}: {fits['direction_base']} direction base and "
            f"{fits['direction_calibration']} training-only Platt calibration."
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
        + ". The macro source design is now closed for this generation "
        f"(`macro_source_design_closed: "
        f"{str(disposition['macro_source_design_closed']).lower()}`); a third source "
        "semantics is forbidden."
    )
    lines.append("")
    lines.append("## Accounting")
    lines.append("")
    lines.append(
        f"Base-rate controls refit per fold: {result['base_rate_control_fits']['fits']} "
        f"(`{result['base_rate_control_fits']['classification']}`). Sealed queries "
        f"{result['boundaries']['sealed_queries']}. Champion NONE. Real money "
        f"{str(result['boundaries']['real_money']).lower()}. No combination with the rejected "
        "Stage-1, settled-funding, open-interest or cross-asset breadth features, no basis, "
        "CFTC, calendar, news, sentiment or on-chain source, no Stage-1 substrate repair, no "
        "current-revised macro data, no interpolation or future vintage, no post-cutoff data. "
        "Every prior predictive experiment result and every predecessor record is unchanged."
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
        "root_hypothesis_id": result["root_hypothesis_id"],
        "hypothesis_id": configuration["hypothesis_id"],
        "research_generation": result["research_generation"],
        "evaluation_contract": result["evaluation_contract"],
        "evaluation_contract_amendment": result["evaluation_contract_amendment"],
        "preregistration": preregistration_path(model_version),
        "search_plan": result["search_plan"],
        "admission": result["admission"],
        "source_audit": result["source_audit"],
        "source_cadence_integrity": result["source_cadence_integrity"],
        "predecessor": result["predecessor"],
        "source": result["source"],
        "labels": result["labels"],
        "folds": result["folds"],
        "features": result["features"],
        "release_state_accounting": result["release_state_accounting"],
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


def validate_macro_release_state(
    root: Path = ROOT, *, data_available: bool = False
) -> dict[str, Any]:
    """Check the committed experiments against their frozen records, and the data if present."""
    findings: dict[str, Any] = {"status": "PASS", "data_replayed": False}

    plan = json.loads((root / SEARCH_PLAN_PATH).read_text(encoding="utf-8"))
    admitted = json.loads((root / ADMISSION_PATH).read_text(encoding="utf-8"))
    audit = json.loads((root / AUDIT_PATH).read_text(encoding="utf-8"))
    if plan != search_plan():
        raise ExperimentError("the committed search plan drifted from the code")
    if admitted != admission(root):
        raise ExperimentError("the admission artifact no longer matches the frozen files")
    if admitted["status"] != "PASS" or not admitted["execution_authorized"]:
        raise ExperimentError("the pre-execution admission gate did not pass")
    if admitted["model_fits_executed"] or admitted["market_results_observed"]:
        raise ExperimentError("the admission artifact claims a result it preceded")
    if audit["status"] != PASS:
        raise ExperimentError("the source audit did not pass its own gates")
    if audit["target_bearing_model_fitted"]:
        raise ExperimentError("the source audit claims a model fit it must precede")
    if audit["predecessor_reclassified"]:
        raise ExperimentError("the source audit reclassified the predecessor source block")
    if not audit["source_cadence_integrity"]["passed"]:
        raise ExperimentError("the source cadence integrity gate did not pass")
    for key in (
        "btc_close_column_loaded",
        "btc_return_values_inspected",
        "btc_direction_labels_inspected",
        "candidate_predictions_inspected",
    ):
        if audit["coverage"][key]:
            raise ExperimentError(f"the fold selection inspected an outcome: {key}")
    if admitted["director_decisions"] != director_decisions():
        raise ExperimentError("the admitted Research Director decisions drifted from the code")
    if plan["family_size"] != FAMILY_SIZE or len(plan["configurations"]) != FAMILY_SIZE:
        raise ExperimentError("the family size drifted from the frozen plan")
    if plan["inference"]["seed"] != PAIRED_SEED:
        raise ExperimentError("the family's paired bootstrap seed drifted")
    if plan["declares"]["magnitude"]:
        raise ExperimentError("the family declared a magnitude the plan froze out")

    # The predecessor's frozen records, and every prior executed result, must still be the
    # bytes the admission recorded before this family was executed.
    for path, digest in admitted["predecessor_record_sha256"].items():
        if path not in PREDECESSOR_RECORDS:
            raise ExperimentError(f"an unexpected predecessor record was pinned: {path}")
        if content_hash(root / path) != digest:
            raise ExperimentError(f"a predecessor record changed after admission: {path}")
    if set(admitted["predecessor_record_sha256"]) != set(PREDECESSOR_RECORDS):
        raise ExperimentError("the pinned predecessor record set drifted")
    for path, digest in admitted["prior_experiment_result_sha256"].items():
        if content_hash(root / path) != digest:
            raise ExperimentError(f"a prior predictive result changed after admission: {path}")
    if set(admitted["prior_experiment_result_sha256"]) != set(PRIOR_EXPERIMENT_RESULTS):
        raise ExperimentError("the pinned prior-result set drifted")

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
    if result["features"]["btc_price_or_return_feature_present"]:
        raise ExperimentError("a BTC price feature entered the macro family")
    if result["features"]["combined_with_rejected_families"]:
        raise ExperimentError("the family was combined with a rejected family")
    if result["folds"]["included_folds"] != admitted["included_folds"]:
        raise ExperimentError("the included folds are not the audited source-admissible set")
    if result["predecessor"]["reclassified"] or result["predecessor"]["records_modified"]:
        raise ExperimentError("the result claims a change to the predecessor source block")
    if result["source"]["current_revised_substitution"]:
        raise ExperimentError("current-revised macro data entered the family")
    if result["source"]["interpolation"] or result["source"]["nearest_future_substitution"]:
        raise ExperimentError("an interpolated or future-substituted value entered the family")
    if result["source"]["current_state_expiry_relative_to_decision_time"]:
        raise ExperimentError("the corrected release-state semantics were not used")
    if result["source"]["post_2024_vintages"]:
        raise ExperimentError("a post-cutoff vintage entered the family")
    if result["release_state_accounting"]["current_release_age_is_a_model_feature"]:
        raise ExperimentError("the current release age was used as a model feature")

    labels = result["labels"]
    if labels["admissible_labels"] + labels["excluded_total"] != labels["grid_decision_instants"]:
        raise ExperimentError("the label accounting does not close")
    features = result["features"]
    if (
        features["available_vectors"] + features["unavailable_vectors"]
        != labels["admissible_labels"]
    ):
        raise ExperimentError("the macro availability accounting does not close")

    advancing: list[str] = []
    for model_version in CONFIGURATION_ORDER:
        configuration = result["configurations"][model_version]
        pooled = configuration["candidate"]["pooled_directional"]
        primary = configuration["primary_comparison"]
        reference = configuration["absolute_reference_comparison"]
        calibration = configuration["calibration_comparison"]
        paired = primary["paired_interval"]
        prereg = preregistration(model_version, root)

        if configuration["experiment_id"] != EXPERIMENT_IDS[model_version]:
            raise ExperimentError(f"{model_version}: wrong experiment identity")
        if configuration["model"]["declares_magnitude"]:
            raise ExperimentError(f"{model_version}: declared a magnitude after the freeze")
        if primary["minimum_important_effect"] != MINIMUM_IMPORTANT_EFFECT:
            raise ExperimentError(f"{model_version}: the MESI changed after the result")
        if primary["matched_control"] != MATCHED_CONTROL:
            raise ExperimentError(f"{model_version}: the matched control changed after the result")
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
            float(reference["matched_win_rate"]),
            float(calibration["candidate_brier_score"]),
            float(calibration["matched_brier_score"]),
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
        if recomputed["secondary_metric_used_to_rescue"]:
            raise ExperimentError(f"{model_version}: a secondary metric rescued the gate")
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
            "total": 2 * count,
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
            for control in (MATCHED_CONTROL, ABSOLUTE_REFERENCE):
                if (
                    record["controls"][control]["eligible_decision_timestamps"]
                    != record["matched_universe"]["records"]
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
    if not disposition["macro_source_design_closed"]:
        raise ExperimentError("the macro source design must close with this checkpoint")
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
    if budget["source_semantics_versions_consumed"] != 1:
        raise ExperimentError("the source-semantics budget does not close")
    if budget["source_semantics_versions_remaining"] != 0:
        raise ExperimentError("a further macro source redesign would remain authorized")

    boundaries = result["boundaries"]
    for key in (
        "additional_information_family",
        "combined_with_rejected_families",
        "predecessor_records_modified",
        "predecessor_reclassified",
        "third_macro_source_redesign",
        "coverage_gate_lowered_after_observation",
        "stage1_substrate_repair",
        "current_revised_macro_data",
        "interpolation_or_future_vintage",
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
    "validate_macro_release_state",
]
