"""Deterministic structural and installed-data validation for WP-009."""

from __future__ import annotations

import ast
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .exogenous import (
    ALFRED_SERIES,
    GDELT_CHANNELS,
    hours,
    validate_catalogs,
)
from .registry import cumulative_accounting, directions
from .wp004 import ROOT

WP008_HEAD = "ffeb73d6c0799ccfc09d0ee3b85c25d8e52364c2"
WP008_BASE = "762b3b77f686305b1c73f19956d0b9b16b7a9b1c"
WP008_PREREG = "2d8bc11b2bbc76db387652804f7ad8c492e3d493"
WP008_RESULT = "88e9c6e941be54b2fe65b802e15312eadc01c7ec"


class WP009ValidationError(ValueError):
    """The exogenous foundation differs from its frozen authority."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise WP009ValidationError(message)


def _read(relative: str, root: Path) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def _creation_commit(root: Path, relative: str) -> str:
    commits = _git(root, "log", "--diff-filter=A", "--format=%H", "--", relative).splitlines()
    _require(bool(commits), f"missing Git creation commit for {relative}")
    return commits[-1]


def _ancestor(root: Path, earlier: str, later: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", earlier, later],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )


def _no_market_dependency(root: Path) -> None:
    paths = [
        "backend/app/research/exogenous.py",
        "backend/app/research/gdelt.py",
        "backend/app/research/alfred.py",
        "backend/app/research/exogenous_context.py",
        "backend/app/research/exogenous_oracle.py",
    ]
    forbidden_modules = {
        "app.data.store",
        "app.backtest",
        "app.research.runner",
        "app.research.supervised",
    }
    for relative in paths:
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        _require(not imports.intersection(forbidden_modules), f"market dependency in {relative}")


def validate_wp009(root: Path = ROOT, *, data_available: bool = False) -> dict[str, Any]:
    catalogs = validate_catalogs(root)
    _require(len(catalogs["gdelt"]["channels"]) == 5, "GDELT channel count changed")
    _require(len(catalogs["alfred"]["series"]) == 8, "ALFRED series count changed")
    _require(
        tuple(GDELT_CHANNELS) == tuple(x["channel_id"] for x in catalogs["gdelt"]["channels"]),
        "GDELT channel order changed",
    )
    _require(
        tuple(ALFRED_SERIES) == tuple(x["series_id"] for x in catalogs["alfred"]["series"]),
        "ALFRED series order changed",
    )

    required = [
        "reports/reviews/WP-008-RESEARCH-DIRECTOR-REVIEW.md",
        "reports/reviews/WP-008-CI-EVIDENCE.json",
        "docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md",
        "research/exogenous/SOURCE_CATALOG_V1.json",
        "research/exogenous/GDELT_QUERY_CATALOG_V1.json",
        "research/exogenous/ALFRED_SERIES_CATALOG_V1.json",
        "research/exogenous/GDELT-ACQUISITION-AMENDMENT-V1.json",
        "research/exogenous/ALFRED-ACQUISITION-AMENDMENT-V1.json",
        "research/exogenous/ALFRED-SINGLE-VINTAGE-FALLBACK-V1.json",
        "research/exogenous/ALFRED-SINGLE-VINTAGE-FALLBACK-CORRECTION-V1.json",
        "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json",
        "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json",
        "data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json",
        "reports/validation/WP-009-GDELT-INTEGRITY.json",
        "reports/validation/WP-009-ALFRED-INTEGRITY.json",
        "reports/validation/WP-009-EXOGENOUS-ASOF-RECONCILIATION.json",
        "reports/research/WP-009-EXOGENOUS-COVERAGE.md",
        "reports/research/WP-009-EXOGENOUS-FOUNDATION.md",
        "research/design/ADAPTIVE_MULTISIGNAL_ARCHITECTURE_OPTIONS_V1.md",
        "docs/contracts/DYNAMIC_SIGNAL_IMPORTANCE_GOVERNANCE_V1.md",
        "research/memory/registry/directions/WP009-EXOGENOUS-AND-DYNAMIC-MULTISIGNAL-FOUNDATION.json",
        "reports/checkpoints/WP-009.md",
        "tasks/archive/WP-009.md",
    ]
    _require(all((root / path).is_file() for path in required), "WP-009 artifact set incomplete")

    review = (root / required[0]).read_text(encoding="utf-8")
    ci = _read(required[1], root)
    _require(
        "ACCEPTED" in review and WP008_HEAD in review and WP008_BASE in review,
        "WP-008 review identity mismatch",
    )
    _require(
        ci["run_id"] == 34392236263
        and ci["conclusion"] == "success"
        and ci["reviewed_head"] == WP008_HEAD,
        "WP-008 CI evidence mismatch",
    )
    _require(
        _git(root, "rev-parse", f"{WP008_RESULT}^") == WP008_PREREG,
        "WP-008 prereg/result direct-parent chronology failed",
    )

    gdelt_manifest = _read("data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json", root)
    alfred_manifest = _read("data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json", root)
    context_manifest = _read("data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json", root)
    gdelt_integrity = _read("reports/validation/WP-009-GDELT-INTEGRITY.json", root)
    alfred_integrity = _read("reports/validation/WP-009-ALFRED-INTEGRITY.json", root)
    oracle = _read("reports/validation/WP-009-EXOGENOUS-ASOF-RECONCILIATION.json", root)
    _require(
        gdelt_integrity["status"] == alfred_integrity["status"] == oracle["status"] == "PASS",
        "exogenous integrity/oracle failed",
    )
    _require(gdelt_manifest["hourly_rows"] == len(hours()) * 5, "GDELT row count changed")
    _require(len(gdelt_manifest["requests"]) == 3850, "GDELT request count changed")
    _require(
        gdelt_manifest["coverage"]["end"] == "2024-12-31T23:59:59+00:00", "GDELT cutoff changed"
    )
    _require(
        gdelt_manifest["timeline_smooth"] == 0 and not gdelt_manifest["article_bodies_acquired"],
        "GDELT smoothing/body policy failed",
    )
    _require(gdelt_manifest["response_resolutions"] == ["hour"], "GDELT resolution changed")
    _require(
        all(
            item["end_utc"] <= "2024-12-31T23:59:59Z"
            and len(item["request_id"]) == len(item["response_sha256"]) == 64
            and len(item["compressed_file_sha256"]) == 64
            and item["date_resolution"] == "hour"
            for item in gdelt_manifest["requests"]
        ),
        "GDELT request identity/hash/bound changed",
    )
    _require(alfred_manifest["request_count"] == 8 * 2694, "ALFRED vintage request count changed")
    gaps = alfred_manifest["source_unavailable_requests"]
    _require(
        alfred_manifest["successful_request_count"] == 8 * 2694 - 1
        and alfred_manifest["source_unavailable_request_count"] == len(gaps) == 1
        and gaps[0]["series_id"] == "VIXCLS"
        and gaps[0]["vintage_date"] == "2018-01-23"
        and gaps[0]["request_id"]
        == "f2706372e45ba9585bad7b22ae032da008f90155452ecacbe7548fdcb265eb3e"
        and gaps[0]["classification"] == "SOURCE_VINTAGE_UNAVAILABLE_NO_OBSERVATIONS"
        and gaps[0]["primary_http_status"] == 404
        and all(
            len(gaps[0][key]) == 64
            for key in (
                "primary_response_sha256",
                "fallback_response_sha256",
                "fallback_file_sha256",
            )
        ),
        "ALFRED explicit source gap changed",
    )
    _require(alfred_manifest["coverage"]["vintage_end"] == "2024-12-31", "ALFRED cutoff changed")
    _require(
        not alfred_manifest["current_revised_substitution"],
        "current revised macro substitution detected",
    )
    _require(context_manifest["rows"] == len(hours()), "combined context row count changed")
    _require(
        context_manifest["grid_source"] == "TIMESTAMP_GENERATION_ONLY",
        "context grid is not timestamp-only",
    )
    _require(
        not context_manifest["btc_price_return_or_outcome_columns_loaded"],
        "BTC outcome dependency detected",
    )
    _require(
        not context_manifest["full_history_standardization"]
        and not context_manifest["trading_score"],
        "undeclared transformation or score detected",
    )
    _require(
        context_manifest["post_2024_rows"]
        == gdelt_manifest["post_2024_rows"]
        == alfred_manifest["post_2024_vintages"]
        == 0,
        "post-cutoff exogenous data detected",
    )
    _no_market_dependency(root)

    catalog_commit = _creation_commit(root, "research/exogenous/GDELT_QUERY_CATALOG_V1.json")
    series_commit = _creation_commit(root, "research/exogenous/ALFRED_SERIES_CATALOG_V1.json")
    gdelt_amendment_commit = _creation_commit(
        root, "research/exogenous/GDELT-ACQUISITION-AMENDMENT-V1.json"
    )
    alfred_amendment_commit = _creation_commit(
        root, "research/exogenous/ALFRED-ACQUISITION-AMENDMENT-V1.json"
    )
    alfred_fallback_commit = _creation_commit(
        root, "research/exogenous/ALFRED-SINGLE-VINTAGE-FALLBACK-CORRECTION-V1.json"
    )
    gdelt_result_commit = _creation_commit(root, "data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json")
    alfred_result_commit = _creation_commit(root, "data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json")
    _require(
        all(
            _ancestor(root, earlier, gdelt_result_commit) and earlier != gdelt_result_commit
            for earlier in (catalog_commit, gdelt_amendment_commit)
        ),
        "GDELT catalog/amendment did not precede results",
    )
    _require(
        all(
            _ancestor(root, earlier, alfred_result_commit) and earlier != alfred_result_commit
            for earlier in (series_commit, alfred_amendment_commit, alfred_fallback_commit)
        ),
        "ALFRED catalog/amendments did not precede results",
    )
    _require(
        not _git(root, "diff", "--name-only", WP008_HEAD, "HEAD", "--", "research/experiments"),
        "WP-009 altered strategy experiments",
    )

    direction = directions(root)
    _require(
        len([item for item in direction if item["work_package"] == "WP-009"]) == 1,
        "WP-009 direction accounting missing",
    )
    totals = cumulative_accounting(root)
    expected = {
        "material_economic_hypotheses": 6,
        "configuration_variants": 15,
        "profile_trials": 77,
        "supervised_model_fits": 12,
        "numeric_parameter_variants": 0,
        "adaptive_decisions": 6,
        "result_dependent_forks": 6,
        "sealed_queries": 0,
    }
    _require(
        all(totals[key] == value for key, value in expected.items()),
        "WP-009 scientific accounting changed",
    )
    state = _read("state/current_state.json", root)
    _require(state["adaptive_search"] == totals, "state search accounting is stale")
    _require(
        state["experiments_completed"] == 15
        and state["sealed_evaluations_completed"] == state["paper_trades_completed"] == 0,
        "forbidden experiment/sealed/paper counter changed",
    )
    _require(
        state["latest_reviewed_checkpoint"] == "WP-008"
        and state["latest_executor_checkpoint"] == "WP-009",
        "checkpoint state stale",
    )
    _require(
        state["champion_status"] == state["forward_evidence"] == "NONE"
        and not state["real_money_authorized"],
        "safety state changed",
    )
    _require(
        "## STATUS\nCOMPLETED"
        in (root / "tasks/CURRENT_TASK.md").read_text(encoding="utf-8").replace("\r\n", "\n"),
        "task not completed",
    )
    _require(
        (root / "tasks/CURRENT_TASK.md").read_bytes().replace(b"\r\n", b"\n")
        == (root / "tasks/archive/WP-009.md").read_bytes().replace(b"\r\n", b"\n"),
        "task archive differs",
    )

    if data_available:
        from .alfred import validate as validate_alfred
        from .exogenous_context import validate as validate_context
        from .exogenous_oracle import reconcile
        from .gdelt import validate as validate_gdelt

        _require(validate_gdelt(root)["status"] == "PASS", "GDELT deterministic rebuild failed")
        _require(validate_alfred(root)["status"] == "PASS", "ALFRED deterministic rebuild failed")
        _require(
            validate_context(root)["version"] == "EXOGENOUS_CONTEXT_V1",
            "context deterministic rebuild failed",
        )
        _require(reconcile(root) == oracle, "independent oracle report differs from replay")

    return {
        "status": "PASS",
        "gdelt_rows": gdelt_manifest["hourly_rows"],
        "context_rows": context_manifest["rows"],
        "oracle_samples": oracle["sample_count"],
        "data_replayed": data_available,
    }


def clean_checkout_allowed() -> bool:
    return os.environ.get("CLEAN_CHECKOUT") == "1"
