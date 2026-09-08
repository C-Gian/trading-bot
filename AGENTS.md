# AGENTS.md — Trading Bot Operating Protocol

## Mission

Trading Bot is a research-first BTCUSDT spot trading system.

The Owner delegates quantitative research direction, product/technical architecture,
implementation coordination, experiment interpretation, and routine technical choices
to ChatGPT as Research Director. Coding agents are implementation executors.

The scientific objective is robust positive net expectancy after realistic costs and
execution assumptions, not a target hit rate.

Real money is forbidden unless a future explicit Owner gate authorizes it.

## Read order at the start of every work package

Read only what is needed, in this order:

1. `governance/SCIENTIFIC_CONSTITUTION.md`
2. `state/current_state.json`
3. `tasks/CURRENT_TASK.md`
4. `decisions/INDEX.md` and only ADRs relevant to the active task
5. the smallest additional source/doc/code set required for the work

Do not ask the Owner to recap project history. The repository is the source of truth.

## Sources of truth

Use one source for each kind of truth.

- Owner-controlled scientific rules:
  `governance/SCIENTIFIC_CONSTITUTION.md`
- Stable product/technical canon:
  `docs/canonical/`
- Current machine-readable project state:
  `state/current_state.json`
- Active autonomous work package:
  `tasks/CURRENT_TASK.md`
- Material decisions and their rationale:
  `decisions/ADR-*.md`
- Completed checkpoint summaries:
  `reports/checkpoints/`
- Experiment truth:
  `research/experiments/<experiment_id>/`
- Dataset identity/integrity:
  `data/manifests/`

Do not duplicate independently editable current state in several Markdown files.
Human-readable status pages must be generated from or consistent with
`state/current_state.json`.

Git history is part of the audit trail. Do not rewrite scientific history.

## Documentation hygiene

Do not turn canonical files into running journals.

At task completion:

- update `state/current_state.json` once, based on what actually passed;
- create one concise checkpoint report;
- create an ADR only for a material scientific/architectural decision;
- update indexes without duplicating the full content of records;
- create/update experiment records only if an actual experiment occurred;
- preserve negative/failed experiment results;
- keep verbose logs in artifacts, not in canonical documents.

Never append repeated summaries to the same document merely because another task ran.

Prefer a new immutable ADR/checkpoint/experiment record over silently rewriting
historical rationale.

## Scientific non-negotiables

- Deterministic tooling evaluates experiments; AI narrative does not determine results.
- Every material experiment must be preregistered before execution.
- Hypothesis, primary metric, evaluation design, parameter/search space, and trial
  budget are declared before results are observed.
- Failed and negative experiments are preserved.
- Results are never rewritten after observation.
- Material strategy changes require a new strategy/experiment version.
- Signals/features may use only information available at signal time.
- Transaction costs and execution assumptions are mandatory once backtesting begins.
- Ambiguous fills must be handled conservatively.
- Standard random K-fold is forbidden for overlapping financial time-series labels.
- Trial count/adaptive search must be tracked.
- Sealed evaluation data must be inaccessible to research agents.
- Exposed holdout data loses sealed status.
- Paper success is not permission for live capital.
- No agent may create, request, store, use, or deploy real-money credentials.

## Sealed historical boundary

Before strategy research begins, the repository must contain an explicit development
data cutoff in a material ADR and machine-readable state.

Research/strategy agents must not fetch, inspect, summarize, chart, or use detailed
BTCUSDT market data after that cutoff.

A later sealed evaluator may access the reserved interval under a separate controlled
workflow and explicit query budget.

Future prospective paper evidence remains stronger than any historical holdout.

## Engineering principles

- Monorepo.
- Python owns quantitative/domain logic.
- FastAPI is the HTTP boundary.
- React + TypeScript + Vite is the presentation layer.
- Authoritative dependency direction:
  frontend -> HTTP API -> application/domain/research code.
- Frontend code must not independently calculate authoritative trading outcomes.
- Keep HTTP routes thin.
- Prefer deterministic scripts over AI review for validation.
- Prefer simple conventional dependencies.
- Do not introduce infrastructure before demonstrated need.
- V1 is local and Windows-friendly.
- No V2 server complexity until justified.

## Autonomous execution

Work for as long as necessary to complete the active work package.

Do not stop for:

- ordinary library/tool choices;
- naming choices;
- formatting;
- routine refactors;
- test/debug cycles;
- local configuration details;
- minor UI choices;
- reversible implementation details.

Choose the simplest conventional option consistent with repository policy.

When tests fail, diagnose and fix them autonomously.

Stop only for:

- a contradiction with Owner-controlled governance that cannot be resolved safely;
- credentials/expenditure/external authorization requiring the Owner;
- a material change to the Owner's product/risk objective;
- any real-capital authorization.

## Work-package discipline

`tasks/CURRENT_TASK.md` is not a micro-task. It is the one active autonomous work
package and may intentionally contain many hours of implementation.

Complete its internal stages sequentially. Do not ask the Owner to relay intermediate
results between stages unless the task itself defines a hard scientific gate requiring
independent review.

At the end:

1. run all deterministic validation;
2. update the repository records cleanly;
3. archive the completed task snapshot if instructed;
4. commit all intended changes;
5. leave the working tree clean;
6. return only the concise checkpoint report requested by the task.

Do not push to GitHub unless the active task explicitly authorizes it.

## Reporting

Final executor reports should be short.

Do not paste raw logs unless a checkpoint failed and a small excerpt is needed to
identify a blocker.

The Research Director will inspect committed repository artifacts and interpret the
scientific meaning of the work.
