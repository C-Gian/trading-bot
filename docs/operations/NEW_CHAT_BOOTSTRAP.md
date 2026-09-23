# NEW CHAT BOOTSTRAP — Trading Bot

Purpose: make a new ChatGPT conversation recover the project from repository truth without
depending on the previous chat transcript.

This file is an operating protocol, not a current-state record. Live truth always comes from
the files below at the current `main` HEAD.

## Mandatory bootstrap order

At the start of a new Research Director chat:

1. resolve the current `main` HEAD;
2. read `AGENTS.md`;
3. read `governance/SCIENTIFIC_CONSTITUTION.md`;
4. read `state/current_state.json`;
5. read `tasks/CURRENT_TASK.md`;
6. read `decisions/INDEX.md` and only the ADRs relevant to the current task;
7. before proposing any new research family, inspect:
   - `research/memory/registry/families/`;
   - `research/memory/registry/outcomes/`;
   - predictive generation closure/state fields in `state/current_state.json`;
8. read the latest dated handover snapshot under `reports/handover/` only as a navigation
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

## Executor / Owner division

Default workflow is token-efficient:

- ChatGPT/Research Director: science, architecture, frozen experiment design, result
  interpretation, next allocation.
- Codex/Claude Code: write the substantial code block requested by `CURRENT_TASK.md`.
- Owner: run the provided acquisition/backtest/validation/Git/CI commands locally and return
  concise PASS/FAIL/output to ChatGPT.
- Heavy downloads, backtests, full validation, Git operations and CI polling are NOT executor
  work unless `CURRENT_TASK.md` explicitly says otherwise.

Avoid micro-tasks that force repeated Owner intervention. One executor implementation block and
one Owner execution/validation step per cycle is the default target.

## Safety / research boundaries

- BTCUSDT only unless the Owner explicitly changes product scope.
- Paper only; no real capital.
- Sealed/post-cutoff data remains inaccessible to development research.
- Champion remains NONE until an admissible result explicitly changes it.
- Search memory never resets merely because a new generation or chat begins.
