# ADR-0053 — Repository documentation hygiene and current-authority alignment

Status: ACCEPTED — Owner-directed maintenance, 2026-09-27

## Decision

Reduce stale Markdown context without rewriting scientific history.

Changes:
- align AGENTS/bootstrap/allocation/research-stage/executor navigation with the already-adopted G2 state;
- make Codex the primary engineering executor and Claude Code overflow, matching current Owner project instructions;
- compact completed task bodies in `tasks/archive/` into historical pointers to Git history;
- compact superseded canonical/navigation documents while preserving their paths;
- add concise documentation maps;
- compact clearly superseded contract versions;
- remove the unreferenced duplicate LIB-020 dossier while retaining the registry-canonical dossier.

## Preservation rule

No ADR, experiment result, checkpoint result, research-memory outcome, canonical library dossier or scientific result is rewritten or deleted by this maintenance.

The pre-cleanup tree remains recoverable at commit `0038c4d94f5569eb97353137051b7c84744ae9b7`.

Compaction changes context/navigation cost only. It does not change the scientific meaning of prior evidence.

The maintenance also repairs the project-state schema so the already-adopted G2 values validate, and reorders `current_state.json` to place `current_project_status` first without changing any state value.

## Current authority

Live state remains `state/current_state.json -> current_project_status`; current work remains `tasks/CURRENT_TASK.md`.
