# CURRENT TASK — IMPLEMENT-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1

Status: ACTIVE_IMPLEMENTATION_ONLY_NO_EXECUTION

Read only:
- `AGENTS.md`;
- `decisions/ADR-0033-PUBLIC-TAKER-FLOW-FOUNDATION-1H-ONLY-AND-INCREMENTAL-ALLOCATION.md`;
- `research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-V1.md` (frozen; do not edit);
- `backend/app/predictive/taker_flow_foundation.py`, `backend/app/predictive/taker_flow_source.py`,
  `backend/app/predictive/paired_inference.py` (import only; do not edit — their hashes are
  pinned by the EXP-PRED-V2-005 result and replay);
- `research/experiments/EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION/result.json`.

## Purpose

Implement the deterministic pre-execution power/detectability gate for the frozen
`EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL` design, and nothing else.

## Frozen gate design

The authoritative definition is the "Pre-execution power gate" section of the frozen protocol.
Implement it exactly:

- proxy classification `ANALOG_DEPENDENCE_AND_VARIANCE_PROXY`; the output must state
  prominently `MDE_IS_ANALOG_EXPECTED_DETECTABILITY_NOT_REALIZED_INCREMENTAL_VARIANCE`;
- proxy series: EXP-PRED-V2-005 1h per-row `FLOW_ONLY_BRIER_LOSS -
  TRAINING_BASE_RATE_CONSTANT_BRIER_LOSS`, rebuilt by exact replay of the frozen foundation
  code; before use the replay must reproduce the committed 1h result exactly (pooled and
  per-fold Brier improvement, scored rows); any mismatch -> `POWER_GATE_FAILED_CLOSED`;
- annual folds 2021-2024, 48h moving blocks on each fold's hourly timeline, never crossing a
  fold, 10,000 replicates in chunks of 500, seed `numpy.random.default_rng(2026092307)`;
- `D0` = replicate pooled statistics minus the observed pooled proxy mean;
- `power(delta) = mean_d [delta + d + quantile_0.025(D0) > 0]`; report `power(0.00020)`;
- empirical MDE = smallest `delta = k * 1e-7` (`k = 0..100000`) with `power >= 0.80`, else
  reported as not reached;
- `ANALOG_POWER_GATE_PASSES_PENDING_RESEARCH_DIRECTOR_REVIEW` iff `power(0.00020) >= 0.80`,
  otherwise `POWER_BLOCKED_NOT_EXECUTED`. MESI is never lowered; no proxy, seed, block, alpha
  or power change after the value is seen. A pass does not authorize EXP-PRED-V2-006.

Forbidden inputs: any price-only or price-plus-flow prediction, any EXP-PRED-V2-006 control or
candidate fit, any observed incremental effect, any statistic of price features on an
outer-fold row, post-cutoff or sealed data.

## Implement

- a new module (for example `backend/app/predictive/taker_flow_power_gate.py`) importing the
  frozen foundation functions without modifying them;
- focused deterministic tests on synthetic series: bootstrap `D0`
  determinism, fold-boundary containment, verdict thresholds, fail-closed on replay mismatch,
  `power()`/MDE-grid arithmetic on a synthetic `D0`, and a guard proving no price feature or
  EXP-PRED-V2-006 model is constructed;
- one Owner-facing command, e.g.
  `.venv\Scripts\python.exe scripts\run_public_taker_flow_1h_incremental_power_gate.py`, that
  writes `reports/validation/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1.json`
  and `.md`, refuses to overwrite them, and supports `--check` replay;
- identify every text dependency of the gate artifact (protocol, foundation result, code) by
  `canonical_text_sha256` from `backend/app/research/text_provenance.py` (ADR-0034), never
  by checkout bytes;
- extend `backend/app/predictive/taker_flow_validation.py` and `scripts/check.py` so the
  power-gate artifact is a governed, hash-checked record once it exists;
- register the command in this task file.

## Do not

- execute the gate, EXP-PRED-V2-006, or EXP-PRED-V2-005 beyond what the Owner command does;
- fit or score any EXP-PRED-V2-006 control or candidate, or create a candidate market result;
- search thresholds, models, features, horizons or seeds;
- edit the frozen protocol, the EXP-PRED-V2-005 result or the foundation modules;
- run full test suites or `scripts/check.py`; git add/commit/push/pull; inspect CI.

## Stop condition

Stop before the incremental experiment itself. When code is ready return only:

`CODE_READY`

then:
- changed_files: <count>
- run_command: <one PowerShell command>
- expected_outputs: <paths>
- notes: <only if a manual prerequisite exists>

After the Owner runs the gate, the Research Director reviews it. EXP-PRED-V2-006 stays
`PREREGISTERED_EXECUTION_BLOCKED_PENDING_POWER_GATE` until that review.
