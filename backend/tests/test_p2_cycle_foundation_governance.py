import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "research/protocols/P2-CYCLE-FOUNDATION-V1.json"
SOURCE_BOUNDARY = ROOT / "docs/canonical/CYCLE_RESEARCH_SOURCE_BOUNDARY_V1.md"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_p1a_is_power_blocked_without_market_result() -> None:
    state = _json(ROOT / "state/current_state.json")
    p1a = state["signal_persistence_power_gate"]
    report = _json(ROOT / p1a["report_json"])

    assert p1a["hypothesis_id"] == "ALIGNED_SIGNAL_PERSISTS_TO_120H_V1"
    assert p1a["hypothesis_status"] == "POWER_BLOCKED_NOT_EXECUTED"
    assert p1a["hypothesis_status"] not in {"REJECT", "INCONCLUSIVE"}
    assert p1a["power_gate_status"] == report["power_gate_status"] == "REDESIGN_REQUIRED"
    assert (
        p1a["mesi_bps_per_event"]
        == report["economic_threshold"]["P1A_INFORMATION_MESI_BPS"]
        == 24.0
    )
    assert p1a["empirical_mde_bps_per_event"] == 285.640052
    assert round(p1a["power_at_mesi"], 8) == 0.01424888
    assert not p1a["material_experiment_executed"]
    assert not p1a["zero_shift_statistic_computed"]
    assert not p1a["preregistration_authorized"]
    assert not p1a["runner_candidate_registered"]


def test_p2_has_one_primary_at_most_two_diagnostics_and_no_economic_result() -> None:
    protocol = _json(PROTOCOL)
    state = _json(ROOT / "state/current_state.json")
    cycle = state["cycle_foundation"]

    assert [item["hypothesis_id"] for item in protocol["primary_hypotheses"]] == [
        "BTC_TIME_CYCLE_STRUCTURE_V1"
    ]
    assert len(protocol["primary_hypotheses"]) == 1
    assert len(protocol["diagnostics"]) <= 2
    assert protocol["budget"] == {
        "primary_structural_hypotheses": 1,
        "maximum_diagnostics": 2,
        "material_economic_hypotheses_executed": 0,
    }
    assert not protocol["actual_market_result_inspected"]
    assert not protocol["detectability"]["actual_market_result_available"]
    assert protocol["detectability"]["target_power"] == 0.8
    assert protocol["detectability"]["economic_mesi"] is None
    assert not protocol["economic_strategy_created"]
    assert protocol["implemented_components"] == []
    assert cycle["primary_structural_hypotheses"] == 1
    assert cycle["diagnostic_count"] <= cycle["maximum_diagnostics"] == 2
    assert not cycle["actual_market_result_inspected"]
    assert not cycle["economic_strategy_created"]


def test_cycle_source_boundary_marks_unsupported_rules_unspecified() -> None:
    source = SOURCE_BOUNDARY.read_text(encoding="utf-8")
    for concept in (
        "hierarchical cyclic time",
        "index / inverse concepts",
        "swing as control",
        "price",
        "volume as contextual confirmation",
        "vincolo / raccordo concepts",
        "multi-timeframe reasoning",
    ):
        line = next(line for line in source.splitlines() if f"| {concept} |" in line)
        assert "| DOCUMENTED_PUBLIC |" in line

    for unsupported in (
        "complete centering algorithm",
        "universal swing-selection formula",
        "universal swing-value formula",
        "universal volume thresholds",
        "complete raccordo algorithm",
        "target algorithm",
        "official executable code",
    ):
        line = next(line for line in source.splitlines() if f"| {unsupported} |" in line)
        assert "| UNSPECIFIED |" in line
    assert "invented or completed by this" in source
    assert "project is `RECONSTRUCTED`" in source


def test_no_cycle_component_implementation_or_safety_counter_drift() -> None:
    state = _json(ROOT / "state/current_state.json")
    forbidden_modules = {
        "cycle.py",
        "cycle_swing.py",
        "cycle_volume.py",
        "cycle_inverse.py",
        "cycle_vincolo.py",
        "cycle_raccordo.py",
        "cycle_target.py",
        "cycle_trading.py",
    }
    research_modules = ROOT / "backend/app/research"

    assert not forbidden_modules.intersection(path.name for path in research_modules.glob("*.py"))
    assert state["experiments_completed"] == 26
    assert state["statistical_governance"]["known_discovery_family_size"] == 12
    assert state["adaptive_search"]["material_economic_hypotheses"] == 13
    assert state["cycle_foundation"]["material_economic_hypotheses_executed"] == 0
    assert state["sealed_evaluation"]["consumed_btc_queries"] == 0
    assert state["adaptive_search"]["sealed_queries"] == 0
    assert state["champion_status"] == "NONE"
    assert state["real_money_authorized"] is False
    assert state["owner_economic_policy"]["real_money_authorized"] is False
    assert state["paper_trading"]["real_money"] is False
