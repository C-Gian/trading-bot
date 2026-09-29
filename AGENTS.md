# AGENTS.md — Trading Bot Operating Protocol

## 1. Bootstrap from live truth

Do not infer current status from historical reports, archived tasks or old architecture files.

Read in this order:

1. `state/current_state.json -> current_project_status` (this block is deliberately first in the JSON; do not read the historical remainder unless needed)
2. `tasks/CURRENT_TASK.md`
3. `docs/canonical/OWNER_PRODUCT_MISSION_V2.md`
4. `governance/SCIENTIFIC_CONSTITUTION.md`
5. only the ADRs/contracts explicitly referenced by the active task

For a new chat, follow `docs/operations/NEW_CHAT_BOOTSTRAP.md`.

Current state at this revision:
- G1: closed / terminal park;
- G2: `G2_DEVELOPMENT_SYSTEM` allocated;
- active package: `G2-02-BASELINE-AND-DIAGNOSTICS-V1`;
- market/economic execution: authorized only for frozen G2-02 exposed development through 2024; protected 2025+ remains forbidden;
- validated strategy: NONE;
- Champion: NONE;
- operational action: NO_TRADE;
- real money: false.

The machine-readable state and active task always override this human-readable snapshot.

## 2. Mission

Trading Bot is a professional, interpretable BTC paper-trading web application.

Owner Product Mission V2 requires:
- continuous market prediction at eligible candles;
- selective `LONG / SHORT / NO_TRADE`;
- multi-timeframe state including cyclical context;
- causal historical replay;
- visible prediction and decision state;
- realistic risk/execution accounting;
- local web app first;
- paper only unless the Owner explicitly authorizes real capital.

Do not reduce the project to an indicator tournament or isolated-alpha search.

## 3. Decision authority

- **Owner** — mission, product/risk/resource scope and any real-capital authorization.
- **Astra** — material research allocation, reopening/expanding closed lineages, successor generations, major architecture exceptions and Champion-level decisions.
- **ChatGPT Research Director** — routine science, architecture, governance, tasking, checkpoint review and result interpretation inside the authorized programme.
- **Codex** — primary engineering executor.
- **Claude Code** — overflow engineering executor when Codex is unavailable or intentionally delegated.

Executors implement; they do not redefine scientific truth.

## 4. Current G2 authority

The active strategic chain is:
- `docs/canonical/OWNER_PRODUCT_MISSION_V2.md`
- `governance/SCIENTIFIC_CONSTITUTION.md`
- `reports/strategic/ASTRA_TRADING_BOT_DEVELOPMENT_SYSTEM_DIRECTIVE_V2.md`
- `decisions/ADR-0052-ADOPT-ASTRA-G2-DEVELOPMENT-SYSTEM-AND-OPEN-G2-00.md`
- `docs/canonical/G2_PROFESSIONAL_KNOWLEDGE_MODEL_V1.md`
- `docs/canonical/G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1.md`
- `research/g2/G2_DATA_EXPOSURE_AND_EXECUTION_MANIFEST_V1.md`
- `research/g2/G2_CYCLE_CAUSALITY_CHECKPOINT_V1.md`
- `research/g2/G2_DEVELOPMENT_PROTOCOL_V1.md`

G1 and earlier programmes remain historical evidence, not templates to revive.

## 5. Scientific non-negotiables

- deterministic tooling evaluates experiments;
- causal/point-in-time data only;
- no look-ahead or incomplete-bar leakage;
- realistic fees/costs/execution for economic claims;
- ambiguous fills handled conservatively;
- development evidence remains development evidence;
- protected data lose independence once used for adaptation;
- overlapping time-series labels are not IID samples;
- prediction, policy and execution are scored separately;
- uncalibrated scores are never presented as probabilities;
- search/revision history is append-only;
- failed/negative results remain visible;
- no post-hoc rescue by renaming, threshold drift, horizon selection or model substitution;
- real money requires explicit Owner authorization.

## 6. Anti-loop / search memory

Before proposing a mechanism, feature family, horizon or model lineage, inspect the smallest relevant subset of:
- `research/memory/registry/families/`
- `research/memory/registry/outcomes/`
- `research/candidates/`
- `reports/reviews/METHODOLOGICAL-QUALIFICATIONS-V1.md`

A renamed idea is not new evidence. Prior negative evidence remains binding for the exact tested formulation.

## 7. Documentation hygiene

Use one source for each kind of truth:
- live state: `state/current_state.json`;
- active work: `tasks/CURRENT_TASK.md`;
- Owner mission: `docs/canonical/OWNER_PRODUCT_MISSION_V2.md`;
- scientific governance: `governance/SCIENTIFIC_CONSTITUTION.md`;
- current G2 contracts: the G2 files listed above;
- material decisions: `decisions/ADR-*.md`;
- experiment truth: `research/experiments/`;
- data identity: `data/manifests/`;
- historical results: checkpoint/report/registry artifacts.

Do not use `tasks/archive/` as current context. Archived task bodies are compact historical pointers; Git history contains their full text.

Do not read all Markdown files “for context.” Read only the active chain and the minimum lineage required by the task.

## 8. Engineering principles

- monorepo;
- Python owns quantitative/domain logic;
- FastAPI is the HTTP boundary;
- React + TypeScript + Vite is presentation;
- frontend never independently computes authoritative trading outcomes;
- shared scientific core between replay and future/live modes;
- conventional dependencies;
- local/Windows-friendly V1;
- deterministic tests and scripts over narrative validation.

## 9. Work-package discipline

`tasks/CURRENT_TASK.md` is the only active autonomous work package.

For an implementation task:
1. read the smallest referenced file set;
2. implement the full bounded checkpoint;
3. use focused/fast deterministic validation while iterating;
4. run the complete repository/scientific validation only when the checkpoint requires final validation;
5. save verbose logs/artifacts to files;
6. update state only after the gate actually passes;
7. preserve failed results;
8. return a concise report.

Do not ask the Owner to write code, debug, inspect raw logs or reconstruct project history.

### Executor-run vs Owner-run jobs

Normal engineering work remains autonomous. Executors may run:
- focused tests;
- lint/type checks;
- builds;
- ordinary deterministic validations;
- medium-duration repository checks.

Do not weaken validation merely to make execution faster.

A job is `HEAVY_OWNER_RUN` when either:
- the active task explicitly classifies it that way; or
- available evidence indicates it is likely to take roughly one hour or more / is naturally an hours-scale backtest, development run, evaluation, stress run, large replay or large data job.

For `HEAVY_OWNER_RUN` jobs:
- Codex/Claude must prepare the runner, configuration, manifests, frozen identities and pre-run checks completely;
- the executor must **not** start the heavy job, including in a background/detached shell;
- stop with the exact marker `WAITING_FOR_OWNER_RUN`;
- report the exact command the Owner should execute;
- report the canonical output artifact paths that will contain the results;
- after the Owner reports completion, read those artifacts directly from the repository/workspace; do not ask the Owner to paste or manually summarize results;
- interrupted/partial runtime state is not scientific evidence.

This boundary does **not** apply to an ordinary 10–30 minute validation solely because it is inconvenient. Medium jobs may remain executor-run when they are observable.

### Long-job observability

Any executor-run job expected to take more than about one minute must follow
`docs/operations/LONG_RUNNING_JOB_PROGRESS_V1.md`.

In particular:
- use progress/heartbeat output instead of a silent wait;
- when Claude Code runs a shell command in background, keep it inspectable through Claude Code's task/background-shell monitoring rather than hiding progress behind repeated polling;
- expose phase, elapsed time, heartbeat and ETA when defensibly estimable;
- never fabricate percentage or ETA.

During development, prefer focused tests after a local fix. If a final full check fails late, diagnose and repair with the smallest affected checks first, then perform the required final full validation once the candidate is ready. Do not repeatedly rerun the whole repository gate after every small fix.

## 10. Git / repository history

Scientific history is append-only. Never rewrite Git history to make past work disappear.

Historical Markdown may be compacted in the current tree when its authoritative content is already preserved by Git plus ADR/checkpoint/experiment records. A compacted pointer is not current authority.

### Owner-controlled Git mutations

Git mutation is Owner-controlled unless the Owner explicitly overrides this rule for a specific action.

Executors may use read-only Git commands such as:
- `git status`;
- `git diff`;
- `git log`;
- `git show`.

Executors must not autonomously:
- commit;
- push;
- pull/merge;
- rebase;
- reset;
- tag;
- create/delete/move branches;
- force-update refs.

File edits in the working tree are allowed and expected. The Owner handles repository-history mutations.

External deployment also requires explicit authorization from the active task or Owner.
