"""Result-free structural validation for preregistered WP-016."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from app.research.funding import FEATURE as FUNDING_FEATURE
from app.research.supervised import FULL_FEATURES
from app.research.wikimedia import FEATURE as ATTENTION_FEATURE
from app.research.wp014_model import HGBR_PARAMETERS
from app.research.wp016 import (
    CONTROL_VARIANT,
    EXPERIMENTS,
    PRIMARY_VARIANT,
    load_protocol,
    novelty_decision,
    preflight,
)
from app.research.wp016_lab import FUNDING_FEATURES, PRIMARY_FEATURES, AttentionContextLab

ROOT = Path(__file__).resolve().parents[2]


def test_frozen_protocol_adds_exactly_one_attention_feature() -> None:
    protocol = load_protocol(ROOT)
    assert protocol["internal_features"] == list(FULL_FEATURES)
    assert tuple(protocol["control_feature_order"]) == FUNDING_FEATURES
    assert tuple(protocol["primary_feature_order"]) == PRIMARY_FEATURES
    assert PRIMARY_FEATURES == (*FULL_FEATURES, FUNDING_FEATURE, ATTENTION_FEATURE)
    assert protocol["hgbr_parameters"] == HGBR_PARAMETERS
    assert protocol["folds"] == [2020, 2021, 2022, 2023, 2024]
    assert protocol["profiles"] == ["DEFAULT", "ZERO", "DOUBLE", "DELAY_1H"]
    assert protocol["budget"] == {
        "hypotheses": 1,
        "configurations": 2,
        "profile_evaluations": 8,
        "model_fits": 10,
        "attention_windows": 0,
        "article_variants": 0,
        "transform_variants": 0,
        "threshold_variants": 0,
        "algorithm_variants": 0,
        "hyperparameter_variants": 0,
        "feature_subsets": 0,
        "result_dependent_forks": 0,
    }


def test_admission_and_preflight_exist_before_any_result() -> None:
    admission = novelty_decision(ROOT)
    primary, control = admission["variants"]
    assert primary["variant"] == PRIMARY_VARIANT
    assert primary["classification"] == "NEW_FAMILY" and primary["admitted"] is True
    assert control["variant"] == CONTROL_VARIANT
    assert control["classification"] == "KNOWN_FUNDING_HGBR_MATCHED_CONTROL"
    assert control["authorized_as_matched_control"] is True
    gate = preflight(ROOT)
    assert gate["status"] == "PASS"
    assert gate["market_results_observed"] == gate["model_fits_executed"] == 0
    assert gate["post_cutoff_access"] == gate["sealed_queries"] == 0
    assert gate["matched_eligible_universe"] is True
    assert not any(
        (ROOT / "research/experiments" / experiment / "result.json").exists()
        for experiment in EXPERIMENTS.values()
    )


def test_committed_attention_audit_is_metadata_only_and_leakage_safe() -> None:
    audit = json.loads(
        (ROOT / "reports/validation/WP-016-WIKIMEDIA-ATTENTION-AUDIT.json").read_text()
    )
    assert audit["status"] == "PASS" and audit["market_results_observed"] is False
    assert audit["records_rebuilt"] == 3472
    assert audit["post_cutoff_rows"] == audit["duplicates"] == audit["missing_days"] == 0
    assert audit["complete_validation_folds"] == [2020, 2021, 2022, 2023, 2024]
    assert set(audit["checks"].values()) == {"PASS"}


def test_lab_source_has_no_alternative_attention_or_tuning_paths() -> None:
    source = inspect.getsource(AttentionContextLab).lower()
    assert all(
        forbidden not in source
        for forbidden in (
            "google",
            "reddit",
            "news",
            "zscore",
            "clip(",
            "gridsearch",
            "early_stopping=true",
        )
    )
