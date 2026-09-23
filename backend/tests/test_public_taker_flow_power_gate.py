"""Deterministic proofs for the EXP-PRED-V2-006 pre-execution power gate.

Synthetic series only: nothing here reads market data, replays the foundation, fits a model
or computes the real gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from app.predictive import taker_flow_power_gate as gate
from app.predictive import taker_flow_validation as validation
from app.predictive.taker_flow_foundation import HOUR_SECONDS, ScoredFold, year_start_seconds
from app.research.text_provenance import canonical_text_bytes

ROOT = Path(__file__).resolve().parents[2]
YEARS = (2021, 2022, 2023, 2024)


def fold(year: int, values: np.ndarray) -> ScoredFold:
    first = year_start_seconds(year)
    times = first + np.arange(values.shape[0], dtype=np.int64) * HOUR_SECONDS
    return ScoredFold(year, first, int(times[-1]), times, values)


def synthetic_folds(seed: int = 3, rows: int = 400) -> list[ScoredFold]:
    rng = np.random.default_rng(seed)
    return [fold(year, rng.normal(0.0005, 0.01, size=rows)) for year in YEARS]


def test_frozen_constants_match_the_protocol() -> None:
    assert gate.MESI == 0.0002 and gate.TARGET_POWER == 0.80
    assert gate.ALPHA == 0.05 and gate.LOWER_QUANTILE == 0.025
    assert gate.BLOCK_LENGTH_HOURS == 48 and gate.REPLICATES == 10_000
    assert gate.REPLICATE_CHUNK == 500 and gate.POWER_GATE_SEED == 2026092307
    assert gate.GRID_STEP == 1e-7 and gate.GRID_MAX_K == 100_000
    assert gate.PROXY_HORIZON_HOURS == 1
    assert len({gate.POWER_GATE_SEED, 2026092306, 20260923}) == 3


def test_bootstrap_noise_distribution_is_deterministic_and_centred() -> None:
    folds = synthetic_folds()
    first, geometry = gate.replicate_statistics(folds, replicates=300)
    second, _ = gate.replicate_statistics(folds, replicates=300)
    assert np.array_equal(first, second)
    other, _ = gate.replicate_statistics(folds, replicates=300, seed=1)
    assert not np.array_equal(first, other)
    assert geometry["2021"]["block_start_positions"] == 400 - 48 + 1
    observed = gate.observed_pooled_mean(folds)
    d0 = gate.noise_distribution(first, observed)
    assert np.allclose(d0 + observed, first)
    assert abs(float(d0.mean())) < 0.001


def test_blocks_never_cross_a_fold_boundary() -> None:
    # Every slot of each fold is scored, so a within-fold resample keeps each fold's mass:
    # the pooled statistic is constant only if no block ever mixes the two folds.
    folds = [fold(2021, np.full(300, 1.0)), fold(2022, np.full(200, -1.0))]
    statistics, _ = gate.replicate_statistics(folds, replicates=200)
    assert np.allclose(statistics, (300 - 200) / 500)
    outside = ScoredFold(2021, 0, 10 * HOUR_SECONDS, np.array([20 * HOUR_SECONDS]), np.ones(1))
    with pytest.raises(gate.PowerGateError):
        gate.replicate_statistics([outside], replicates=10)


def test_power_is_the_literal_frozen_formula() -> None:
    d0 = np.arange(-50, 51, dtype=np.float64) * 1e-6
    quantile = gate.lower_quantile(d0)
    assert quantile == pytest.approx(float(np.quantile(d0, 0.025)))
    for delta in (0.0, 5e-5, 7.7e-5, 1e-4):
        expected = sum(1 for d in d0 if delta + d + quantile > 0) / d0.shape[0]
        assert gate.power(delta, d0, quantile) == expected


def test_mde_is_the_smallest_grid_effect_reaching_target_power() -> None:
    d0 = np.arange(-50, 51, dtype=np.float64) * 1e-6
    quantile = gate.lower_quantile(d0)
    brute = next(k for k in range(5000) if gate.power(k * gate.GRID_STEP, d0, quantile) >= 0.80)
    mde = gate.minimum_detectable_effect(d0, quantile)
    assert mde["reached"] is True and mde["k"] == brute
    assert mde["mde"] == brute * gate.GRID_STEP
    assert gate.power((brute - 1) * gate.GRID_STEP, d0, quantile) < 0.80

    wide = np.linspace(-1.0, 1.0, 1001)
    assert gate.minimum_detectable_effect(wide, gate.lower_quantile(wide)) == {
        "reached": False,
        "k": None,
        "mde": None,
        "power_at_mde": None,
    }


def test_verdict_thresholds() -> None:
    assert gate.classify(0.80) == gate.PASSES
    assert gate.classify(0.95) == gate.PASSES
    assert gate.classify(0.7999) == gate.BLOCKED
    assert gate.classify(0.0) == gate.BLOCKED


def _matching_replay(folds: list[ScoredFold]) -> tuple[dict, dict]:
    summary = {
        "scored_rows": sum(int(f.differences.shape[0]) for f in folds),
        "pooled_brier_improvement": gate.observed_pooled_mean(folds),
        "folds": [
            {
                "year": f.year,
                "scored_rows": int(f.differences.shape[0]),
                "brier_improvement": float(f.differences.mean()),
            }
            for f in folds
        ],
    }
    committed = {"horizons": {"1": json.loads(json.dumps(summary))}}
    return summary, committed


def test_replay_verification_fails_closed_on_any_mismatch() -> None:
    folds = synthetic_folds()
    summary, committed = _matching_replay(folds)
    checks = gate.verify_replay(summary, folds, committed)
    assert "FULL_1H_SUMMARY_EQUALS_COMMITTED" in checks
    committed["horizons"]["1"]["folds"][2]["brier_improvement"] += 1e-9
    with pytest.raises(gate.ProxyReplayMismatch):
        gate.verify_replay(summary, folds, committed)
    summary, committed = _matching_replay(folds)
    with pytest.raises(gate.ProxyReplayMismatch):
        gate.verify_replay(summary, folds[:3], committed)


def test_a_replay_mismatch_records_failed_closed_without_power(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    folds = synthetic_folds()
    summary, _ = _matching_replay(folds)
    monkeypatch.setattr(gate, "load_minute_books", lambda root: ({}, {}))
    monkeypatch.setattr(gate, "build_panel", lambda books: None)
    monkeypatch.setattr(gate, "replay_proxy_folds", lambda panel: (summary, folds))
    record = gate.run_power_gate(ROOT)  # the committed 1h result differs from this summary
    assert record["classification"] == gate.FAILED_CLOSED
    assert record["analysis"] is None
    assert record["replay"]["status"] == "MISMATCH_FAILED_CLOSED"
    assert record["statement"] == gate.MDE_STATEMENT
    gate.validate_record(record, ROOT)
    assert gate.MDE_STATEMENT.encode() in gate.markdown_bytes(record)


def test_a_computed_record_is_consistent_with_its_verdict() -> None:
    folds = synthetic_folds(rows=500)
    analysis = gate.power_analysis(folds)
    replay = {"status": "REPRODUCED_EXACTLY", "checks": ["X"], "scored_rows": 2000}
    record = gate.build_record(ROOT, analysis["classification"], replay, analysis)
    gate.validate_record(record, ROOT)
    assert record["boundaries"]["execution_authorized"] is False
    assert record["boundaries"]["pass_authorizes_execution"] is False
    tampered = json.loads(json.dumps(record))
    tampered["classification"] = (
        gate.BLOCKED if record["classification"] == gate.PASSES else gate.PASSES
    )
    with pytest.raises(gate.PowerGateError):
        gate.validate_record(tampered, ROOT)
    tampered = json.loads(json.dumps(record))
    tampered["design"]["mesi"] = 0.0001
    with pytest.raises(gate.PowerGateError):
        gate.validate_record(tampered, ROOT)


def test_no_price_feature_or_incremental_model_is_constructed() -> None:
    source = (ROOT / "backend/app/predictive/taker_flow_power_gate.py").read_text(encoding="utf-8")
    for forbidden in ("LOG_RETURN", "first_open", "LogisticRegression", "fit_model(", "2026092306"):
        assert forbidden not in source, forbidden

    class SixFeaturePanel:
        features = np.zeros((10, 6))

    with pytest.raises(gate.PowerGateError):
        gate.replay_proxy_folds(SixFeaturePanel())  # type: ignore[arg-type]


def test_text_dependencies_use_canonical_text_identity() -> None:
    dependencies = gate.text_dependencies(ROOT)
    assert {item["path"] for item in dependencies} == set(gate.TEXT_DEPENDENCIES)
    assert all(item["rule"] == "CANONICAL_UTF8_LF_TEXT_V1" for item in dependencies)
    assert gate.INCREMENTAL_PROTOCOL_PATH in gate.TEXT_DEPENDENCIES
    assert (
        "research/experiments/EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION/result.json"
        in (gate.TEXT_DEPENDENCIES)
    )


def _mirror(tmp_path: Path) -> Path:
    for relative in gate.TEXT_DEPENDENCIES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    return tmp_path


def _write(root: Path, record: dict) -> None:
    for path, payload in (
        (gate.GATE_JSON_PATH, gate.canonical_json_bytes(record)),
        (gate.GATE_MARKDOWN_PATH, gate.markdown_bytes(record)),
    ):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload.replace(b"\n", b"\r\n"))  # a CRLF checkout still validates


def test_validator_governs_the_written_gate_record(tmp_path: Path) -> None:
    state = json.loads((ROOT / "state/current_state.json").read_text(encoding="utf-8"))
    assert validation.validate_power_gate(ROOT, state, False) in {
        "NOT_COMPUTED",
        *gate.CLASSIFICATIONS,
    }
    # A pre-run state: the gate is not yet recorded or pinned, so a freshly written record
    # is governed on its own terms.
    state = json.loads(json.dumps(state))
    state["predictive_public_taker_flow_1h_incremental"]["power_gate"] = {
        "status": "NOT_COMPUTED_PENDING_IMPLEMENTATION"
    }
    root = _mirror(tmp_path)
    replay = {"status": "MISMATCH_FAILED_CLOSED", "failed_check": "X", "source_result": "r"}
    record = gate.build_record(root, gate.FAILED_CLOSED, replay, None)
    _write(root, record)
    assert validation.validate_power_gate(root, state, False) == gate.FAILED_CLOSED

    report = root / gate.GATE_MARKDOWN_PATH
    report.write_bytes(canonical_text_bytes(report.read_bytes()) + b"edited\n")
    with pytest.raises(validation.TakerFlowValidationError, match="regenerate"):
        validation.validate_power_gate(root, state, False)
    _write(root, record)
    protocol = root / gate.INCREMENTAL_PROTOCOL_PATH
    protocol.write_bytes(protocol.read_bytes().replace(b"0.00020", b"0.00010", 1))
    with pytest.raises(validation.TakerFlowValidationError, match="canonical text"):
        validation.validate_power_gate(root, state, False)
    (root / gate.GATE_MARKDOWN_PATH).unlink()
    with pytest.raises(validation.TakerFlowValidationError, match="incomplete"):
        validation.validate_power_gate(root, state, False)
