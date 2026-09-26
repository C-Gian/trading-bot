# NEW CHAT BOOTSTRAP — Trading Bot

> **Current canonical state:** `SYSTEM_G1_TERMINAL_PARK` under ADR-0050.
> Owner Product Mission V2 remains active. System G1 is closed, System G2 is unallocated,
> Phase B is forbidden, active research allocation is zero, and production action is
> `NO_TRADE`. Read `state/current_state.json` and `tasks/CURRENT_TASK.md` before interpreting
> any older programme text.

Purpose: make a new ChatGPT conversation recover the project from repository truth without
depending on the previous chat transcript.

This file is an operating protocol, not a current-state record. Live truth always comes from
the files below at the current `main` HEAD.

## Current operative status — read before anything else

Research is **parked**:

`SYSTEM_G1_TERMINAL_PARK`

([ADR-0050](../../decisions/ADR-0050-ADOPT-ASTRA-SYSTEM-G1-TERMINAL-PARK.md)).

The canonical machine-readable truth is `state/current_state.json -> current_project_status`.

- G1 closed at `SYSTEM_G1_DEVELOPMENT_REJECTED_SELECTION_STAGE`.
- G2 unallocated.
- no Phase B;
- no active market experiment/search/confirmation;
- no validated strategy or Champion;
- production action `NO_TRADE`;
- no real capital.
- `tasks/CURRENT_TASK.md` is `PARKED-NO-ACTIVE-RESEARCH-TASK`.

The Owner Product Mission V2 remains canonical: professional BTC multi-signal paper system,
continuous prediction, `LONG / SHORT / NO_TRADE`, multi-timeframe context and causal replay.

Reopening requires a written material changed case and Astra approval. A new indicator/model,
generic paper, elapsed time or renewed interest is insufficient.

## Mandatory bootstrap order

At the start of a new Research Director chat:

1. resolve the current `main` HEAD;
2. read `AGENTS.md`;
3. read `governance/SCIENTIFIC_CONSTITUTION.md`;
4. read `state/current_state.json`;
5. read `tasks/CURRENT_TASK.md`;
6. read `decisions/INDEX.md` and only the ADRs relevant to the current task;
7. read `docs/canonical/RESEARCH_STAGE_POLICY_V1.md` and
   `docs/canonical/STRATEGIC_ALLOCATION_MAP_V1.md` (Constitution 3.0, ADR-0036);
8. before proposing any new research family, mechanism or candidate, inspect:
   - `research/memory/registry/families/`;
   - `research/memory/registry/outcomes/`;
   - `research/candidates/` (Candidate Cards and admission dispositions);
   - `reports/reviews/METHODOLOGICAL-QUALIFICATIONS-V1.md`;
   - `state.governance_transition_v3` and the predictive generation closure/state fields in
     `state/current_state.json`;
9. read the latest dated handover snapshot under `reports/handover/` only as a navigation
   aid, never as higher authority than live state/task/experiment artifacts.

Do not ask the Owner to reconstruct prior work from memory.

## Anti-loop rule

Before authorizing a new hypothesis or data family, explicitly determine whether the mechanism,
information source, entry-event anchor, threshold family, horizon, or model lineage has already
been tested, parked, rejected, blocked or deferred.

A renamed family is not new evidence.

A revisit is allowed only when the repository supports a genuinely different falsifiable
scientific question and the Research Director records why the prior negative evidence does not
already answer it.

Preserve all negative evidence. Never rescue a failed result by post-hoc inversion, threshold
drift, fold removal, feature pruning, horizon selection or model substitution.

## Decision hierarchy

- Owner: mission, evaluation principles, product/risk objective, real capital.
- Astra: strategic scientific authority for material research-allocation decisions (new
  mechanism / Candidate Card, budget excess, reopening closed lineages, frontier R&D,
  project-level reallocation, Champion; full list in `RESEARCH_STAGE_POLICY_V1.md` §5).
- ChatGPT/Research Director: routine scientific design, architecture, tasking, implementation
  review, experiment adjudication and ordinary decisions inside Astra's directive.
- Claude Code: sole coding / repository implementation executor. Codex is not part of the
  normal implementation workflow.

## Executor / Owner division

Default workflow is token-efficient:

- ChatGPT/Research Director: routine science, architecture, frozen experiment design, result
  interpretation; material allocation goes to Astra.
- Claude Code: write the substantial code block requested by `CURRENT_TASK.md`.
- Owner: run the provided acquisition/backtest/validation/Git/CI commands locally and return
  concise PASS/FAIL/output to ChatGPT.
- Heavy downloads, backtests, full validation, Git operations and CI polling are NOT executor
  work unless `CURRENT_TASK.md` explicitly says otherwise.

Avoid micro-tasks that force repeated Owner intervention. One executor implementation block and
one Owner execution/validation step per cycle is the default target.

## Safety / research boundaries

- Owner Product Mission V2 remains the active product scope: BTC-focused professional multi-signal
  paper system with `LONG / SHORT / NO_TRADE`.
- Current research allocation is zero under `SYSTEM_G1_TERMINAL_PARK`.
- G1 Phase B and automatic G2/G3 are forbidden.
- Historical development/search memory remains exposed evidence and never becomes fresh
  confirmation through renaming/rescoring.
- 2023-2024 remain locked against new system evaluation under the present allocation and are not
  relabeled pristine sealed confirmation.
- post-cutoff data remains protected.
- Champion remains NONE.
- Real money remains forbidden without explicit Owner authorization.
