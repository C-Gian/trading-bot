"""The committed baseline report matches the frozen protocol and its own arithmetic.

These run without the market data installed, so they also guard the report in CI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.predictive import PREDICTIVE_FOUNDATION_VERSION, PROTOCOL_PATH
from app.predictive.baselines import (
    ALWAYS_UP,
    BASELINE_NAMES,
    DECLARATIONS,
    PREVIOUS_24H_SIGN_PERSISTENCE,
    TRAINING_UP_BASE_RATE,
    ZERO_RETURN_MAGNITUDE,
)
from app.predictive.evaluation import (
    BLOCK_LENGTH_HOURS,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    MAGNITUDE_EXCLUSIONS,
)
from app.predictive.labels import EXCLUSION_TAXONOMY
from app.predictive.report import REPORT_PATH, load_report, validate_report

ROOT = Path(__file__).resolve().parents[2]
REPORT = load_report(ROOT)
PROTOCOL = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))


def test_the_committed_report_validates_against_the_frozen_protocol() -> None:
    findings = validate_report(ROOT, data_available=False)
    assert findings["status"] == "PASS"
    assert findings["data_replayed"] is False


def test_the_protocol_was_frozen_before_observation() -> None:
    assert PROTOCOL["status"] == "FROZEN_BEFORE_OBSERVATION"
    assert PROTOCOL["model_fits"] == 0
    assert PROTOCOL["sealed_queries"] == 0
    assert PROTOCOL["predictive_hypothesis_tested"] is False
    assert PROTOCOL["candidate_created"] is False
    assert PROTOCOL["evaluation_contract_amendment"] == "A1"


def test_the_report_is_a_reference_not_a_result() -> None:
    assert REPORT["version"] == PREDICTIVE_FOUNDATION_VERSION
    assert REPORT["classification"] == "BASELINE_REFERENCE_REPORT_NOT_AN_EXPERIMENT_RESULT"
    boundaries = REPORT["boundaries"]
    assert boundaries["model_fits"] == 0
    assert boundaries["sealed_queries"] == 0
    assert boundaries["parameter_search"] is False
    assert boundaries["external_data"] is False
    assert boundaries["post_cutoff_market_data"] is False
    assert boundaries["champion_created"] is False
    assert boundaries["baseline_promoted_to_candidate"] is False
    assert boundaries["real_money"] is False


def test_the_label_accounting_closes_and_is_fully_typed() -> None:
    labels = REPORT["labels"]
    assert set(labels["exclusions"]) == set(EXCLUSION_TAXONOMY)
    assert sum(labels["exclusions"].values()) == labels["excluded_total"]
    assert (
        labels["admissible_labels"] + labels["excluded_total"] == (labels["grid_decision_instants"])
    )
    assert sum(labels["direction_counts"].values()) == labels["admissible_labels"]
    assert labels["direction_counts"]["NEUTRAL"] >= 0


def test_the_fold_assignment_closes() -> None:
    folds = REPORT["folds"]
    assert folds["random_k_fold"] is False
    assert folds["purge_embargo_hours"] == PROTOCOL["folds"]["purge_embargo_hours"]
    per_fold = sum(item["eligible_decision_timestamps"] for item in folds["by_fold"].values())
    assert per_fold == folds["eligible_decision_timestamps"]
    assert (
        per_fold + sum(folds["admissible_not_assigned"].values())
        == (REPORT["labels"]["admissible_labels"])
    )
    assert list(folds["by_fold"]) == ["2019", "2020", "2021", "2022", "2023", "2024"]


def test_the_scoring_parameters_are_the_frozen_ones() -> None:
    bootstrap = REPORT["scoring"]["bootstrap"]
    assert bootstrap["method"] == "MOVING_BLOCK_BOOTSTRAP"
    assert bootstrap["block_length_hours"] == BLOCK_LENGTH_HOURS == 48
    assert bootstrap["replicates"] == BOOTSTRAP_REPLICATES == 10_000
    assert bootstrap["seed"] == BOOTSTRAP_SEED == 20260916
    assert (
        REPORT["scoring"]["reliability_bin_edges"] == PROTOCOL["scoring"]["reliability_bin_edges"]
    )


def test_every_baseline_is_scored_on_the_identical_eligible_universe() -> None:
    eligible = REPORT["folds"]["eligible_decision_timestamps"]
    assert set(REPORT["baselines"]) == set(BASELINE_NAMES)
    for name, record in REPORT["baselines"].items():
        assert record["pooled"]["eligible_decision_timestamps"] == eligible, name
        by_fold = record["by_fold"]
        assert set(by_fold) == set(REPORT["folds"]["by_fold"])
        for fold, scored in by_fold.items():
            assert (
                scored["eligible_decision_timestamps"]
                == (REPORT["folds"]["by_fold"][fold]["eligible_decision_timestamps"])
            )


def test_declared_quantities_match_the_contract_for_every_baseline() -> None:
    for name, record in REPORT["baselines"].items():
        assert record["declares"] == DECLARATIONS[name], name


@pytest.mark.parametrize("name", [ALWAYS_UP, PREVIOUS_24H_SIGN_PERSISTENCE])
def test_deterministic_baselines_carry_no_calibration(name: str) -> None:
    pooled = REPORT["baselines"][name]["pooled"]
    assert pooled["probability_flag"] == "PROBABILITY_NOT_DECLARED"
    assert pooled["brier_score"] is None
    assert pooled["reliability_table"] is None
    assert pooled["win_rate"] is not None and pooled["coverage"] is not None


def test_the_probabilistic_baseline_is_calibrated_and_declares_a_majority_side() -> None:
    record = REPORT["baselines"][TRAINING_UP_BASE_RATE]
    assert record["pooled"]["brier_score"] is not None
    assert record["pooled"]["reliability_table"] is not None
    for fold, scored in record["by_fold"].items():
        fit = scored["fit"]
        assert fit["declared_direction"] in {"UP", "DOWN"}, fold
        expected = fit["p_up"] if fit["declared_direction"] == "UP" else 1 - fit["p_up"]
        assert fit["probability"] == pytest.approx(expected), fold
        assert fit["probability"] >= 0.5, fold
        decided = fit["training_up_labels"] + fit["training_down_labels"]
        assert fit["p_up"] == pytest.approx(fit["training_up_labels"] / decided), fold
        assert scored["training_labels"] >= decided, fold


def test_the_magnitude_baseline_has_no_direction_and_closes_its_exclusions() -> None:
    pooled = REPORT["baselines"][ZERO_RETURN_MAGNITUDE]["pooled"]
    assert pooled["direction_flag"] == "DIRECTION_NOT_DECLARED"
    assert pooled["win_rate"] is None and pooled["coverage"] is None
    assert pooled["magnitude_mae_percentage_points"] > 0
    assert set(pooled["magnitude_match_exclusions"]) == set(MAGNITUDE_EXCLUSIONS)
    excluded = sum(pooled["magnitude_match_exclusions"].values())
    assert excluded + pooled["magnitude_match_included"] == (pooled["eligible_decision_timestamps"])
    assert pooled["magnitude_match_included"] == 0
    assert pooled["magnitude_match_mean"] is None


def test_the_dependence_aware_interval_is_wider_than_the_naive_reference() -> None:
    for name in (ALWAYS_UP, PREVIOUS_24H_SIGN_PERSISTENCE, TRAINING_UP_BASE_RATE):
        pooled = REPORT["baselines"][name]["pooled"]
        block = pooled["win_rate_interval_moving_block"]
        naive = pooled["win_rate_interval_naive_wilson_optimistic_reference"]
        assert block[1] - block[0] > naive[1] - naive[0], name


def test_every_fold_is_reported_including_unfavourable_ones() -> None:
    always_up = REPORT["baselines"][ALWAYS_UP]["by_fold"]
    assert all(scored["win_rate"] is not None for scored in always_up.values())
    assert any(scored["win_rate"] < 0.5 for scored in always_up.values()), (
        "an unfavourable fold must not have been dropped"
    )


def test_the_human_report_exists_and_declares_its_classification() -> None:
    text = (ROOT / "reports/research/PREDICTIVE-BASELINES-V1.md").read_text(encoding="utf-8")
    assert "baseline reference report, not an experiment result" in text
    assert "Champion `NONE`" in text
    assert (ROOT / REPORT_PATH).is_file()
