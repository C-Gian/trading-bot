# Long-running Job Progress V1

Status: **REQUIRED OPERATING STANDARD**

Purpose: no long-running repository operation should look hung to the Owner.

Applies to:
- `scripts/check.py`;
- G2 development/evaluation/stress runners;
- backtests/replays/audits expected to take more than about one minute;
- future data acquisition or research jobs with measurable work units.

## Runtime contract

Long jobs emit runtime-only progress events. Progress state is operational telemetry, not scientific
evidence and is never committed as a research result.

Minimum state:
- job id/type;
- status: QUEUED/RUNNING/PASS/FAIL/CANCELLED;
- current phase name and phase index/count;
- completed/total work units when measurable;
- percent only when a defensible denominator exists;
- start/update timestamps;
- elapsed time;
- ETA when defensibly estimable, otherwise UNKNOWN;
- heartbeat age;
- current message;
- last completed phase;
- final exit code/error summary.

Never fabricate a percent or ETA.

## Terminal UX

Long commands must support `--progress`.

Example:

`python scripts/check.py --progress`

The terminal should continuously make clear:
- what phase is running;
- whether the child process is alive;
- elapsed time;
- phase progress where measurable;
- estimated remaining time when historical/current-unit information supports it.

A heartbeat must continue even when a child command itself emits no output.

## Local web UI

Expose read-only local job status through an operations API and a small Operations panel/page.

It should show:
- active/recent jobs;
- progress bar when percent exists;
- phase X/Y;
- elapsed;
- ETA or “unknown”;
- last heartbeat;
- running/pass/fail;
- a short tail of operational log messages.

Polling is sufficient; SSE/WebSockets are optional.

No UI control may silently change scientific parameters.

## Persistence

Use a git-ignored runtime directory such as `.runtime/jobs/` with atomic state writes plus an
append-only operational log.

Optional historical duration telemetry may be stored there to estimate future phase duration. Such
ETA history is convenience telemetry only and must never enter scientific artifacts.

## Validation-efficiency rule

During implementation:
1. run focused tests/checks for the files changed;
2. do not repeatedly run the complete repository check after every small fix;
3. run the complete repository check on the intended final candidate;
4. if the full check fails, diagnose with the smallest affected checks, repair, then perform the
   required final full validation.

Scientific runners still require whatever preregistered integrity gate applies before outcomes are
opened.
