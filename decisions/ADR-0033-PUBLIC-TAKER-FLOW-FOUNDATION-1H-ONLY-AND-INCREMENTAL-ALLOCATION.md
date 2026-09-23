# ADR-0033 — Public taker-flow foundation supports 1h only and allocates an incremental-information test

Status: RESEARCH_DIRECTOR_ACCEPTED (2026-09-23)

## Evidence reviewed

- Frozen protocol `research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md`
  (sha256 `6fb5da71b18a44bd6c8891f50b0490311f48a988eef27ea46ff66546762fe012`).
- Source manifest `data/manifests/BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1.json`
  (sha256 `cf696350cfe6294ffcbb74bef657ba9e58be22d232e7aab30c9cc7aa4c204bc4`): 120 official
  Binance monthly objects, spot + USD-M BTCUSDT 1m, 2020-01 to 2024-12, all verified
  against their official checksums.
- Result `research/experiments/EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION/result.json`
  (sha256 `bc8150163b156840e711a916823ccd5dcd69bf747ab6e389302524d7a6497bbf`).
- Report `reports/research/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md`
  (sha256 `b77fe1f9c28bfc9fb057140b3a07b6f526bfab2c5af3a05d8528090b9bb0d50a`).
- Owner-executed targeted tests: 19 passed. Deterministic `--check` replay: PASS.

## Implementation interpretations frozen

Both executor interpretations left open by the protocol are accepted and frozen:

- calibration embargo: base-fit candidates with `T + 2H` after the first calibration instant
  are dropped, so the calibration set remains exactly the chronological last 20%;
- bootstrap streams: `SeedSequence(20260923).spawn(3)`, assigned in frozen 24h -> 4h -> 1h
  order.

## Verdict

Classification: `FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY`.

| Horizon | Scored | Coverage | Brier improvement | Bonferroni 98.33% interval | Classification |
|---|---|---|---|---|---|
| 24h | 34997 | 0.9999 | -0.0037126 | [-0.0059875, -0.0013780] | NOT SUPPORTED |
| 4h | 35017 | 0.9999 | -0.0002184 | [-0.0007812, +0.0003397] | NOT SUPPORTED |
| 1h | 35030 | 0.9999 | +0.0006438 | [+0.0001705, +0.0011318] | SUPPORTED |

The result artifact is authoritative for exact values and secondary metrics.

Interpretation:

- 24h is not supported: pooled Brier and log loss are worse than the training-base-rate
  control and the adjusted interval lies entirely below zero.
- 4h is not supported: the interval spans zero and log loss is worse than control.
- 1h is supported as a predictive-information foundation: a small out-of-sample
  probabilistic directional signal (pooled AUC 0.5316, three of four folds non-negative, the
  2021 fold negative).
- This is not evidence of trading profitability, not a LONG/NO_TRADE strategy and not a
  Champion. It does not authorize sealed evaluation, a product-horizon change or real money.

## Boundaries

- Search memory: family `FAM-PUBLIC-TAKER-FLOW-PROBABILITY` (parent `FAM-ORDER-FLOW`) and the
  predictive non-sealed outcome
  `research/memory/registry/outcomes/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.jsonl`.
- 24h and 4h may not be rescued from this exposed foundation: no alternative model,
  threshold, feature transformation, horizon tweak, inversion or post-result tuning.
- 1h receives further research budget only.
- Historical `FAM-ORDER-FLOW` (WP-007, `EXP-ALG-012`/`EXP-ALG-013`, `REJECT_COST_DOMINATED`)
  remains rejected. EXP-PRED-V2-005 is a distinct structural prediction result (continuous
  spot + USD-M flow as a probability source), not a retroactive rescue of WP-007.
- Champion = NONE. Sealed queries = 0. Real money = false. Product horizon unchanged (24h).

## Allocation

The next question is whether the supported 1h flow information is **incremental** to the
matched contemporaneous 1h price movement of the same two markets, rather than a proxy for
contemporaneous price momentum or relative spot-perpetual movement.

- Experiment: `EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL`; hypothesis:
  `H-PRED-V2-PUBLIC-FLOW-INCREMENTAL-001`.
- Protocol: `research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-V1.md`.
- Status: `PREREGISTERED_EXECUTION_BLOCKED_PENDING_POWER_GATE`.
- MESI = 0.00020 absolute paired Brier improvement; alpha = 0.05; target power = 0.80.
- Power gate: seed `2026092307`; variance source `ANALOG_DEPENDENCE_AND_VARIANCE_PROXY` = the
  exposed EXP-PRED-V2-005 1h per-row `FLOW_ONLY_BRIER_LOSS - TRAINING_BASE_RATE_CONSTANT_BRIER_LOSS`
  by exact replay, centred into an empirical noise distribution. Its MDE is analog expected
  detectability, not the realized incremental variance
  (`MDE_IS_ANALOG_EXPECTED_DETECTABILITY_NOT_REALIZED_INCREMENTAL_VARIANCE`). Classification
  `ANALOG_POWER_GATE_PASSES_PENDING_RESEARCH_DIRECTOR_REVIEW` or `POWER_BLOCKED_NOT_EXECUTED`;
  MESI is not lowered if the gate blocks, and a pass still requires Research Director review.
- Next work package: `IMPLEMENT-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1`. It implements
  the pre-execution power gate only and must not fit or score the EXP-PRED-V2-006 candidate
  or control.

Not authorized by this allocation: other horizons, extra lags, alternative imbalance
definitions, nonlinear models, hand-built regimes, threshold sweeps, the V2 `p_up >= 0.60`
LONG rule, trading PnL, costs, or any feature beyond the frozen six.
