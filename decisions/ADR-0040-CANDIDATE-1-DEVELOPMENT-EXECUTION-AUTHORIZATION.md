# ADR-0040 — Authorize the single Candidate #1 Development execution

Status: ACCEPTED — Research Director, 2026-09-25

## Basis

The Research Director reviewed the implementation checkpoint
`reports/checkpoints/IMPLEMENT-CANDIDATE-1-DEVELOPMENT-V1.md`, the outcome-blind validation record
`reports/validation/CANDIDATE-1-DEVELOPMENT-IMPLEMENTATION-V1.json`, the implementation module,
runner and synthetic tests against the frozen
`research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md`.

No Candidate #1 historical forward return or economic outcome was inspected during this review.

Review findings:

- protocol / ADR / admission identities: PASS;
- admission population replay: PASS (335 valid; 116 Candidate / 219 control);
- outcome-blind matching: PASS (101 pairs; all frozen coverage/balance gates pass);
- execution semantics and cost accounting: PASS on synthetic fixtures;
- economic metric implementation: PASS on synthetic fixtures;
- one-way / two-way cluster uncertainty: PASS on synthetic fixtures;
- prospective detectability implementation: PASS on synthetic fixtures;
- fail-closed adjudication ordering: PASS;
- repository no-data validation: PASS.

The implementation readings documented by the executor are accepted as ordinary engineering
interpretations of the frozen protocol. The in-repository Hungarian assignment implementation is
accepted because deterministic tests verify exactness against brute force / SciPy and real matching
uses only T-known covariates.

## Decision

Authorize exactly **one** historical Development Lab execution of Candidate #1 using the frozen
protocol and the already-authorized cached pre-cutoff 2022-2024 data.

This authorization permits the first inspection of Candidate #1 economic outcomes.

It does not authorize:

- any change to the frozen protocol;
- any second execution under a changed scientific specification;
- parameter, horizon, matching, cost, delay or subgroup search;
- new market data;
- post-cutoff or sealed-data access;
- Candidate #2;
- prospective confirmation;
- Champion designation;
- real capital.

The executor may run the frozen result once, record the complete result and deterministic provenance,
and apply the already-coded mechanical gate ordering. The Research Director retains adjudication of
the scientific checkpoint and all subsequent allocation decisions.

## Accepted implementation conventions

The following are recorded, not newly optimized:

- canonical BTCUSDT spot 1m parquet supplies execution prices;
- sample SD uses ddof=1;
- matching balance uses Austin SMD;
- deterministic matching tie-break is Candidate timestamp then earliest feasible control preserving
  the frozen optimum;
- cluster CIs use t critical values with the documented cluster degrees of freedom;
- ES10 is the mean of the worst ceil(10% of observations);
- break-even all-in cost is mean gross return in bp;
- the custom Hungarian solver is an engineering implementation of the frozen matching objective.

## Post-execution state

After the one execution the executor must immediately remove execution authorization and leave the
project at:

`CANDIDATE_1_DEVELOPMENT_RESULT_PENDING_RESEARCH_DIRECTOR_ADJUDICATION`

The raw mechanically determined Development disposition may be recorded, but it does not authorize
a successor action.

Champion remains NONE. Sealed queries remain 0. Real money remains false.
