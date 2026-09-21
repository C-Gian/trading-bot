"""The WP-009 governance validator must follow what state truthfully declares.

A paused WP-009 must not be asked for artifacts only a completed WP-009 would have, and a
WP-009 that claims completion must still produce every one of them. Neither branch may
relax a cutoff or sealed check.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from check import (
    WP009_FINAL_ARTIFACTS,
    WP009_PAUSED_ARTIFACTS,
    wp009_governance_checks,
)

PAUSE_RECORD = "research/exogenous/GDELT-NEWS-CONTEXT-V1_1-PAUSE-V1.json"


def _mirror(tmp_path: Path) -> Path:
    """A minimal repository mirror carrying only what the validator reads."""
    root = tmp_path / "repo"
    for relative in ("state/current_state.json", "tasks/CURRENT_TASK.md", *WP009_PAUSED_ARTIFACTS):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relative, target)
    return root


def _state(root: Path) -> dict:
    return json.loads((root / "state/current_state.json").read_text(encoding="utf-8"))


def _write_state(root: Path, state: dict) -> None:
    (root / "state/current_state.json").write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


# --- paused branch ------------------------------------------------------------------


def test_the_live_repository_validates_as_paused() -> None:
    assert wp009_governance_checks(ROOT) == "PAUSED"


def test_a_paused_wp009_needs_no_final_artifacts(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    for relative in WP009_FINAL_ARTIFACTS:
        assert not (root / relative).exists()
    assert wp009_governance_checks(root) == "PAUSED"


def test_a_paused_wp009_still_requires_its_own_evidence(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    (root / PAUSE_RECORD).unlink()
    with pytest.raises(AssertionError, match="declared paused but its evidence is missing"):
        wp009_governance_checks(root)


def test_a_paused_wp009_must_assert_finalization_is_false(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    record = json.loads((root / PAUSE_RECORD).read_text(encoding="utf-8"))
    record["wp009_finalized"] = True
    (root / PAUSE_RECORD).write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    with pytest.raises(AssertionError):
        wp009_governance_checks(root)


def test_a_paused_wp009_cannot_claim_a_completed_task(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    (root / "tasks/CURRENT_TASK.md").write_text(
        "# CURRENT TASK — WP-009\n\n## STATUS\nCOMPLETED\n", encoding="utf-8", newline="\n"
    )
    with pytest.raises(AssertionError):
        wp009_governance_checks(root)


def test_a_paused_wp009_cannot_silently_carry_finalized_artifacts(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    premature = root / WP009_FINAL_ARTIFACTS[0]
    premature.parent.mkdir(parents=True, exist_ok=True)
    premature.write_text("{}\n", encoding="utf-8", newline="\n")
    with pytest.raises(AssertionError, match="declared paused but finalized artifacts exist"):
        wp009_governance_checks(root)


# --- completed branch ---------------------------------------------------------------


def test_a_state_claiming_completion_hard_fails_without_final_artifacts(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    state = _state(root)
    state["exogenous_acquisition_pause"]["wp009_finalized"] = True
    _write_state(root, state)
    with pytest.raises(AssertionError, match="declared finalized but these are missing"):
        wp009_governance_checks(root)


def test_removing_the_pause_block_entirely_also_demands_final_artifacts(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    state = _state(root)
    state.pop("exogenous_acquisition_pause")
    _write_state(root, state)
    with pytest.raises(AssertionError, match="declared finalized but these are missing"):
        wp009_governance_checks(root)


def test_a_completed_wp009_needs_every_final_artifact(tmp_path: Path) -> None:
    root = _mirror(tmp_path)
    state = _state(root)
    state["exogenous_acquisition_pause"]["wp009_finalized"] = True
    _write_state(root, state)
    for relative in WP009_FINAL_ARTIFACTS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}\n", encoding="utf-8", newline="\n")
    completed = "# CURRENT TASK — WP-009\n\n## STATUS\nCOMPLETED\n"
    (root / "tasks/CURRENT_TASK.md").write_text(completed, encoding="utf-8", newline="\n")
    (root / "tasks/archive/WP-009.md").write_text(completed, encoding="utf-8", newline="\n")
    assert wp009_governance_checks(root) == "COMPLETED"

    # Drop one final artifact and the completed branch must fail closed.
    (root / WP009_FINAL_ARTIFACTS[-1]).unlink()
    with pytest.raises(AssertionError, match="declared finalized but these are missing"):
        wp009_governance_checks(root)


# --- nothing is weakened -------------------------------------------------------------


def test_the_validator_never_touches_cutoff_or_sealed_state() -> None:
    source = (ROOT / "scripts/check.py").read_text(encoding="utf-8")
    start = source.index("def wp009_governance_checks(")
    end = source.index("def governance_checks(")
    body = source[start:end]
    for forbidden in ("development_cutoff", "sealed_queries", "authorized_btc_queries", "champion"):
        assert forbidden not in body
    # The unconditional required list still carries the completed WP-009 foundation.
    assert '"data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json"' in source
    assert '"reports/validation/WP-009-ALFRED-INTEGRITY.json"' in source
    assert '"research/exogenous/GDELT_QUERY_CATALOG_V1.json"' in source
    assert '"docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md"' in source


def test_state_records_the_accepted_wp011_review() -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    adaptive = state["adaptive_challenger"]
    assert state["latest_reviewed_checkpoint"] == (
        "PROSPECTIVE-RUNTIME-ARTIFACT-PROVENANCE-FIX-V1_1"
    )
    assert adaptive["research_director_verdict"] == "ACCEPTED"
    assert adaptive["terminal_classification"] == "REJECT_COST_DOMINATED"
    assert adaptive["ablation_terminal_classification"] == "INCONCLUSIVE"
    assert adaptive["family_status"] == "PARKED_REJECTED_NO_TUNING_AUTHORIZED"
    assert adaptive["sealed_eligibility"] == "NOT_ELIGIBLE_REJECTED"
    assert adaptive["ablation_sealed_eligibility"] == "NOT_ELIGIBLE_INCONCLUSIVE"
    assert state["champion_status"] == "NONE"
    assert state["paper_trades_completed"] == 0
    assert state["adaptive_search"]["sealed_queries"] == 0
    assert state["real_money_authorized"] is False
    assert state["exogenous_acquisition_pause"]["wp009_finalized"] is False
    assert state["paper_trading"]["research_status"] == "PAPER_RESEARCH_CANDIDATE"
    assert state["next_recommended_work_package"] == (
        "RESEARCH_DIRECTOR_REVIEW_PREDICTIVE_V2_DETERMINISTIC_CALENDAR_V1"
    )


def test_the_sealed_table_keeps_both_wp011_candidates_ineligible() -> None:
    table = json.loads(
        (ROOT / "research/sealed/SEALED_CANDIDATE_ELIGIBILITY.json").read_text(encoding="utf-8")
    )
    rows = {item["experiment_id"]: item for item in table["candidates"]}
    assert rows["EXP-ML-016-EWLS-INTERNAL-MACRO"]["sealed_eligibility"] == "NOT_ELIGIBLE_REJECTED"
    assert (
        rows["EXP-ML-017-EWLS-INTERNAL-ONLY"]["sealed_eligibility"] == "NOT_ELIGIBLE_INCONCLUSIVE"
    )
    for experiment_id in ("EXP-ML-016-EWLS-INTERNAL-MACRO", "EXP-ML-017-EWLS-INTERNAL-ONLY"):
        assert rows[experiment_id]["sealed_allocation"] is None
    assert not [item for item in table["candidates"] if item["sealed_eligibility"] == "ELIGIBLE"]


def test_the_review_records_the_accepted_verdict_and_identity() -> None:
    review = (ROOT / "reports/reviews/WP-011-RESEARCH-DIRECTOR-REVIEW.md").read_text(
        encoding="utf-8"
    )
    assert "ACCEPTED" in review
    assert "dfd57339d9a1b60ed64ae865c36fd3df279733c5" in review
    assert "16344c17bf7a0be579bb60fc42b58b04b9dc6c88" in review
    assert "ca98565f1df6ea52dfcd3cd770ffb50cc5e76ee5" in review
    assert "REJECT_COST_DOMINATED" in review
    assert "INCONCLUSIVE" in review
    assert "NEGATIVE" in review
    assert "5 commits ahead / 0 behind" in review
