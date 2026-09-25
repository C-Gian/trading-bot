# Checkpoint — SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1

Status: `SYSTEM_G1_CYCLE_QUALITY_RESULT_PENDING_RESEARCH_DIRECTOR_ADJUDICATION`
Mechanical disposition: **`CYCLE_SYNTHETIC_QUALITY_GATE_PASS_PENDING_RESEARCH_DIRECTOR_ACTIVATION`**
Authority: ADR-0045; `research/protocols/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.md`.
Artifact: `reports/research/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.json`
Replay: `uv run python scripts/build_g1_cycle_quality_gate.py --check` (byte-identical; run by
`scripts/check.py`).

## Implemented

- Frozen labels in `backend/app/g1/cycle.py` (`METHOD_VERSION ...-ACP-IMPL-2-QUALITY-GATE-V1`):
  UNAVAILABLE (warm-up / re-warm / no dominant period / no projection); USABLE iff
  `explained_fraction >= 0.90` on the current and the two immediately preceding completed input
  bars, with the persistence history cleared on every gap/reset; otherwise WEAK. No other metric
  participates. The ACP numerics were not changed.
- Frozen gate in `backend/app/g1/cycle_quality_gate.py`, executed once. Per scale: 128 seeded
  white-noise paths, 48 clean-cycle and 48 trend+cycle paths (16 each at the band's lower quartile,
  midpoint and upper quartile, seeded uniform phase, trend 0.05/bar), warm-up + 512 evaluated bars.
  All seeds and the rule/protocol/ADR/code SHA-256 identities are in the artifact.
- `CYCLE_DECISION_ACTIVATION` stays False; decision-path role `METHOD_NOT_READY` and qualifier
  `CYCLE_METHOD_NOT_READY` are unchanged even when a scale is USABLE (tested).
- Primary operational delay: `RiskPolicy` default now 1m
  (`G1_RISK_V2_..._1M_PRIMARY_DELAY`); synthetic plans inherit 1m, fills at readiness + 1m; the +5m
  stress stays relative to primary. Costs and risk limits unchanged; legacy engines untouched.
- The Checkpoint-1 diagnostics artifact (IMPL-1) is preserved unchanged and hash-pinned; it no
  longer regenerates because the labels are now frozen.

## Result (USABLE occupancy over 512 post-warm-up bars)

| Scale | Noise median / p95 | Clean median / p10 | Trend+cycle median / p10 | Period error (clean / trend) | Gates |
|---|---|---|---|---|---|
| 45m | 0.018 / 0.047 | 1.00 / 1.00 | 1.00 / 1.00 | 0.039 / 0.039 | PASS |
| 3h | 0.020 / 0.053 | 1.00 / 1.00 | 1.00 / 1.00 | 0.042 / 0.042 | PASS |
| 1d | 0.022 / 0.058 | 1.00 / 1.00 | 1.00 / 1.00 | 0.039 / 0.039 | PASS |
| 4d | 0.020 / 0.068 | 1.00 / 1.00 | 1.00 / 1.00 | 0.039 / 0.039 | PASS |
| 1w | 0.025 / 0.090 | 1.00 / 1.00 | 1.00 / 1.00 | 0.046 / 0.046 | PASS |
| 4w | 0.020 / 0.060 | 1.00 / 1.00 | 1.00 / 1.00 | 0.040 / 0.040 | PASS |

Integrity: zero turn-confirmation violations; gap reset + full re-warm PASS on every scale;
replay-speed label identity PASS (60×–14400×); independent ACP reconciliation max difference 0.

Observations for the Director (descriptive, not used to change anything):

- Clean and trend+cycle results are identical because the two-pole high-pass removes a linear
  trend exactly; the trend family therefore does not stress the rule beyond the clean family.
- Coherent retention is saturated (noise-free sinusoids); the gate says nothing about retention
  under additive noise, which the protocol did not include.
- Noise p95 occupancy rises with scale (0.047 → 0.090 at 1w) but stays under 0.15.

## Boundaries kept

No market data or BTC outcome read; no threshold, feature, band, ACP parameter or method searched;
no P1/P2 performance; no forecaster fitted; sealed queries 0; validated strategy null; production
NO_TRADE; Champion NONE; real money false.
