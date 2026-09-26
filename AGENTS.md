## CURRENT TERMINAL PARK AUTHORITY — 2026-09-26

Active Constitution: Version 4.0.

Canonical mission:
`docs/canonical/OWNER_PRODUCT_MISSION_V2.md`.

Strategic disposition:
`SYSTEM_G1_TERMINAL_PARK` under ADR-0050.

System G1 is closed at `SYSTEM_G1_DEVELOPMENT_REJECTED_SELECTION_STAGE`.
System G2 is unallocated. Phase B is forbidden. Active strategy/alpha/system research allocation is
zero.

The reusable web-app/data/replay/ledger architecture is preserved, but there is no validated
trading policy. Production/live action must remain `NO_TRADE`.

No market experiment, configuration/playbook/model search, source search, prospective strategy
collection or engineering optimization is active.

Reopening requires a written material changed case and Astra strategic approval. Real capital
always requires explicit Owner authorization.

# AGENTS.md — Trading Bot Operating Protocol

## Current operative status — read before anything else

Strategy/system research is **parked** at:

`SYSTEM_G1_TERMINAL_PARK`

([ADR-0050](decisions/ADR-0050-ADOPT-ASTRA-SYSTEM-G1-TERMINAL-PARK.md)).

The canonical machine-readable truth is `state/current_state.json -> current_project_status`, which
takes precedence over historical top-level fields and older programme summaries.

- System G1: closed / selection-stage rejected.
- System G2: unallocated.
- Active alpha/system allocation: zero.
- Phase B: forbidden.
- Champion: NONE.
- Validated strategy: NONE.
- Production action: NO_TRADE.
- Prospective strategy collection: not authorized.
- Real money: false.
- `tasks/CURRENT_TASK.md` is `PARKED-NO-ACTIVE-RESEARCH-TASK`.

The Owner Product Mission V2 remains active. Parking is a research-allocation state, not a rollback
to the old LONG-only predecessor mission.

## Mission

Trading Bot is intended to become a professional, interpretable BTC paper-trading web application
under Owner Product Mission V2.

The intended product remains:

- continuous candle-level market prediction;
- selective `LONG / SHORT / NO_TRADE` decisions;
- multi-timeframe market/signal state including cyclical context;
- causal historical replay;
- visible prediction and trade annotations;
- realistic risk/execution accounting;
- local web app first;
- paper only unless a future explicit Owner decision authorizes real capital.

The project is not a search for one isolated alpha anomaly and is not an unconstrained indicator or
model tournament.

Statistics is the evaluator and anti-overfitting guardrail.

Current research parking means only that no validated active trading policy has earned deployment
and no successor allocation is justified under the present evidence. It does not alter the Owner
mission or convert G1 into a live strategy.

Decision hierarchy:

- Owner: mission, product/risk/resource scope and real capital;
- Astra: material research allocation / reopening / successor generation;
- ChatGPT Research Director: routine science, architecture, governance and interpretation;
- Claude Code: engineering executor when an active task authorizes implementation.

Real money is forbidden without explicit Owner authorization.

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
- Research stages, promotion, confirmation and Astra escalation:
  `docs/canonical/RESEARCH_STAGE_POLICY_V1.md`
- Current strategic allocation dispositions:
  `docs/canonical/STRATEGIC_ALLOCATION_MAP_V1.md`
- Candidate Cards and their admission records:
  `research/candidates/`
- How a prediction is defined, scored and reported (where predictions are used):
  `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md` and `_V2.md`
- Historical prediction-first source ladder (no longer authorizes work by itself):
  `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`
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
- Transaction costs and execution assumptions are mandatory for any claim of economic or
  trading profitability, and are not part of the primary scoring of a pure prediction
  experiment.
- Ambiguous fills must be handled conservatively.
- Standard random K-fold is forbidden for overlapping financial time-series labels.
- Every reported win rate is paired with sample size and prediction coverage.
- Probabilistic predictions are evaluated for calibration; magnitude is scored separately.
- Every metric is compared against predeclared chronological baselines with a
  dependence-aware uncertainty interval.
- A win rate obtained by trivial abstention, class imbalance or selective reporting is not
  predictive success.
- Uncalibrated model scores are never presented as probabilities, and magnitude strength is
  never presented as a probability.
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

## Cost-aware execution

Preserve scientific and engineering quality while minimizing executor usage.

- Use deterministic tools/scripts directly whenever they can perform a task reliably.
- Do not spawn a subagent for a trivial shell command or tiny edit where coordination would
  cost more than doing the work directly; give any subagent the smallest task-specific context
  and explicit acceptance criteria.
- The main Claude Code session verifies every delegated output before it affects scientific
  truth, governance, experiment classification or final commits.
- No subagent may change hypotheses after results, authorize sealed access, promote a Champion
  or make real-capital decisions.
- Do not claim a cost saving from model routing unless the runtime proves which model was used.

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

## Sequential Git workflow

`main` is the single sequential development and research branch. Future work packages
commit directly to local `main`; do not create a branch per work package. Never rewrite
history. Immutable checkpoint reports, experiment records, content hashes, and commit
SHAs form the audit trail. Failed experiments and failed checkpoints remain recorded.
The executor does not push unless the active task explicitly authorizes it.

## Reporting

Final executor reports should be short.

Do not paste raw logs unless a checkpoint failed and a small excerpt is needed to
identify a blocker.

The Research Director will inspect committed repository artifacts and interpret the
scientific meaning of the work.

## Conversation handover and token-efficient execution

A new ChatGPT conversation must bootstrap from repository truth, not from a manually reconstructed
chat recap. Follow `docs/operations/NEW_CHAT_BOOTSTRAP.md`.

Before proposing a new research direction, inspect the append-only research registry, the
strategic allocation map, `research/candidates/` and the predictive-generation closure/current-state
records so rejected, parked or blocked mechanisms cannot be silently retried under a new name.
Opening a new mechanism or Candidate Card requires Astra.

Default executor division:

- Astra decides material strategic research allocation (escalation list in
  `docs/canonical/RESEARCH_STAGE_POLICY_V1.md`).
- ChatGPT/Research Director decides routine science, architecture, preregistration and
  interpretation inside Astra's directive.
- Claude Code implements a substantial code block and stops when the active task says code is
  ready.
- The Owner runs heavy local downloads, backtests, full validation, Git commands and CI checks from
  copy/paste commands supplied by ChatGPT.
- Do not spend executor usage waiting for CPU-bound jobs, polling CI or performing routine Git
  operations unless the active task explicitly authorizes it.
- Avoid tiny implementation fragments that force repeated Owner intervention; batch adjacent coding
  work when scientifically safe.

The Owner reports concise PASS/FAIL/result paths. The Owner is not expected to debug or interpret
raw output.

