"""Deterministic structural validation for the completed WP-007 checkpoint."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .continuation_lab import PROFILES
from .evaluation_protocol import load_protocol, terminal_classification, utc_us
from .records import validate_result
from .registry import cumulative_accounting, validate_budgets
from .report_guard import declared_base, validate_report_bases
from .runner import deterministic_run_identity, sha256
from .sealed_eligibility import build_eligibility_table
from .wp004 import ancestor, immutable_from_first_commit
from .wp007 import (
    ADMISSION_PATH,
    AMENDMENT_PATH,
    ATTEMPT_PATH,
    BASE,
    OUTCOMES_PATH,
    PRIMARY_VARIANT,
    ROOT,
    SPEC,
    effective_preregistration,
    git,
    read_json,
    substrate_gate,
    validate_admission,
    validate_allocation,
    validate_family_record,
    validate_identity,
    validate_ledger,
)
from .wp007_views import build_wp007_comparison


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_wp007(root: Path = ROOT) -> dict[str, Any]:
    branch = git("branch", "--show-current", root=root)
    require(
        branch == "main" or (not branch and os.environ.get("CLEAN_CHECKOUT") == "1"),
        "WP-007 must validate on main or a declared clean checkout",
    )
    head = git("rev-parse", "HEAD", root=root)
    require(ancestor(BASE, head, root), "required WP-007 base is not in ancestry")
    require(declared_base("WP-007", root) == BASE, "WP-007 declared base changed")
    report_guard = validate_report_bases(root, repo=root)
    substrate = substrate_gate(root)
    validate_allocation(root)
    validate_family_record(root)
    admission = validate_admission(root)
    counts = validate_ledger(root)
    validate_budgets(root)
    require(admission["family_classification"] == "NEW_FAMILY", "primary root was not admitted")
    require(
        counts
        == {"experiments": 2, "strategy_variants": 2, "trials": 8, "numeric_parameter_variants": 0},
        "WP-007 allocation accounting changed",
    )

    admission_commit = immutable_from_first_commit(ADMISSION_PATH, root)
    amendment_commit = immutable_from_first_commit(AMENDMENT_PATH, root)
    attempt = read_json(root / ATTEMPT_PATH)
    require(
        attempt["status"] == "PASS" and attempt["family_classification"] == "NEW_FAMILY",
        "execution preflight evidence failed",
    )
    require(attempt["admission_commit"] == admission_commit, "execution used another admission")
    require(
        attempt["trial_ids"]
        == [f"{variant}:{profile}" for variant in SPEC.values() for profile in PROFILES],
        "execution trial set changed",
    )

    outcomes = [
        json.loads(line)
        for line in (root / OUTCOMES_PATH).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    require([item["experiment_id"] for item in outcomes] == list(SPEC), "outcome ledger changed")
    classifications: dict[str, str] = {}
    result_commits: set[str] = set()
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    for outcome, (experiment_id, variant) in zip(outcomes, SPEC.items(), strict=True):
        directory = root / "research/experiments" / experiment_id
        require(
            {path.name for path in directory.iterdir()}
            == {"preregistration.json", "preregistration.v2.json", "trials.json", "result.json"},
            "undeclared WP-007 experiment artifact",
        )
        original_commit = immutable_from_first_commit(
            f"research/experiments/{experiment_id}/preregistration.json", root
        )
        effective = effective_preregistration(experiment_id, root)
        effective_commit = immutable_from_first_commit(effective.relative_to(root).as_posix(), root)
        result_commit = immutable_from_first_commit(
            (directory / "result.json").relative_to(root).as_posix(), root
        )
        require(
            all(
                ancestor(a, b, root)
                for a, b in (
                    (admission_commit, original_commit),
                    (original_commit, amendment_commit),
                    (amendment_commit, effective_commit),
                    (effective_commit, result_commit),
                )
            ),
            "WP-007 scientific chronology changed",
        )
        prereg = read_json(effective)
        require(prereg["experiment_version"] == 2, "effective preregistration version changed")
        validate_identity(prereg, root, validate_current_dependencies=False)
        require(
            attempt["dependency_manifest_sha256"]
            == hashlib.sha256(
                json.dumps(prereg["parameter_space"]["dependencies"], sort_keys=True).encode()
            ).hexdigest(),
            "execution dependency closure differs from the frozen preregistration",
        )
        result = validate_result(directory / "result.json", effective)
        require(
            utc_us(prereg["created_at_utc"])
            <= utc_us(attempt["started_at_utc"])
            <= utc_us(result["completed_at_utc"]),
            "WP-007 timestamps violate preregistration chronology",
        )
        trials = read_json(directory / "trials.json")
        require(
            len(trials) == 4 and [trial["profile"] for trial in trials] == list(PROFILES),
            "exact four-profile plan changed",
        )
        summaries = {trial["profile"]: trial["summary"] for trial in trials}
        require(
            result["primary_result"] == summaries["DEFAULT"]["metrics"]["net_expectancy_r"],
            "primary result does not follow DEFAULT",
        )
        classification = terminal_classification(
            summaries["DEFAULT"], summaries["ZERO"], summaries["DOUBLE"], protocol
        )
        require(
            result["secondary_results"]["terminal_classification"] == classification,
            "terminal rule changed",
        )
        require(result["secondary_results"]["profiles"] == summaries, "result summaries changed")
        require(
            result["run_identity_hash"]
            == deterministic_run_identity(
                prereg,
                attempt["execution_commit"],
                {"reference": prereg["code_config_reference"]},
                {
                    "engine": "BACKTEST_ENGINE_V2",
                    "execution": "EXECUTION_MODEL_V2",
                    "cost": "BTCUSDT_SPOT_COST_V1",
                },
            ),
            "run identity changed",
        )
        require(
            outcome["result_sha256"] == sha256(directory / "result.json")
            and outcome["terminal_classification"] == classification,
            "outcome linkage changed",
        )
        classifications[variant] = classification
        result_commits.add(result_commit)
    result_commits.add(immutable_from_first_commit(ATTEMPT_PATH, root))
    require(len(result_commits) == 1, "WP-007 result artifacts were not frozen together")
    require(
        classifications[PRIMARY_VARIANT] == "REJECT_COST_DOMINATED",
        "family conclusion must follow FLOW_CORE",
    )

    comparison_path = root / "reports/research/WP-007-COMPARISON.json"
    require(
        read_json(comparison_path) == json.loads(json.dumps(build_wp007_comparison(root))),
        "WP-007 comparison is not reproducible",
    )
    eligibility = build_eligibility_table(root)
    require(
        read_json(root / "research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json") == eligibility,
        "sealed eligibility is stale",
    )
    require(
        len(eligibility["candidates"]) >= 13
        and not any(
            item["sealed_eligibility"].startswith("DEVELOPMENT_ELIGIBLE")
            for item in eligibility["candidates"]
            if item["experiment_id"] in SPEC
        ),
        "sealed eligibility counters changed",
    )
    state = read_json(root / "state/current_state.json")
    require(
        state["experiments_completed"] >= 13
        and state["adaptive_search"] == cumulative_accounting(root),
        "current accounting differs from append-only records",
    )
    require(
        state["order_flow_substrate"]["content_hash"] == substrate["substrate_content_hash"],
        "state order-flow identity changed",
    )
    require(
        state["sealed_evaluation"]["authorized_btc_queries"]
        == state["sealed_evaluation"]["consumed_btc_queries"]
        == 0,
        "sealed query counter is nonzero",
    )
    require(
        state["sealed_evaluation"]["candidates_assessed"] >= 13
        and state["sealed_evaluation"]["seal_eligible_candidates"] == 0,
        "sealed state summary changed",
    )
    return {
        "status": "PASS",
        "head": head,
        "base": BASE,
        "substrate": substrate,
        "admission_commit": admission_commit,
        "preregistration_commit": attempt["preregistration_commit"],
        "result_commit": result_commits.pop(),
        "classifications": classifications,
        "family_terminal_classification": classifications[PRIMARY_VARIANT],
        "accounting": cumulative_accounting(root),
        "sealed": {"assessed": len(eligibility["candidates"]), "eligible": 0, "queries": 0},
        "report_base_guard": report_guard["base_guard_enforced"],
    }
