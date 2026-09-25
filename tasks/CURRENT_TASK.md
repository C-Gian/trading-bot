# CURRENT TASK — IMPLEMENT-CANDIDATE-1-DEVELOPMENT-V1

Status: IMPLEMENTATION_AUTHORIZED_OUTCOME_EXECUTION_FORBIDDEN

## Authority

Scientific design is frozen in:

- `research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md`
- `decisions/ADR-0039-CANDIDATE-1-DEVELOPMENT-PROTOCOL-FREEZE.md`

Strategic authority remains Astra Directive V2 under Constitution 3.0 and
`docs/canonical/RESEARCH_STAGE_POLICY_V1.md`.

Candidate #1 disposition entering this task:

`CANDIDATE_1_ADMITTED_FOR_PROTOCOL_DESIGN`

The economic hypothesis is untested.

## Objective

Implement the frozen Candidate #1 Development Lab protocol completely enough that a later explicit
Research Director task can execute the single development market-outcome run without further
scientific choices.

This is an **implementation-only checkpoint**.

Do not inspect Candidate #1 forward returns or economic performance in this task.

## Mandatory read set

Read, in order:

1. `AGENTS.md`
2. `governance/SCIENTIFIC_CONSTITUTION.md` — current Version 3.0 only as active authority;
   historical appendices only if needed for compatibility
3. `state/current_state.json`
4. this task
5. `research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md`
6. `decisions/ADR-0039-CANDIDATE-1-DEVELOPMENT-PROTOCOL-FREEZE.md`
7. `research/protocols/CANDIDATE-1-FROZEN-ADMISSION-V1.md`
8. the smallest existing implementation/test files necessary for reuse

Do not reopen broad historical research.

## Scientific non-discretion

Implement the protocol exactly.

Claude Code may choose ordinary engineering structure, names and conventional libraries.

Claude Code may NOT change or reinterpret:

- sell-off event/state/population;
- source interval;
- decision/entry/exit timestamps;
- 24 bp primary cost profile;
- 36 bp cost stress;
- +30m delay stress;
- fixed ~4h timed exit;
- control definition;
- matching covariates/calipers/balance gates;
- economic MESIs;
- support/risk/stability gates;
- uncertainty method;
- prospective-detectability method;
- analysis/search budget;
- dispositions.

If a protocol sentence is genuinely impossible or materially ambiguous, stop with
`RESEARCH_DIRECTOR_PROTOCOL_CLARIFICATION_REQUIRED`. Do not invent a scientific resolution.

## Reuse mandate

Prefer existing proven infrastructure identified by the historical salvage audit.

Reuse where applicable:

- source manifests/provenance;
- spot and dual-market parsing;
- OI quantity selection;
- completed-bar/as-of utilities;
- cost/trade accounting;
- deterministic replay conventions;
- paired/statistical utilities where their semantics fit;
- existing test helpers.

Do not build a generalized playbook framework, generic feature platform, new predictor layer or
unused state modules.

Minimal Candidate #1-specific additions are preferred.

## Required implementation

Implement deterministic code for the frozen protocol, including:

### 1. Frozen episode/state ingestion

Consume the already-frozen admission event/state definitions rather than independently re-deriving a
different scientific population.

The implementation must be able to reproduce/consume:

- event T;
- Candidate/control state;
- `shock_z`;
- prior volatility;
- source validity metadata.

No new feature or gate.

### 2. Outcome-blind control matching

Implement the exact year-stratified matching contract from the protocol:

- covariates `shock_z` and `log(sigma_prior_1h)`;
- standardization within year over valid Candidate+control sell-offs;
- per-covariate absolute standardized caliper <=0.50;
- deterministic maximum-cardinality, minimum-total-squared-distance one-to-one matching without
  replacement;
- deterministic timestamp tie-break;
- required matching coverage and SMD balance calculations.

Matching must not load or inspect forward returns.

If a conventional optimization routine is used, tests must prove deterministic tie behavior and the
lexicographic optimization priorities required by the protocol.

### 3. Execution semantics

Implement, but do NOT execute on real Candidate #1 market outcomes:

Primary:
- decision T+15m;
- entry exact valid spot 1m open at T+16m;
- exit exact valid spot 1m open at T+4h+15m;
- LONG, fixed notional;
- no stop/target/trailing/scaling.

Missing exact entry/exit minute -> unscorable; no later replacement fill.

Primary costs:
- 10 bp fee each side;
- 2 bp adverse friction each side.

Cost stress:
- 15 bp fee each side;
- 3 bp adverse friction each side.

Delay stress:
- entry T+46m;
- exit remains T+4h+15m;
- primary 24 bp cost profile.

Use existing accounting semantics rather than duplicate cost arithmetic where possible.

### 4. Economic metrics

Implement:

- arithmetic gross return bp;
- fee/friction components;
- net return bp on initial notional;
- `ABS_NET_BP`;
- paired `INCREMENTAL_NET_BP`;
- break-even all-in transaction cost;
- yearly means;
- conservative annual contribution;
- 10% expected shortfall;
- chronological fixed-notional cumulative P&L and max drawdown;
- occupied minutes/fraction and bp per occupied hour;
- top 1/3/5 winner concentration;
- top-three-winners-removed absolute and paired incremental stresses;
- all primary/support/materiality/robustness gates exactly as frozen.

### 5. Dependence-aware uncertainty

Implement exactly:

- one-way UTC-calendar-month cluster-robust SE for Candidate absolute net returns;
- two-way cluster-robust SE for matched differences using Candidate month and matched-control month;
- standard finite-cluster corrections;
- two-sided 95% intervals;
- raw SD, per-year estimates and leave-one-year-out estimates.

Synthetic tests must cover:

- repeated observations inside a month;
- two-way overlapping clusters;
- degenerate/insufficient cluster cases;
- non-finite variance -> invalid uncertainty / no promotion.

Do not substitute bootstrap/HAC after implementation convenience.

### 6. Prospective detectability

Implement the frozen two-claim planning calculation:

- absolute MESI +25 bp/trade;
- incremental MESI +20 bp/pair;
- one-sided alpha .025 each;
- target power .80 each;
- <=12 months;
- prospective arrivals = minimum scorable Candidate count among 2022/2023/2024;
- planning SD = max(raw pooled SD, cluster-SE*sqrt(N), largest finite within-year raw SD);
- standard-normal required-N formula from the protocol.

Both claims must pass for promotion eligibility.

### 7. Deterministic adjudication

Implement the exact disposition ordering:

1. `INVALID_EXECUTION`
2. `BLOCKED_DATA_OR_SUPPORT`
3. `DEVELOPMENT_REJECTED`
4. `INCONCLUSIVE_NO_PROMOTION`
5. `PROMOTION_ELIGIBLE`

Tests must demonstrate that a later-stage attractive metric cannot override an earlier gate failure.

## Outcome-inspection prohibition

During this task, do NOT:

- run the Candidate #1 primary development evaluation on historical forward prices;
- compute real entry-to-exit returns for Candidate #1 episodes;
- compute real matched economic outcomes;
- print/chart/inspect any Candidate #1 economic performance;
- access post-cutoff or sealed data;
- fetch new market data.

Allowed:

- synthetic fixtures;
- deterministic unit/integration tests with synthetic prices/outcomes;
- replay of the already-authorized admission/support record;
- outcome-blind real-data checks needed to verify event identity/matching inputs, provided they do not
  read forward return/execution bars;
- static/provenance validation.

If an existing test accidentally invokes real Candidate #1 forward outcomes, stop and report it.

## Pre-execution implementation artifact

Create a concise machine-readable implementation-validation record and checkpoint report proving:

- protocol identity/hash;
- implementation paths;
- synthetic test coverage;
- admission-event identity/replay;
- outcome-blind matching mechanics;
- no market outcome inspection;
- no new data access;
- execution authorization false.

Do not create a development result file.

## Governance/state

Update canonical records so the final successful checkpoint state is:

`CANDIDATE_1_IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_AUTHORIZATION`

with:

- market_trial_authorized = false;
- economic_hypothesis_tested = false;
- market_outcomes_inspected = false;
- sealed_queries = 0;
- Champion NONE;
- real_money false.

Update the decision index to include ADR-0039 if not already indexed.

Archive this completed task and leave `tasks/CURRENT_TASK.md` as a Research-Director execution-review
checkpoint. It must explicitly forbid the market run until the Director reviews the implementation.

## Validation

Run:

- focused Candidate #1 tests;
- deterministic implementation replay/validation;
- ruff;
- mypy;
- full backend tests;
- frontend/governance checks as appropriate;
- repository `check.py --no-data` on a clean worktree if compatible with the repository workflow.

Do not run a data-mode check that computes Candidate #1 forward outcomes.

## Git

Local commits on `main` are authorized after validation.

- Keep commits logically clean.
- Do not rewrite history.
- Do not push.

## Completion report

Return only:

`CANDIDATE_1_IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_AUTHORIZATION`

Then:

- changed_files
- implementation_commit_sha(s)
- protocol_identity: PASS/FAIL
- admission_identity_replay: PASS/FAIL
- matching_implementation: PASS/FAIL
- execution_semantics: PASS/FAIL
- economic_metrics: PASS/FAIL
- uncertainty_implementation: PASS/FAIL
- prospective_detectability: PASS/FAIL
- adjudication_tests: PASS/FAIL
- synthetic_tests
- full_validation: PASS/FAIL
- real_candidate_outcomes_inspected: NO
- new_market_data_accessed: NO
- market_trial_authorized: false
- sealed_queries: 0
- champion: NONE
- real_money: false
- blockers: concise only
