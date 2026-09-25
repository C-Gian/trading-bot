## CURRENT SYSTEM G1 AUTHORITY — 2026-09-25

Active Constitution: Version 4.0.

Read `docs/canonical/OWNER_PRODUCT_MISSION_V2.md`, ADR-0044 and
`docs/canonical/PROFESSIONAL_MULTISIGNAL_SYSTEM_ARCHITECTURE_V1.md`.

The current bounded programme is System G1: continuous 15m predictions, selective
LONG/SHORT/NO_TRADE paper decisions, exactly two initial playbooks, shared multi-timeframe state and
causal replay.

The predecessor ADR-0042 parked decision and Candidate #1 rejection remain historical evidence.

No historical System G1 market-performance run is authorized until a later Research Director task.
Checkpoint 1 (ADR-0045) and the cycle quality gate (ADR-0046, cycle = active component) are
accepted. The frozen Development V1 implementation is executor-complete; the current task is the
review-only `RESEARCH-DIRECTOR-G1-INCOMPLETE-BAR-FIX-REVIEW-V1` (ADR-0047 correction). The historical G1 runner refuses
until the state explicitly authorizes it, and executor market work is forbidden.
The action guard fails closed on `current_project_status.validated_strategy = null` (NO_TRADE).

# AGENTS.md — Trading Bot Operating Protocol

## Current operative status — read before anything else

Alpha research is **parked**:
`PARKED_NO_CREDIBLE_EDGE_UNDER_CURRENT_CONSTRAINTS`
([ADR-0042](decisions/ADR-0042-PARK-ACTIVE-ALPHA-RESEARCH.md); Candidate #1 closed as
`CANDIDATE_1_CLOSED_DEVELOPMENT_REJECTED`, [ADR-0041](decisions/ADR-0041-CANDIDATE-1-DEVELOPMENT-REJECTED-STRONG-STOP.md)).
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

## Mission

Trading Bot is a research-first project intended to become a practical, reproducible BTC
spot `LONG` / `NO_TRADE` paper system (Constitution Version 3.0, ADR-0036). Its final product
advancement objective is practical, risk-constrained economic usefulness, demonstrated by
frozen prospective economic confirmation. `NO_TRADE` is a valid operational output and a valid
permanent project outcome.

Governed sequence:
`PLAUSIBLE MECHANISM -> EXPLICIT PLAYBOOK -> BOUNDED HISTORICAL DEVELOPMENT -> PROMOTION GATE -> FROZEN PROSPECTIVE ECONOMIC CONFIRMATION`
(`docs/canonical/RESEARCH_STAGE_POLICY_V1.md`). Historical development is exposed exploratory
evidence and never becomes fresh confirmation through rescoring or renaming.

Decision hierarchy:

- the Owner controls mission, evaluation principles, product/risk objective and real capital;
- Astra is the strategic scientific authority for material research-allocation decisions;
- the ChatGPT Research Director owns routine scientific design, architecture, tasking,
  implementation review, experiment adjudication and ordinary decisions inside Astra's
  directive;
- Claude Code is the sole coding / repository implementation executor. Codex is not part of
  the normal implementation workflow.

Where a playbook uses a prediction, prediction quality remains a distinct quantity.
Directional win rate is a primary human-facing metric and is never interpreted alone. It
is always reported with sample size and coverage, alongside calibration, magnitude error,
predeclared baselines and dependence-aware uncertainty.

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

