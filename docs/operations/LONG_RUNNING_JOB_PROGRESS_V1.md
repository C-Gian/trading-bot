# Long-running Job Progress V1

Status: **REQUIRED OPERATING STANDARD**

Purpose: long-running repository operations must be observable and reproducible without turning
agent chat into a waiting room.

This document implements the permanent execution boundary in `AGENTS.md`.

## 1. Execution classes

### EXECUTOR_RUN

Focused tests, builds, ordinary deterministic validations and medium-duration repository checks may
be run autonomously by Codex/Claude.

If an executor-run command is expected to take more than about one minute, it must expose live
runtime progress as defined below.

### HEAVY_OWNER_RUN

A job is HEAVY_OWNER_RUN when:
- the active task explicitly says so; or
- available evidence indicates an approximately one-hour-or-longer / hours-scale backtest,
  development run, evaluation, stress run, large replay or large data job.

The executor prepares the job completely but does not start it.

The executor stops with:

`WAITING_FOR_OWNER_RUN`

and provides:
- exact command;
- expected success condition;
- canonical output artifact paths;
- runtime progress location if applicable.

The Owner executes the command. On the next turn the executor reads the generated artifacts directly.
The Owner should not have to copy large results into chat.

## 2. Runtime telemetry

Applies to executor-run long jobs and Owner-run heavy jobs.

Runtime telemetry is operational state, not scientific evidence.

Use a git-ignored directory such as:

`.runtime/jobs/<job-id>/`

Minimum state:
- job id/type;
- execution class;
- status: QUEUED/RUNNING/PASS/FAIL/CANCELLED;
- current phase name and phase index/count;
- completed/total work units when measurable;
- percent only when a defensible denominator exists;
- start/update timestamps;
- elapsed time;
- ETA when defensibly estimable, otherwise UNKNOWN;
- heartbeat age;
- current activity/message;
- last completed phase;
- final exit code/error summary;
- canonical result artifact paths.

Writes to the live status file should be atomic. Keep an append-only operational log/tail separately.

Never fabricate a percent or ETA.

## 3. Terminal UX

Long commands should support `--progress`.

Example:

`python scripts/check.py --progress`

The terminal should continuously make clear:
- what phase is running;
- whether the child process is alive;
- elapsed time;
- phase progress where measurable;
- estimated remaining time when current units or historical duration support it;
- where canonical outputs will be written.

A heartbeat must continue even when a child command itself emits no output.

When Claude Code launches an EXECUTOR_RUN command in the background, it should remain visible through
Claude Code's task/background-shell monitoring. Do not hide a live job behind repeated agent polling.

## 4. Local web UI

Expose read-only local job status through an operations API and a small Operations panel/page.

It should show:
- active/recent jobs;
- execution class;
- progress bar when percent exists;
- phase X/Y;
- elapsed;
- ETA or “unknown”;
- last heartbeat;
- running/pass/fail;
- a short tail of operational log messages;
- canonical output paths when complete.

Polling is sufficient; SSE/WebSockets are optional.

No UI control may silently change scientific parameters.

## 5. Heavy-run result handoff

Hours-scale runs must write their substantive results to deterministic, versioned artifacts.

The chat handoff is intentionally tiny:
1. executor prepares and stops at `WAITING_FOR_OWNER_RUN`;
2. Owner runs the exact command and monitors progress;
3. Owner reports only completion/failure;
4. executor reads the output files directly and continues analysis.

Partial/interrupted output under `.runtime/jobs/` is never promoted to a canonical result merely
because it exists.

Where deterministic boundaries allow it, heavy runners should support resume/checkpointing without
changing the frozen scientific identity.

## 6. Validation-efficiency rule

During implementation:
1. run focused tests/checks for the files changed;
2. do not repeatedly run the complete repository check after every small fix;
3. run the complete repository/scientific check on the intended final candidate when the checkpoint
   requires it;
4. if the full check fails, diagnose with the smallest affected checks, repair, then perform the
   required final full validation.

The final gate is not weakened: optimization means avoiding redundant recomputation during
iteration, not deleting scientific assertions.

For slow suites, profile phase durations and slow tests before optimizing. Parallelization is allowed
only when independence and deterministic equivalence are demonstrated.

Scientific runners still require whatever preregistered integrity gate applies before outcomes are
opened.
