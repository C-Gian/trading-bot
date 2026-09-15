"""Deterministic P0 discovery, provenance, inference, and detectability audits."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, localcontext
from math import factorial
from pathlib import Path
from statistics import fmean, stdev
from typing import Any

import pyarrow.parquet as pq
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]

MATERIAL_ECONOMIC_HYPOTHESIS = "MATERIAL_ECONOMIC_HYPOTHESIS"
CONFIGURATION = "CONFIGURATION"
MATCHED_CONTROL = "MATCHED_CONTROL"
COST_OR_DELAY_PROFILE = "COST_OR_DELAY_PROFILE"
WALK_FORWARD_FIT = "WALK_FORWARD_FIT"
REPRODUCTION = "REPRODUCTION"
BLOCKED_NEVER_OBSERVED = "BLOCKED_NEVER_OBSERVED"

EVENT_CLASSES = frozenset(
    {
        MATERIAL_ECONOMIC_HYPOTHESIS,
        CONFIGURATION,
        MATCHED_CONTROL,
        COST_OR_DELAY_PROFILE,
        WALK_FORWARD_FIT,
        REPRODUCTION,
        BLOCKED_NEVER_OBSERVED,
    }
)
PROVENANCE_STATUSES = frozenset(
    {"EX_ANTE_CONVENTION", "INHERITED", "RESULT_DEPENDENT", "UNKNOWN_PROVENANCE"}
)
BLOCKED_HYPOTHESES = frozenset({"WIKIPEDIA_ATTENTION_SHOCK_ADDS_INFORMATION_V1"})
PRIMARY_ALPHA = 0.05
POWER_TARGET = 0.80
DECIMAL_PI = Decimal(
    "3.141592653589793238462643383279502884197169399375105820974944592307816406286"
)


class StatisticalGovernanceError(ValueError):
    """A statistical calculation lacks a governed or finite basis."""


def _gamma_integer_or_half(twice_value: int) -> Decimal:
    if twice_value < 1:
        raise StatisticalGovernanceError("gamma input must be a positive integer or half")
    if twice_value % 2 == 0:
        return Decimal(factorial(twice_value // 2 - 1))
    half_steps = (twice_value - 1) // 2
    numerator = Decimal(factorial(2 * half_steps)) * DECIMAL_PI.sqrt()
    denominator = (Decimal(4) ** half_steps) * Decimal(factorial(half_steps))
    return numerator / denominator


def _regularized_incomplete_beta(x: Decimal, a: Decimal, b: Decimal) -> Decimal:
    """Deterministic high-precision regularized incomplete beta continued fraction."""
    if not Decimal(0) < x < Decimal(1):
        if x == 0:
            return Decimal(0)
        if x == 1:
            return Decimal(1)
        raise StatisticalGovernanceError("incomplete beta x is outside [0, 1]")

    tiny = Decimal("1e-70")
    epsilon = Decimal("1e-70")

    def continued_fraction(left: Decimal, right: Decimal, value: Decimal) -> Decimal:
        total = left + right
        plus = left + 1
        minus = left - 1
        c = Decimal(1)
        d = 1 - total * value / plus
        if abs(d) < tiny:
            d = tiny
        d = 1 / d
        result = d
        for index in range(1, 10_001):
            doubled = Decimal(2 * index)
            term = Decimal(index) * (right - index) * value
            term /= (minus + doubled) * (left + doubled)
            d = 1 + term * d
            d = tiny if abs(d) < tiny else d
            c = 1 + term / c
            c = tiny if abs(c) < tiny else c
            d = 1 / d
            result *= d * c

            term = -(left + index) * (total + index) * value
            term /= (left + doubled) * (plus + doubled)
            d = 1 + term * d
            d = tiny if abs(d) < tiny else d
            c = 1 + term / c
            c = tiny if abs(c) < tiny else c
            d = 1 / d
            delta = d * c
            result *= delta
            if abs(delta - 1) <= epsilon:
                return result
        raise StatisticalGovernanceError("incomplete beta continued fraction did not converge")

    twice_a = int(a * 2)
    twice_b = int(b * 2)
    beta = (
        _gamma_integer_or_half(twice_a)
        * _gamma_integer_or_half(twice_b)
        / _gamma_integer_or_half(twice_a + twice_b)
    )
    front = (a * x.ln() + b * (1 - x).ln()).exp() / beta
    if x < (a + 1) / (a + b + 2):
        return front * continued_fraction(a, b, x) / a
    return 1 - front * continued_fraction(b, a, 1 - x) / b


def deterministic_student_t_sf(statistic: float, *, degrees_of_freedom: int) -> float:
    """One-tailed Student-t survival probability with platform-stable arithmetic."""
    if not math.isfinite(statistic) or degrees_of_freedom < 1:
        raise StatisticalGovernanceError("Student-t inputs are invalid")
    if statistic == 0:
        return 0.5
    with localcontext() as context:
        context.prec = 80
        value = Decimal.from_float(abs(statistic))
        freedom = Decimal(degrees_of_freedom)
        x = freedom / (freedom + value * value)
        tail = _regularized_incomplete_beta(x, freedom / 2, Decimal("0.5")) / 2
        return float(tail if statistic > 0 else 1 - tail)


@dataclass(frozen=True)
class EvidenceSpec:
    hypothesis_id: str
    experiment_id: str
    directional_positive_claim: bool | None


MATERIAL_PRIMARY_SPECS = (
    EvidenceSpec("HYP-TREND-V1", "EXP-BASE-003-TREND", None),
    EvidenceSpec("HYP-BREAKOUT-V1", "EXP-BASE-004-BREAKOUT", None),
    EvidenceSpec("ALIGNED_PARTICIPATION_CONTINUATION_V1", "EXP-ALG-009-ALIGNED", True),
    EvidenceSpec(
        "PERSISTENT_TREND_PULLBACK_RECOVERY_V1",
        "EXP-ALG-010-PULLBACK-RECOVERY-CORE",
        True,
    ),
    EvidenceSpec("AGGRESSIVE_BUY_FLOW_TRANSITION_V1", "EXP-ALG-012-ORDERFLOW-CORE", True),
    EvidenceSpec("LINEAR_NET_R_SELECTION_V1", "EXP-ML-014-LINEAR-NET-R-FULL", True),
    EvidenceSpec("DYNAMIC_INTERNAL_MACRO_NET_R_V1", "EXP-ML-016-EWLS-INTERNAL-MACRO", True),
    EvidenceSpec(
        "FINANCIAL_REGIME_CONDITIONED_SIGNAL_WEIGHTS_V1",
        "EXP-ML-018-REGIME-TWO-EXPERTS",
        True,
    ),
    EvidenceSpec(
        "NFCI_MODULATES_INTERNAL_SIGNAL_VALUE_V1",
        "EXP-ML-020-NFCI-CONTEXT-INTERACTIONS",
        True,
    ),
    EvidenceSpec(
        "NONLINEAR_INTERNAL_SIGNAL_INTERACTIONS_V1",
        "EXP-ML-022-SHALLOW-INTERNAL-HGBR",
        True,
    ),
    EvidenceSpec(
        "SETTLED_FUNDING_ADDS_POSITIONING_INFORMATION_V1",
        "EXP-ML-024-INTERNAL-PLUS-FUNDING-HGBR",
        True,
    ),
    EvidenceSpec(
        "CFTC_LEVERAGED_FUNDS_NET_POSITIONING_ADDS_INFORMATION_V1",
        "EXP-ML-028-INTERNAL-PLUS-CFTC-LEVERAGED-NET-HGBR",
        True,
    ),
)


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise StatisticalGovernanceError(f"expected a JSON object: {path}")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise StatisticalGovernanceError(f"expected JSON objects in {path}")
            records.append(value)
    return records


def load_search_records(root: Path = ROOT) -> list[dict[str, Any]]:
    """Load the smallest canonical ledgers and deterministically deduplicate them."""
    records = _jsonl(root / "research/memory/SEARCH_LEDGER.jsonl")
    wp006 = _json(root / "research/memory/WP006-NOVELTY-ADMISSION.json")
    for variant in wp006["variants"]:
        records.append(
            {
                "work_package": "WP-006",
                "experiment_id": variant["experiment_id"],
                "hypothesis_id": wp006["proposed_hypothesis_id"],
                "hypothesis_role": variant["hypothesis_role"],
                "record_kind": "PREREGISTERED_ADMISSION",
                "result_path": (f"research/experiments/{variant['experiment_id']}/result.json"),
            }
        )
    for path in sorted((root / "research/memory/registry/ledger").glob("*.jsonl")):
        records.extend(_jsonl(path))
    by_experiment = {str(record["experiment_id"]): record for record in records}
    return [by_experiment[key] for key in sorted(by_experiment)]


def _result_exists(root: Path, record: Mapping[str, Any]) -> bool:
    result_path = record.get("result_path")
    return isinstance(result_path, str) and (root / result_path).is_file()


def classify_non_discovery_role(role: str) -> str:
    if "MATCHED" in role:
        return MATCHED_CONTROL
    if "TIMING" in role:
        return COST_OR_DELAY_PROFILE
    return CONFIGURATION


def build_material_hypothesis_ledger(
    records: Iterable[Mapping[str, Any]],
    *,
    observed_experiment_ids: Iterable[str],
    blocked_hypothesis_ids: Iterable[str],
    profile_evaluations_observed: int,
    walk_forward_fits_observed: int,
    reproduction_count: int,
    registered_configuration_count: int,
    registered_profile_count: int,
    registered_fit_count: int,
    unquantified_pre_repo_exposure: bool,
) -> dict[str, Any]:
    observed = frozenset(observed_experiment_ids)
    blocked = frozenset(blocked_hypothesis_ids)
    ordered = sorted((dict(record) for record in records), key=lambda item: item["experiment_id"])
    economic_by_hypothesis: dict[str, list[dict[str, Any]]] = {}
    non_discovery: list[dict[str, Any]] = []

    for record in ordered:
        hypothesis_id = str(record.get("hypothesis_id", ""))
        role = str(record.get("hypothesis_role", ""))
        experiment_id = str(record["experiment_id"])
        if role == "ECONOMIC_CORE":
            economic_by_hypothesis.setdefault(hypothesis_id, []).append(record)
            continue
        non_discovery.append(
            {
                "classification": classify_non_discovery_role(role),
                "discovery_family_member": False,
                "event_id": experiment_id,
                "hypothesis_id": hypothesis_id,
                "observed": experiment_id in observed,
                "semantic_role": role,
                "unit_count": 1,
            }
        )

    discovery_events: list[dict[str, Any]] = []
    for hypothesis_id in sorted(economic_by_hypothesis):
        ids = sorted(
            str(record["experiment_id"]) for record in economic_by_hypothesis[hypothesis_id]
        )
        is_blocked = hypothesis_id in blocked
        is_observed = any(experiment_id in observed for experiment_id in ids) and not is_blocked
        discovery_events.append(
            {
                "classification": (
                    BLOCKED_NEVER_OBSERVED if is_blocked else MATERIAL_ECONOMIC_HYPOTHESIS
                ),
                "discovery_family_member": is_observed,
                "event_id": hypothesis_id,
                "experiment_ids": ids,
                "observed": is_observed,
                "unit_count": 1,
            }
        )

    aggregate_events = [
        {
            "classification": COST_OR_DELAY_PROFILE,
            "discovery_family_member": False,
            "event_id": "OBSERVED_PROFILE_EVALUATIONS",
            "observed": True,
            "unit_count": profile_evaluations_observed,
        },
        {
            "classification": WALK_FORWARD_FIT,
            "discovery_family_member": False,
            "event_id": "OBSERVED_WALK_FORWARD_FITS",
            "observed": True,
            "unit_count": walk_forward_fits_observed,
        },
        {
            "classification": REPRODUCTION,
            "discovery_family_member": False,
            "event_id": "OBSERVED_REPRODUCTIONS",
            "observed": reproduction_count > 0,
            "unit_count": reproduction_count,
        },
    ]
    events = sorted(
        [*discovery_events, *non_discovery, *aggregate_events],
        key=lambda item: (item["classification"], item["event_id"]),
    )
    if any(event["classification"] not in EVENT_CLASSES for event in events):
        raise StatisticalGovernanceError("unknown ledger classification")
    known_family = sorted(
        event["event_id"] for event in discovery_events if event["discovery_family_member"]
    )
    registered_material = len(discovery_events)
    blocked_count = sum(event["classification"] == BLOCKED_NEVER_OBSERVED for event in events)
    matched_observed = sum(
        event["classification"] == MATCHED_CONTROL and event["observed"] for event in events
    )
    payload = {
        "schema_version": 1,
        "ledger_id": "MATERIAL-HYPOTHESIS-LEDGER-V1",
        "counting_policy": {
            "annual_folds_are_hypotheses": False,
            "cost_or_delay_profiles_are_hypotheses": False,
            "matched_controls_are_discoveries": False,
            "model_fits_are_hypotheses": False,
            "reproductions_are_discoveries": False,
            "only_observed_material_economic_hypotheses_enter_primary_family": True,
        },
        "registered_material_hypothesis_count": registered_material,
        "known_material_hypothesis_count": len(known_family),
        "known_family_size": len(known_family),
        "known_discovery_family": known_family,
        "unquantified_pre_repo_exposure": unquantified_pre_repo_exposure,
        "known_count_is_lower_bound": unquantified_pre_repo_exposure,
        "missing_historical_trials_estimated": False,
        "counts": {
            MATERIAL_ECONOMIC_HYPOTHESIS: len(known_family),
            CONFIGURATION: registered_configuration_count,
            MATCHED_CONTROL: matched_observed,
            COST_OR_DELAY_PROFILE: profile_evaluations_observed,
            WALK_FORWARD_FIT: walk_forward_fits_observed,
            REPRODUCTION: reproduction_count,
            BLOCKED_NEVER_OBSERVED: blocked_count,
        },
        "registered_search_burden": {
            "configurations": registered_configuration_count,
            "profile_evaluations": registered_profile_count,
            "supervised_model_fits": registered_fit_count,
        },
        "events": events,
    }
    payload["events_sha256"] = canonical_hash(events)
    return payload


def build_repository_ledger(root: Path = ROOT) -> dict[str, Any]:
    records = load_search_records(root)
    observed = {str(record["experiment_id"]) for record in records if _result_exists(root, record)}
    wp017_primary = _json(
        root / "research/experiments/EXP-ML-028-INTERNAL-PLUS-CFTC-LEVERAGED-NET-HGBR/result.json"
    )
    control_id = wp017_primary["secondary_results"]["primary_minus_control_default_net_r"][
        "control_experiment_id"
    ]
    observed.add(str(control_id))
    result_paths = sorted((root / "research/experiments").glob("*/result.json"))
    observed_profiles = (
        sum(int(_json(path)["trial_accounting"]["executed_trials"]) for path in result_paths) + 4
    )  # WP017's matched control is embedded in the single counted result.
    model_fits = sum(_extract_model_fits(_json(path)) for path in result_paths)
    state = _json(root / "state/current_state.json")
    model_fits += int(state["adaptive_challenger"]["inadmissible_model_fits"])
    adaptive = state["adaptive_search"]
    reproduction_count = int(
        state["research_runner"].get("wp015_reproduction", {}).get("status") == "SUCCESS"
    )
    return build_material_hypothesis_ledger(
        records,
        observed_experiment_ids=observed,
        blocked_hypothesis_ids=BLOCKED_HYPOTHESES,
        profile_evaluations_observed=observed_profiles,
        walk_forward_fits_observed=model_fits,
        reproduction_count=reproduction_count,
        registered_configuration_count=int(adaptive["configuration_variants"]),
        registered_profile_count=int(adaptive["profile_trials"]),
        registered_fit_count=int(adaptive["supervised_model_fits"]),
        unquantified_pre_repo_exposure=True,
    )


def _extract_model_fits(value: Any) -> int:
    """Count actual fits once from result fields with their historically varied names."""
    if not isinstance(value, dict):
        return 0
    secondary = value.get("secondary_results")
    if not isinstance(secondary, dict):
        return 0
    annual = secondary.get("annual_folds")
    if isinstance(annual, dict) and isinstance(annual.get("model_fits"), int):
        return int(annual["model_fits"])
    fold_models = secondary.get("fold_models")
    if isinstance(fold_models, list):
        return len(fold_models)
    if isinstance(secondary.get("monthly_models"), int):
        return int(secondary["monthly_models"])
    if isinstance(secondary.get("expert_fits"), int):
        return int(secondary["expert_fits"])
    return 0


def holm_bonferroni(
    raw_p_values: Mapping[str, float], *, family_size: int | None = None
) -> dict[str, float]:
    """Holm step-down adjusted p-values, deterministic under input ordering."""
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or not 0 <= float(value) <= 1
        for value in raw_p_values.values()
    ):
        raise StatisticalGovernanceError("Holm inputs must be finite probabilities")
    size = family_size if family_size is not None else len(raw_p_values)
    if size < len(raw_p_values) or size <= 0:
        raise StatisticalGovernanceError("Holm family size is invalid")
    ordered = sorted(raw_p_values.items(), key=lambda item: (float(item[1]), item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (key, value) in enumerate(ordered):
        candidate = min(1.0, (size - rank) * float(value))
        running = max(running, candidate)
        adjusted[key] = running
    return {key: adjusted[key] for key in sorted(adjusted)}


def compute_mde(
    *,
    sample_standard_deviation: float,
    effective_sample_size: float,
    alpha: float,
    power_target: float,
    directional: bool,
    dependence_method: str,
) -> float:
    """Normal-approximation mean MDE under an explicit governed sample-size basis."""
    if dependence_method != "GOVERNED_IID":
        raise StatisticalGovernanceError("dependence basis is not governed")
    values = (sample_standard_deviation, effective_sample_size, alpha, power_target)
    if any(not math.isfinite(float(value)) for value in values):
        raise StatisticalGovernanceError("MDE inputs must be finite")
    if (
        sample_standard_deviation <= 0
        or effective_sample_size <= 1
        or not 0 < alpha < 1
        or not 0.5 < power_target < 1
    ):
        raise StatisticalGovernanceError("MDE inputs are outside the valid domain")
    critical = stats.norm.ppf(1 - alpha if directional else 1 - alpha / 2)
    power_quantile = stats.norm.ppf(power_target)
    return float(
        (critical + power_quantile) * sample_standard_deviation / math.sqrt(effective_sample_size)
    )


def _profile_name(trial: Mapping[str, Any]) -> str:
    profile = trial.get("profile")
    if isinstance(profile, str):
        return profile
    if isinstance(profile, dict):
        return str(profile.get("name", ""))
    return ""


def _raw_outcomes(root: Path, experiment_id: str) -> tuple[list[float], list[float] | None]:
    directory = root / "research/experiments" / experiment_id
    parquet = directory / "trials.parquet"
    if parquet.is_file():
        table = pq.read_table(parquet)
        rows = table.to_pylist()
        selected = [
            row
            for row in rows
            if row.get("profile") == "DEFAULT"
            and row.get("status") == "VALID"
            and (
                experiment_id != "EXP-ML-028-INTERNAL-PLUS-CFTC-LEVERAGED-NET-HGBR"
                or row.get("variant") == "INTERNAL_PLUS_CFTC_LEVERAGED_NET_HGBR"
            )
        ]
        returns = [float(row["net_r"]) for row in selected if row.get("net_r") is not None]
        bps = [
            float(row["net_return_bps"])
            for row in selected
            if row.get("net_return_bps") is not None
        ]
        return returns, bps if len(bps) == len(returns) else None

    trials_path = directory / "trials.json"
    if not trials_path.is_file():
        return [], None
    trials = json.loads(trials_path.read_text(encoding="utf-8"))
    if not isinstance(trials, list):
        return [], None
    default = next(
        (
            trial
            for trial in trials
            if isinstance(trial, dict) and _profile_name(trial) == "DEFAULT"
        ),
        None,
    )
    if not isinstance(default, dict) or not isinstance(default.get("trades"), list):
        return [], None
    selected = [
        trade
        for trade in default["trades"]
        if isinstance(trade, dict)
        and trade.get("status") == "VALID"
        and trade.get("net_r") is not None
    ]
    returns = [float(trade["net_r"]) for trade in selected]
    bps = [float(trade["net_return_bps"]) for trade in selected if "net_return_bps" in trade]
    return returns, bps if len(bps) == len(returns) else None


def _governed_ess(result: Mapping[str, Any]) -> float | None:
    secondary = result.get("secondary_results")
    if not isinstance(secondary, dict):
        return None
    candidates: list[Any] = []
    annual = secondary.get("annual_folds")
    if isinstance(annual, dict):
        candidates.append(annual.get("trade_ess"))
    concentration = secondary.get("trade_ess_and_concentration")
    if isinstance(concentration, dict):
        candidates.append(concentration.get("trade_ess"))
    profiles = secondary.get("profiles")
    if isinstance(profiles, dict):
        default = profiles.get("DEFAULT")
        if isinstance(default, dict):
            diagnostics = default.get("diagnostics")
            if isinstance(diagnostics, dict):
                candidates.append(diagnostics.get("trade_ess"))
            summary = default.get("summary")
            if isinstance(summary, dict) and isinstance(summary.get("diagnostics"), dict):
                candidates.append(summary["diagnostics"].get("trade_ess"))
    for value in candidates:
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 1:
            return float(value)
    return None


def _terminal_classification(result: Mapping[str, Any]) -> str:
    secondary = result.get("secondary_results")
    if isinstance(secondary, dict):
        annual = secondary.get("annual_folds")
        if isinstance(annual, dict) and isinstance(annual.get("terminal_classification"), str):
            return str(annual["terminal_classification"])
        if isinstance(secondary.get("terminal_classification"), str):
            return str(secondary["terminal_classification"])
    return "HISTORICAL_CLASSIFICATION_NOT_DEFINED"


def _summary_metric(result: Mapping[str, Any], metric: str) -> float | int | None:
    secondary = result.get("secondary_results")
    if not isinstance(secondary, dict):
        return None
    candidates: list[Any] = [secondary.get(metric)]
    annual = secondary.get("annual_folds")
    if isinstance(annual, dict):
        candidates.append(annual.get(metric))
    profiles = secondary.get("profiles")
    if isinstance(profiles, dict):
        default = profiles.get("DEFAULT")
        if isinstance(default, dict):
            metrics = default.get("metrics")
            if isinstance(metrics, dict):
                candidates.append(metrics.get(metric))
            summary = default.get("summary")
            if isinstance(summary, dict) and isinstance(summary.get("metrics"), dict):
                candidates.append(summary["metrics"].get(metric))
    for value in candidates:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    return None


def reconstruct_statistical_evidence(root: Path = ROOT) -> dict[str, Any]:
    ledger = build_repository_ledger(root)
    family_size = int(ledger["known_family_size"])
    rows: list[dict[str, Any]] = []
    raw_p_values: dict[str, float] = {}
    for spec in MATERIAL_PRIMARY_SPECS:
        result_path = root / "research/experiments" / spec.experiment_id / "result.json"
        result = _json(result_path)
        outcomes, bps = _raw_outcomes(root, spec.experiment_id)
        row: dict[str, Any] = {
            "hypothesis_id": spec.hypothesis_id,
            "experiment_id": spec.experiment_id,
            "terminal_historical_classification": _terminal_classification(result),
            "raw_trade_count": (
                len(outcomes) if outcomes else _summary_metric(result, "trade_count")
            ),
            "mean_net_R": float(result["primary_result"]),
            "mean_net_bps": _summary_metric(result, "net_expectancy_bps"),
            "sample_standard_deviation": None,
            "naive_test_statistic": None,
            "naive_test_statistic_basis": None,
            "governed_effective_sample_size": _governed_ess(result),
            "dependence_adjusted_statistic": None,
            "unadjusted_p_value": None,
            "unadjusted_p_value_basis": None,
            "holm_adjusted_p_value": None,
            "statistical_status": "EXACT_STATISTIC_UNAVAILABLE",
            "unavailable_reason": None,
        }
        if outcomes:
            # statistics.fmean/stdev have a platform-stable, high-precision reduction
            # path. NumPy's vector reduction can differ by a final bit across CPU builds,
            # which is unacceptable for byte-frozen governance artifacts.
            mean = fmean(outcomes)
            deviation = stdev(outcomes) if len(outcomes) > 1 else math.nan
            row.update(
                raw_trade_count=len(outcomes),
                mean_net_R=mean,
                mean_net_bps=fmean(bps) if bps is not None else None,
                sample_standard_deviation=deviation if math.isfinite(deviation) else None,
            )
            if len(outcomes) > 1 and deviation > 0:
                statistic = mean / (deviation / math.sqrt(len(outcomes)))
                row["naive_test_statistic"] = float(statistic)
                row["naive_test_statistic_basis"] = "NAIVE_IID"
                if spec.directional_positive_claim is True:
                    raw_p = deterministic_student_t_sf(
                        statistic, degrees_of_freedom=len(outcomes) - 1
                    )
                    row["unadjusted_p_value"] = raw_p
                    row["unadjusted_p_value_basis"] = "NAIVE_IID_ONE_SIDED"
                    row["statistical_status"] = "NAIVE_IID_T_AVAILABLE_DEPENDENCE_UNRESOLVED"
                    row["unavailable_reason"] = None
                    raw_p_values[spec.hypothesis_id] = raw_p
                else:
                    row["statistical_status"] = "TEST_STATISTIC_AVAILABLE_P_VALUE_UNAVAILABLE"
                    row["unavailable_reason"] = "HISTORICAL_DIRECTIONALITY_AMBIGUOUS"
            else:
                row["unavailable_reason"] = "RAW_VARIANCE_OR_SAMPLE_SIZE_INSUFFICIENT"
        else:
            row["unavailable_reason"] = (
                "RAW_TRADE_OUTCOMES_NOT_PRESERVED_IN_GOVERNED_RESULT_ARTIFACT"
            )
        rows.append(row)

    adjusted = holm_bonferroni(raw_p_values, family_size=family_size)
    for row in rows:
        hypothesis_id = str(row["hypothesis_id"])
        if hypothesis_id in adjusted:
            row["holm_adjusted_p_value"] = adjusted[hypothesis_id]

    detectability = []
    for row in rows:
        diagnostic_ess = row["governed_effective_sample_size"]
        deviation = row["sample_standard_deviation"]
        record = {
            "hypothesis_id": row["hypothesis_id"],
            "experiment_id": row["experiment_id"],
            "raw_sample_size": row["raw_trade_count"],
            "effective_sample_size": None,
            "diagnostic_trade_ess": diagnostic_ess,
            "observed_dispersion_estimate": deviation,
            "dependence_method": "NO_GOVERNED_INFERENTIAL_DEPENDENCE_MODEL",
            "dependence_diagnostic_method": (
                "POSITIVE_ACF_LAGS_1_TO_5_ESS_DIAGNOSTIC_ONLY" if diagnostic_ess else None
            ),
            "alpha": PRIMARY_ALPHA,
            "power_target": POWER_TARGET,
            "minimum_detectable_effect": None,
            "mde_metric": "MEAN_NET_R_PER_TRADE",
            "mde_unit": "R_PER_TRADE",
            "multiplicity_basis": (
                f"BONFERRONI_WORST_CASE_ALPHA_{PRIMARY_ALPHA}/{family_size}_KNOWN_FAMILY"
            ),
            "calculation_status": "MDE_UNAVAILABLE",
            "unavailable_reason": "NO_GOVERNED_INFERENTIAL_DEPENDENCE_MODEL",
            "economic_power_interpretation": "ECONOMIC_POWER_INTERPRETATION_UNAVAILABLE",
            "historical_mesi": None,
            "terminal_historical_classification": row["terminal_historical_classification"],
        }
        detectability.append(record)

    payload = {
        "schema_version": 1,
        "audit_id": "STATISTICAL-EVIDENCE-AUDIT-V1",
        "alpha": PRIMARY_ALPHA,
        "power_target": POWER_TARGET,
        "known_material_hypothesis_count": family_size,
        "known_family_size": family_size,
        "unquantified_pre_repo_exposure": ledger["unquantified_pre_repo_exposure"],
        "holm_scope_limitation": (
            "Holm adjustment covers only the documented known family and cannot fully "
            "correct unknowable historical selection."
        ),
        "dependence_inference_limitation": (
            "Naive t statistics and raw p-values use exact preserved trades but an IID "
            "standard error; governed ESS remains a diagnostic and is not used to create "
            "a dependence-adjusted test statistic, p-value, or inferential MDE. Historical "
            "MDE fails closed without a governed inferential dependence model."
        ),
        "historical_mesi_invented": False,
        "historical_classifications_changed": False,
        "statistics": sorted(rows, key=lambda item: item["hypothesis_id"]),
        "detectability": sorted(detectability, key=lambda item: item["hypothesis_id"]),
    }
    payload["statistics_sha256"] = canonical_hash(payload["statistics"])
    payload["detectability_sha256"] = canonical_hash(payload["detectability"])
    return payload


def normalize_provenance_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(entry)
    status = value.get("provenance_status")
    evidence = value.get("evidence")
    if status not in PROVENANCE_STATUSES or not isinstance(evidence, list) or not evidence:
        value["provenance_status"] = "UNKNOWN_PROVENANCE"
        value["known_before_relevant_result_exposure"] = None
        value["notes"] = (
            str(value.get("notes", "")) + " Unsupported provenance failed closed."
        ).strip()
    return value


def build_aligned_provenance_audit() -> dict[str, Any]:
    design_source = "research/design/ALGORITHM_FAMILY_V1_DESIGN.md"
    design_commit = "17cc59a753d2368637de0263c31d3479d1303dff"
    baseline_source = "backend/app/research/baselines.py"
    baseline_commit = "ee6488c9fc6d5a8ee0bf9323b6fbf48a66f30f8d"
    entries = [
        {
            "parameter_id": "ALIGNED_BREAKOUT_LOOKBACK",
            "value": 24,
            "unit": "completed_1h_bars",
            "semantic_role": "ENTRY_EVENT_PRIOR_HIGH_WINDOW",
            "first_known_repository_source": baseline_source,
            "first_known_commit": baseline_commit,
            "known_before_relevant_result_exposure": True,
            "provenance_status": "INHERITED",
            "evidence": [
                design_source,
                "research/experiments/EXP-BASE-004-BREAKOUT/preregistration.json",
            ],
            "notes": "Inherited unchanged from the fixed WP-003 breakout baseline.",
        },
        {
            "parameter_id": "ALIGNED_CONTEXT_LENGTH",
            "value": {"completed_4h_bars": 43, "close_to_close_increments": 42},
            "unit": "4h_bars_and_increments",
            "semantic_role": "DIRECTIONAL_PERSISTENCE_CONTEXT",
            "first_known_repository_source": design_source,
            "first_known_commit": design_commit,
            "known_before_relevant_result_exposure": True,
            "provenance_status": "EX_ANTE_CONVENTION",
            "evidence": [
                design_source,
                "research/experiments/EXP-ALG-009-ALIGNED/preregistration.json",
            ],
            "notes": "Seven-day calendar interpretation; no repository-recorded search is reported.",
        },
        {
            "parameter_id": "ALIGNED_PERSISTENCE_THRESHOLD",
            "value": "U >= 2D",
            "unit": "positive_to_negative_price_travel_ratio",
            "semantic_role": "DIRECTIONAL_PERSISTENCE_GATE",
            "first_known_repository_source": design_source,
            "first_known_commit": design_commit,
            "known_before_relevant_result_exposure": True,
            "provenance_status": "EX_ANTE_CONVENTION",
            "evidence": [
                design_source,
                "research/experiments/EXP-ALG-009-ALIGNED/preregistration.json",
            ],
            "notes": "Equivalent signed efficiency threshold is one third; no threshold search recorded.",
        },
        {
            "parameter_id": "ALIGNED_VOLUME_REFERENCE_LOOKBACK",
            "value": 24,
            "unit": "completed_1h_bars",
            "semantic_role": "PARTICIPATION_REFERENCE_WINDOW",
            "first_known_repository_source": design_source,
            "first_known_commit": design_commit,
            "known_before_relevant_result_exposure": True,
            "provenance_status": "EX_ANTE_CONVENTION",
            "evidence": [
                design_source,
                "research/experiments/EXP-ALG-009-ALIGNED/preregistration.json",
            ],
            "notes": "Prior-day calendar interpretation; current volume is excluded.",
        },
        {
            "parameter_id": "ALIGNED_PARTICIPATION_THRESHOLD",
            "value": 2,
            "unit": "multiple_of_prior_24h_mean_base_volume",
            "semantic_role": "PARTICIPATION_GATE",
            "first_known_repository_source": design_source,
            "first_known_commit": design_commit,
            "known_before_relevant_result_exposure": True,
            "provenance_status": "EX_ANTE_CONVENTION",
            "evidence": [
                design_source,
                "research/experiments/EXP-ALG-009-ALIGNED/preregistration.json",
            ],
            "notes": "The design explicitly calls 2x a unit-based convention, not an estimated optimum.",
        },
        {
            "parameter_id": "ALIGNED_STOP",
            "value": 2,
            "unit": "percent_below_signal_reference",
            "semantic_role": "LOSS_BARRIER",
            "first_known_repository_source": baseline_source,
            "first_known_commit": baseline_commit,
            "known_before_relevant_result_exposure": True,
            "provenance_status": "INHERITED",
            "evidence": [
                design_source,
                "research/experiments/EXP-BASE-004-BREAKOUT/preregistration.json",
            ],
            "notes": "Frozen baseline barrier retained to isolate selection-gate evidence.",
        },
        {
            "parameter_id": "ALIGNED_TARGET",
            "value": 4,
            "unit": "percent_above_signal_reference",
            "semantic_role": "PROFIT_BARRIER",
            "first_known_repository_source": baseline_source,
            "first_known_commit": baseline_commit,
            "known_before_relevant_result_exposure": True,
            "provenance_status": "INHERITED",
            "evidence": [
                design_source,
                "research/experiments/EXP-BASE-004-BREAKOUT/preregistration.json",
            ],
            "notes": "Frozen baseline barrier retained to isolate selection-gate evidence.",
        },
        {
            "parameter_id": "ALIGNED_EXPIRY",
            "value": 24,
            "unit": "hours_from_entry",
            "semantic_role": "MAXIMUM_HOLDING_HORIZON",
            "first_known_repository_source": baseline_source,
            "first_known_commit": baseline_commit,
            "known_before_relevant_result_exposure": True,
            "provenance_status": "INHERITED",
            "evidence": [
                design_source,
                "research/experiments/EXP-BASE-004-BREAKOUT/preregistration.json",
            ],
            "notes": "Frozen baseline horizon; the rebaseline does not reinterpret or retune it.",
        },
    ]
    normalized = [normalize_provenance_entry(entry) for entry in entries]
    payload = {
        "schema_version": 1,
        "audit_id": "ALIGNED-CONSTANT-PROVENANCE-V1",
        "append_only": True,
        "historical_design_rewritten": False,
        "allowed_provenance_statuses": sorted(PROVENANCE_STATUSES),
        "parameters": normalized,
    }
    payload["parameters_sha256"] = canonical_hash(normalized)
    return payload


def render_ledger_markdown(ledger: Mapping[str, Any]) -> str:
    counts = ledger["counts"]
    lines = [
        "# Material Hypothesis Ledger V1",
        "",
        f"Known observed discovery family: **{ledger['known_family_size']}** material hypotheses.",
        f"Registered material hypotheses: **{ledger['registered_material_hypothesis_count']}**.",
        "",
        "`UNQUANTIFIED_PRE_REPO_EXPOSURE = true`: the documented count is a lower bound; no missing-trial estimate was invented.",
        "",
        "| Class | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in sorted(counts.items()))
    lines.extend(
        [
            "",
            "Profiles, folds, model fits, matched controls, configurations, and reproductions do not multiply the discovery family. WP016 is blocked and never observed; WP017 enters exactly once.",
            "",
            f"Events hash: `{ledger['events_sha256']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def render_provenance_markdown(audit: Mapping[str, Any]) -> str:
    lines = [
        "# ALIGNED Constant Provenance V1",
        "",
        "Append-only audit; the frozen design document is unchanged.",
        "",
        "| Parameter | Value | Status | First known commit |",
        "|---|---|---|---|",
    ]
    for item in audit["parameters"]:
        value = json.dumps(item["value"], sort_keys=True, separators=(",", ":"))
        lines.append(
            f"| {item['parameter_id']} | `{value}` | {item['provenance_status']} | `{item['first_known_commit']}` |"
        )
    lines.extend(["", f"Parameters hash: `{audit['parameters_sha256']}`"])
    return "\n".join(lines) + "\n"


def render_statistics_markdown(audit: Mapping[str, Any]) -> str:
    lines = [
        "# Statistical Evidence and Detectability Audit V1",
        "",
        f"Known documented family: **{audit['known_family_size']}**. Primary alpha: {audit['alpha']}; power target: {audit['power_target']}.",
        "",
        audit["holm_scope_limitation"],
        audit["dependence_inference_limitation"],
        "",
        "| Hypothesis | n | Mean net R | Raw p | Holm p | Status |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for item in audit["statistics"]:
        lines.append(
            "| {hypothesis_id} | {raw_trade_count} | {mean_net_R} | {unadjusted_p_value} | {holm_adjusted_p_value} | {statistical_status} |".format(
                **{key: ("—" if value is None else value) for key, value in item.items()}
            )
        )
    computed = sum(
        item["calculation_status"] == "COMPUTED_NO_HISTORICAL_MESI"
        for item in audit["detectability"]
    )
    lines.extend(
        [
            "",
            f"MDE computed for {computed} historical families; unavailable for {len(audit['detectability']) - computed}.",
            "MDE is not MESI. No historical MESI was invented and no historical classification changed.",
            "",
            f"Statistics hash: `{audit['statistics_sha256']}`",
            f"Detectability hash: `{audit['detectability_sha256']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


__all__ = [
    "BLOCKED_NEVER_OBSERVED",
    "CONFIGURATION",
    "COST_OR_DELAY_PROFILE",
    "MATCHED_CONTROL",
    "MATERIAL_ECONOMIC_HYPOTHESIS",
    "POWER_TARGET",
    "PRIMARY_ALPHA",
    "REPRODUCTION",
    "WALK_FORWARD_FIT",
    "StatisticalGovernanceError",
    "build_aligned_provenance_audit",
    "build_material_hypothesis_ledger",
    "build_repository_ledger",
    "compute_mde",
    "deterministic_student_t_sf",
    "holm_bonferroni",
    "json_bytes",
    "normalize_provenance_entry",
    "reconstruct_statistical_evidence",
    "render_ledger_markdown",
    "render_provenance_markdown",
    "render_statistics_markdown",
]
