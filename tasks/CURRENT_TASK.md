# CURRENT TASK — G2-01-CAUSAL-TRADER-VERTICAL-SLICE-V1

Status: **EXECUTOR COMPLETE — PENDING RESEARCH DIRECTOR GATE B REVIEW — ECONOMIC MARKET EXECUTION FORBIDDEN**

Executor checkpoint: `reports/checkpoints/G2-01-CAUSAL-TRADER-VERTICAL-SLICE-V1.md` (Claude Code, overflow executor).

## Authority

- `AGENTS.md`
- `state/current_state.json -> current_project_status`
- `reports/checkpoints/G2-00-GATE-A-CONTRACT-FREEZE-V1.md`
- `tasks/G2_01_IMPLEMENTATION_PACKAGE_V1.md`

## Executor

Primary: **Codex**.  
Overflow: Claude Code only if Codex is unavailable or explicitly delegated.

## Instruction

Implement the complete bounded G2-V0 causal trader vertical slice exactly as specified in:

`tasks/G2_01_IMPLEMENTATION_PACKAGE_V1.md`

Read only the files referenced by that package plus the minimum code required for implementation.

Do not make scientific/economic choices that are already frozen in the contracts.

## Gate B objective

Demonstrate:
- causal completed-bar state;
- continuous G2 forecast semantics;
- separate utility/actionability;
- fail-closed LONG/SHORT/NO_TRADE;
- deterministic risk/execution;
- immutable event lineage;
- shadow-only cycle state;
- replay/API/UI parity;
- phase-bounded I/O;
- deterministic tests and full repository validation.

## Market-data boundary

Allowed:
- synthetic fixtures;
- small explicitly declared <=2024 exposed windows for engineering parser/aggregation/replay checks.

Forbidden:
- BTC economic backtest/performance ranking;
- G2 development selection;
- protected 2025+ outcomes;
- parameter/model/feature/timeframe tuning;
- G1 rescue;
- paper/real orders;
- real capital.

## Completion

Executor leaves status:
`EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_GATE_B_REVIEW`.

The Research Director, not the executor, decides whether Gate B passes and whether G2-02 can be opened.
