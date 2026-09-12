"""Deterministic structural and installed-data validation for completed WP-008."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .artifacts import ARTIFACT_STORAGE_VERSION, validate_parquet
from .continuation_lab import PROFILES
from .evaluation_protocol import terminal_classification
from .linear_lab import TRIAL_SCHEMA
from .model_reconciliation import reconcile
from .records import validate_result
from .registry import all_families, cumulative_accounting, validate_budgets
from .sealed_eligibility import build_eligibility_table
from .supervised import CONFIG_FEATURES, FEATURE_VERSION, LABEL_VERSION, load_supervised_protocol
from .wp004 import ROOT, ancestor, first_commit, git, immutable_from_first_commit
from .wp008 import (
    ADMISSION_PATH,
    ALLOCATION_PATH,
    ATTEMPT_PATH,
    BASE,
    OUTCOMES_PATH,
    PRIMARY_VARIANT,
    SPEC,
    SPEC_DEPENDENCY_PATHS,
    read_json,
    validate_admission,
    validate_allocation,
    validate_identity,
    validate_ledger,
)
from .wp008_views import build_wp008_comparison


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _historical_experiments_unchanged(root: Path) -> int:
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", BASE, "--", "research/experiments"],
        cwd=root,
        text=True,
    ).splitlines()
    for relative in paths:
        baseline = git("rev-parse", f"{BASE}:{relative}", root=root)
        current = git("hash-object", relative, root=root)
        require(current == baseline, f"historical experiment evidence changed: {relative}")
    return len(paths)


def validate_wp008(root: Path = ROOT) -> dict[str, Any]:
    branch = git("branch", "--show-current", root=root)
    require(
        branch == "main" or (not branch and os.environ.get("CLEAN_CHECKOUT") == "1"),
        "WP-008 must validate on main or a declared clean checkout",
    )
    head = git("rev-parse", "HEAD", root=root)
    require(ancestor(BASE, head, root), "accepted WP-007 HEAD is not in ancestry")
    review = (root / "reports/reviews/WP-007-RESEARCH-DIRECTOR-REVIEW.md").read_text(
        encoding="utf-8"
    )
    ci = read_json(root / "reports/reviews/WP-007-CI-EVIDENCE.json")
    require("ACCEPTED" in review and BASE in review, "WP-007 acceptance is missing")
    require(
        ci["run_id"] == 34375244463
        and ci["reviewed_head"] == BASE
        and ci["conclusion"] == "success"
        and ci["branch"] == "main",
        "WP-007 remote CI evidence changed",
    )
    historical_files = _historical_experiments_unchanged(root)
    protocol = load_supervised_protocol(root)
    admission = validate_admission(root)
    allocation = validate_allocation(root)
    counts = validate_ledger(root)
    validate_budgets(root)
    require(admission["family_classification"] == "NEW_FAMILY", "primary was not NEW_FAMILY")
    require(
        [item["classification"] for item in admission["variants"]]
        == ["NEW_FAMILY", "DESCENDANT_MECHANISM_CHANGE"],
        "fixed novelty decisions changed",
    )
    require(
        counts
        == {"experiments": 2, "strategy_variants": 2, "trials": 8, "numeric_parameter_variants": 0},
        "WP-008 allocation accounting changed",
    )
    admission_commit = immutable_from_first_commit(ADMISSION_PATH, root)
    allocation_commit = immutable_from_first_commit(ALLOCATION_PATH, root)
    require(admission_commit == allocation_commit, "admission/allocation were not frozen together")
    for dependency in SPEC_DEPENDENCY_PATHS:
        commit = first_commit(dependency, root)
        require(
            commit != admission_commit and ancestor(commit, admission_commit, root),
            "model implementation/spec did not precede admission",
        )
    attempt = read_json(root / ATTEMPT_PATH)
    require(attempt["status"] == "PASS", "execution preflight did not pass")
    require(attempt["admission_commit"] == admission_commit, "execution used another admission")
    prereg_commits = set()
    result_commits = set()
    classifications = {}
    for experiment_id, variant in SPEC.items():
        directory = root / "research/experiments" / experiment_id
        require(
            {path.name for path in directory.iterdir()}
            == {
                "preregistration.json",
                "result.json",
                "trials.parquet",
                "artifact-manifest.json",
                "training-manifests.json",
                "fold-models.json",
            },
            "undeclared WP-008 experiment artifact",
        )
        prereg_path = directory / "preregistration.json"
        prereg = validate_result(directory / "result.json", prereg_path)
        validate_identity(read_json(prereg_path), root, validate_current_dependencies=False)
        prereg_commit = immutable_from_first_commit(prereg_path.relative_to(root).as_posix(), root)
        result_commit = immutable_from_first_commit(
            (directory / "result.json").relative_to(root).as_posix(), root
        )
        require(
            admission_commit != prereg_commit
            and ancestor(admission_commit, prereg_commit, root)
            and git("rev-parse", f"{result_commit}^", root=root) == prereg_commit,
            "implementation/admission/preregistration/result chronology changed",
        )
        prereg_commits.add(prereg_commit)
        result_commits.add(result_commit)
        secondary = prereg["secondary_results"]
        profiles = secondary["profiles"]
        require(set(profiles) == set(PROFILES), "exact four-profile set changed")
        require(
            secondary["execution_provenance"]["model_fits"] == 6
            and secondary["execution_provenance"]["stress_profile_refits"] == 0,
            "model fit accounting or stress-profile reuse changed",
        )
        expected_features = list(CONFIG_FEATURES[variant])
        require(
            len(secondary["fold_models"]) == len(secondary["training_manifests"]) == 6,
            "each configuration requires six fits/manifests",
        )
        for model, manifest in zip(
            secondary["fold_models"], secondary["training_manifests"], strict=True
        ):
            require(
                model["feature_order"] == manifest["feature_order"] == expected_features
                and model["full_rank"]
                and model["rank"] == len(expected_features) + 1
                and model["regularization"] == "NONE"
                and model["hyperparameters_searched"] == 0
                and model["thresholds_searched"] == 0
                and model["signal_threshold"] == 0.0,
                "model rank/order/no-tuning declaration changed",
            )
            require(
                manifest["max_training_label_outcome_us"] < manifest["validation_start_us"]
                and manifest["validation_start_us"] - manifest["purge_boundary_exclusive_us"]
                == 216 * 3_600_000_000
                and not manifest["training_rows_committed"],
                "training outcome containment or matrix policy changed",
            )
        artifact_manifest = secondary["artifact_manifest"]
        require(
            artifact_manifest == read_json(directory / "artifact-manifest.json")
            and artifact_manifest["artifact_storage_version"] == ARTIFACT_STORAGE_VERSION
            and artifact_manifest["format"] == "PARQUET_ZSTD",
            "compact artifact manifest changed",
        )
        validate_parquet(artifact_manifest, schema=TRIAL_SCHEMA, root=root)
        require(not (directory / "trials.json").exists(), "WP-008 emitted row-level JSON trials")
        summaries = {name: item["summary"] for name, item in profiles.items()}
        classification = terminal_classification(
            summaries["DEFAULT"],
            summaries["ZERO"],
            summaries["DOUBLE"],
            json.loads((root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json").read_text()),
        )
        require(
            prereg["primary_result"] == summaries["DEFAULT"]["metrics"]["net_expectancy_r"]
            and secondary["terminal_classification"] == classification,
            "primary result/classification changed",
        )
        classifications[variant] = classification
    require(len(prereg_commits) == len(result_commits) == 1, "WP-008 freeze commits split")
    result_commit = result_commits.pop()
    prereg_commit = prereg_commits.pop()
    require(
        immutable_from_first_commit(ATTEMPT_PATH, root) == result_commit,
        "attempt and results were not frozen together",
    )
    recorded_dependency_sets = [
        {item["path"]: item["sha256"] for item in variant["spec"]["implementation_dependencies"]}
        for variant in admission["variants"]
    ]
    for dependency in SPEC_DEPENDENCY_PATHS:
        recorded_hashes = {items[dependency] for items in recorded_dependency_sets}
        require(len(recorded_hashes) == 1, f"recorded dependency identity split: {dependency}")
        result_content = subprocess.check_output(
            ["git", "show", f"{result_commit}:{dependency}"], cwd=root
        )
        require(
            hashlib.sha256(result_content).hexdigest() == recorded_hashes.pop(),
            f"result-time dependency differs from admitted identity: {dependency}",
        )
    require(
        classifications[PRIMARY_VARIANT] == "REJECT_COST_DOMINATED",
        "family must follow the preselected LINEAR_FULL primary",
    )
    reconciliation = read_json(root / "reports/validation/WP-008-MODEL-RECONCILIATION.json")
    leakage = read_json(root / "reports/validation/WP-008-SUPERVISED-LEAKAGE-AUDIT.json")
    require(
        reconciliation["status"] == leakage["status"] == "PASS"
        and all(value == "PASS" for value in reconciliation["checks"].values()),
        "independent model/leakage audit did not pass",
    )
    require(
        read_json(root / "reports/research/WP-008-COMPARISON.json")
        == json.loads(json.dumps(build_wp008_comparison(root))),
        "WP-008 comparison is not reproducible",
    )
    outcomes = [
        json.loads(line)
        for line in (root / OUTCOMES_PATH).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    require([item["experiment_id"] for item in outcomes] == list(SPEC), "outcomes changed")
    eligibility = build_eligibility_table(root)
    require(
        read_json(root / "research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json") == eligibility
        # The table grows as later families are recorded; WP-008 owns only the invariant
        # that every assessed candidate stays sealed-ineligible.
        and len(eligibility["candidates"]) >= 15
        and not any(
            item["sealed_eligibility"].startswith("DEVELOPMENT_ELIGIBLE")
            for item in eligibility["candidates"]
        ),
        "sealed eligibility changed",
    )
    state = read_json(root / "state/current_state.json")
    require(
        # Later work packages legitimately add experiments and root families; what
        # WP-008 guards is that state stays consistent with the append-only records.
        state["experiments_completed"] >= 15
        and state["adaptive_search"] == cumulative_accounting(root)
        and state["search_memory"]["families_tracked"] == len(all_families(root)) >= 8,
        "state/search accounting differs from append-only records",
    )
    require(
        state["supervised_challenger"]["model_fits"] == 12
        and state["supervised_challenger"]["terminal_classification"]
        == classifications[PRIMARY_VARIANT]
        and state["artifact_storage"]["historical_evidence_rewritten"] is False,
        "state does not expose the validated supervised/artifact status",
    )
    require(
        state["sealed_evaluation"]["authorized_btc_queries"]
        == state["sealed_evaluation"]["consumed_btc_queries"]
        == state["sealed_evaluations_completed"]
        == state["paper_trades_completed"]
        == 0
        and state["champion_status"] == state["forward_evidence"] == "NONE"
        and not state["real_money_authorized"],
        "forbidden promotion or access occurred",
    )
    forbidden_training_rows = [
        path
        for path in (root / "research/experiments").rglob("*")
        if path.is_file()
        and any(token in path.name.lower() for token in ("training-matrix", "training-labels"))
    ]
    require(not forbidden_training_rows, "row-by-row training matrix/labels were committed")
    require(
        # WP-008 owns its own archived task, not whichever work package currently
        # occupies CURRENT_TASK.md.
        (root / "tasks/archive/WP-008.md").is_file()
        and "## STATUS\nCOMPLETED"
        in (root / "tasks/archive/WP-008.md").read_text(encoding="utf-8").replace("\r\n", "\n")
        and (root / "reports/checkpoints/WP-008.md").is_file(),
        "WP-008 task/checkpoint archive is incomplete",
    )
    return {
        "status": "PASS",
        "head": head,
        "base": BASE,
        "historical_experiment_files_unchanged": historical_files,
        "protocol": protocol["protocol_id"],
        "feature_version": FEATURE_VERSION,
        "label_version": LABEL_VERSION,
        "admission_commit": admission_commit,
        "preregistration_commit": prereg_commit,
        "result_commit": result_commit,
        "classifications": classifications,
        "model_fits": allocation["supervised_model_fits"],
        "profile_trials": allocation["profile_evaluations"],
        "sealed": {"assessed": 15, "eligible": 0, "queries": 0},
    }


def validate_installed_data_reconciliation(root: Path = ROOT) -> dict[str, Any]:
    reconciliation, leakage = reconcile(root)
    require(
        reconciliation == read_json(root / "reports/validation/WP-008-MODEL-RECONCILIATION.json"),
        "installed-data model reconciliation changed",
    )
    require(
        leakage == read_json(root / "reports/validation/WP-008-SUPERVISED-LEAKAGE-AUDIT.json"),
        "installed-data leakage audit changed",
    )
    return {"status": "PASS", "model_fits": 12}
