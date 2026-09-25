# NEW CHAT BOOTSTRAP — Trading Bot

> **Current System G1 programme:** active Constitution is Version 4.0. Read
> `docs/canonical/OWNER_PRODUCT_MISSION_V2.md`, ADR-0044,
> `docs/canonical/PROFESSIONAL_MULTISIGNAL_SYSTEM_ARCHITECTURE_V1.md`, current state and
> `tasks/CURRENT_TASK.md`. The old parked programme remains historical evidence; no System G1
> historical performance execution is authorized unless the current task explicitly says so.

Purpose: make a new ChatGPT conversation recover the project from repository truth without
depending on the previous chat transcript.

This file is an operating protocol, not a current-state record. Live truth always comes from
the files below at the current `main` HEAD.

## Current operative status — read before anything else

Alpha research is **parked**:
`PARKED_NO_CREDIBLE_EDGE_UNDER_CURRENT_CONSTRAINTS`
([ADR-0042](../../decisions/ADR-0042-PARK-ACTIVE-ALPHA-RESEARCH.md); Candidate #1 closed as
`CANDIDATE_1_CLOSED_DEVELOPMENT_REJECTED`, [ADR-0041](../../decisions/ADR-0041-CANDIDATE-1-DEVELOPMENT-REJECTED-STRONG-STOP.md)).
The canonical machine-readable truth is `state/current_state.json` → `current_project_status`,
which takes precedence over every historical top-level field it lists (old prediction-first,
ALIGNED, selected-family, phase, runner and prospective-collection values are history, not
instructions).

- Active alpha allocation is zero; there is no active Candidate and Candidate Card #2 is
  unallocated.
- No Candidate, model, source, feature, horizon, R&D, confirmation or prospective-collection work
  is authorized, and no old roadmap, generation or lineage may be resumed.
- `NO_TRADE` is the honest current action output; the app reports parked / no validated
  strategy.
- A new market-research allocation requires a written reopening dossier establishing a material
  changed case (ADR-0042 triggers) **and** Astra approval. A material product, risk or resource
  scope change may also require Owner approval.
- Real capital remains forbidden without a separate explicit Owner authorization.
- `tasks/CURRENT_TASK.md` is `PARKED-NO-ACTIVE-RESEARCH-TASK`: there is no executor work.

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

- BTC spot `LONG` / `NO_TRADE` only unless the Owner explicitly changes product scope.
- Paper only; no real capital. `NO_TRADE` is a valid permanent outcome.
- Historical development is exposed exploratory evidence; prospective confirmation is earned
  only through the Promotion Gate and must resolve its economic MESI within <= 12 months.
- Sealed/post-cutoff data remains inaccessible to development research.
- Champion remains NONE until an admissible result explicitly changes it.
- Search memory never resets merely because a new generation or chat begins.
