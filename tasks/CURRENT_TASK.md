# CURRENT TASK — FINAL-PARKED-STATE-RECONCILIATION-V1

Status: FINITE_ARCHIVAL_CLOSURE_AUTHORIZED — MARKET/ALPHA WORK FORBIDDEN

## Authority

- Astra strategic decision:
  `ASTRA_POST_CANDIDATE_1_STRATEGIC_REALLOCATION_OR_PARK_2026-09`
- Canonical repository decision:
  `decisions/ADR-0042-PARK-ACTIVE-ALPHA-RESEARCH.md`
- Candidate #1 terminal decision:
  `decisions/ADR-0041-CANDIDATE-1-DEVELOPMENT-REJECTED-STRONG-STOP.md`

Definitive alpha-research disposition:

`PARKED_NO_CREDIBLE_EDGE_UNDER_CURRENT_CONSTRAINTS`

Candidate #1 remains closed as `CANDIDATE_1_CLOSED_DEVELOPMENT_REJECTED`.
Candidate Card #2 is not allocated.

## Objective

Perform exactly one finite governance/archive reconciliation so every future chat, executor and
existing application surface recovers the parked state unambiguously.

This is **not** a research task and **not** a new product build.

## Mandatory read set

Read only what is necessary:

1. `AGENTS.md`
2. `docs/operations/NEW_CHAT_BOOTSTRAP.md`
3. `governance/SCIENTIFIC_CONSTITUTION.md` current Version 3.0
4. `state/current_state.json`
5. this task
6. ADR-0041 and ADR-0042
7. `docs/canonical/STRATEGIC_ALLOCATION_MAP_V1.md`
8. the smallest status/schema/application files needed for reconciliation

Do not reopen historical research.

## Required repository reconciliation

### 1. Machine-readable current state

Make the operative current state explicit:

- project disposition: `PARKED_NO_CREDIBLE_EDGE_UNDER_CURRENT_CONSTRAINTS`;
- active alpha allocation: zero;
- active Candidate: none;
- Candidate #1: closed / `DEVELOPMENT_REJECTED`;
- Candidate #2: unallocated;
- market trial authorized: false;
- confirmation authorized: false;
- Champion: NONE;
- real money: false;
- sealed queries: 0;
- no automatic next research package.

Update the state schema as required.

Preserve historical counters/results. Do not delete or rewrite predecessor state.

### 2. Historical-vs-current ambiguity

Inspect only top-level/current-status fields that could mislead a new agent into treating old
prediction-first, ALIGNED, selected-family or prior-phase values as active instructions.

Do not erase them.

Either:
- mark them explicitly historical/superseded; or
- introduce one unambiguous current-strategy/current-project-status field that canonical consumers
  must prefer.

Do not perform a broad state redesign.

### 3. Bootstrap and executor policy

Reconcile the smallest canonical operating files so a new chat immediately learns:

- alpha research is parked;
- no Candidate/model/source search is authorized;
- `NO_TRADE` is the honest current action output;
- a new market-research allocation requires a valid reopening dossier and Astra;
- material product/risk/resource scope change may require Owner approval;
- real capital remains forbidden without explicit Owner authorization.

Ensure `AGENTS.md` and `docs/operations/NEW_CHAT_BOOTSTRAP.md` cannot accidentally resume an old
roadmap.

### 4. Existing active automation / prospective machinery

Inspect repository truth for project-internal alpha/prospective schedules, observers, continuation
hooks or automatic successors that are still marked active.

If present, disable their active authorization/status through the normal governance mechanism while
preserving code and historical records.

Do NOT delete the implementation.

Do NOT run it.

Do NOT create a new monitoring schedule.

### 5. Existing app/action surface

Inspect only the existing status/action path used by V1.

If it could currently imply an approved actionable LONG or validated strategy while the project is
parked, make the smallest change necessary so it reports the parked/no-validated-strategy state and
returns/displays `NO_TRADE`.

Do not redesign the UI and do not build a new analysis product.

If the existing app already fails closed to NO_TRADE with no Champion, document that and avoid
unnecessary code changes.

### 6. Preservation manifest/checkpoint

Create one concise durable closure artifact that records:

- parked disposition and ADRs;
- current canonical HEAD;
- Candidate #1 result identity and replay/provenance locations;
- key data manifests/caches by path/ID (do not copy or redownload data);
- protocol/result/research-memory locations;
- deterministic validation/replay commands;
- environment/dependency entry points needed to reproduce existing evidence;
- explicit reopening rules;
- Astra review retrieval/exposure note from ADR-0042;
- statement that no active alpha task remains.

This is an archival navigation artifact, not a new historical summary of every experiment.

### 7. Current task after closure

Archive this task.

Leave `tasks/CURRENT_TASK.md` in a terminal parked form such as:

`PARKED_NO_ACTIVE_RESEARCH_TASK`

It must contain no executor work and no scheduled future review.

## Absolute prohibitions

Do not:

- run any market experiment/backtest;
- inspect any additional market outcome;
- fetch/download new market data;
- access post-cutoff or sealed market data;
- calculate an alternate Candidate #1 result;
- create Candidate #2;
- design another strategy;
- run a source/feature/model search;
- create Frontier R&D;
- prepare confirmation;
- start shadow/prospective collection;
- create an automatic future “check again” task;
- pivot the product into an analysis tool;
- authorize real money.

## Validation

Run documentation/state/schema/unit/governance validation that does not access market outcomes.

Use `check.py --no-data` if compatible.

Do not run data-mode validation if it reads market outcomes.

## Git

Local commits on `main` are authorized after validation.

Do not push.

## Completion report

Return only:

`PARKED_STATE_RECONCILIATION_READY`

Then:

- changed_files
- local_commit_sha(s)
- project_disposition
- active_alpha_allocation
- candidate_1_status
- candidate_2_status
- legacy_current_status_ambiguity_resolved: YES/NO
- active_project_internal_alpha_schedules: NONE or list disabled
- app_action_state: PARKED_NO_TRADE / already-fail-closed / blocker
- preservation_artifact
- state_schema_validation: PASS/FAIL
- full_no_data_validation: PASS/FAIL
- market_outcomes_inspected: NO
- new_market_data_accessed: NO
- sealed_queries: 0
- champion: NONE
- real_money: false
- blockers: concise only
