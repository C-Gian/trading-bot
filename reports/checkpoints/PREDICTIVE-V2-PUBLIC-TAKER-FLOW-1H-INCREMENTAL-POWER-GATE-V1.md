# Checkpoint — PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1

Status: **COMPLETE — POWER_BLOCKED_NOT_EXECUTED** (Research Director accepted,
[ADR-0035](../../decisions/ADR-0035-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-BLOCK.md)).

Starting HEAD `bb37a0a`. The gate implementation, the Owner-generated gate record and this
closure are committed together.

## What ran

- Implementation: `backend/app/predictive/taker_flow_power_gate.py`, Owner command
  `scripts/run_public_taker_flow_1h_incremental_power_gate.py`, governed by
  `backend/app/predictive/taker_flow_validation.py` and `scripts/check.py`.
- The frozen foundation's own 1h `evaluate_horizon` was replayed unchanged to rebuild the
  exposed proxy series; the replay reproduced the committed EXP-PRED-V2-005 1h result exactly
  (17 checks, 35,030 scored rows).
- 48h fold-stratified moving-block bootstrap, 10,000 replicates, seed `2026092307`.
- Owner `--check` replay: PASS.

## Result

`MDE_IS_ANALOG_EXPECTED_DETECTABILITY_NOT_REALIZED_INCREMENTAL_VARIANCE`

| Quantity | Value |
|---|---|
| Frozen MESI | 0.00020 |
| Expected power at MESI | 0.1871 (target 0.80) |
| Empirical analog MDE | 0.0005414 |
| Classification | `POWER_BLOCKED_NOT_EXECUTED` |

Gate record canonical text sha256
`09f5e05562aa6439a2e6a9a9b5fc2c94fde1293116502d9d74f08ba9562e5c01`.

## Disposition

- EXP-PRED-V2-006 is not executed. Model fits 0; price-only and price-plus-flow predictions
  never generated; incremental market outcome unobserved. This is not evidence that 1h flow
  lacks incremental information, only that the frozen design cannot detect the MESI.
- MESI, power method, proxy, seed and block length may not be changed as a rescue.
- Search memory: append-only predictive outcome
  `research/memory/registry/outcomes/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1.jsonl`.
- Next: `RESEARCH-DIRECTOR-REALLOCATION-AFTER-PUBLIC-TAKER-FLOW-POWER-BLOCK`; no engineering
  task is authorized.
- Sealed queries 0. Champion NONE. Real money false. Product horizon unchanged.
