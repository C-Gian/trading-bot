# CURRENT TASK — RESEARCH-DIRECTOR-EXECUTION-REVIEW-CANDIDATE-1-DEVELOPMENT-V1

Status: BLOCKED_PENDING_RESEARCH_DIRECTOR_IMPLEMENTATION_REVIEW — MARKET RUN FORBIDDEN

## Context

- Protocol: `research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md`
  ([ADR-0039](../decisions/ADR-0039-CANDIDATE-1-DEVELOPMENT-PROTOCOL-FREEZE.md)).
- Implementation checkpoint: `reports/checkpoints/IMPLEMENT-CANDIDATE-1-DEVELOPMENT-V1.md`;
  outcome-blind validation record
  `reports/validation/CANDIDATE-1-DEVELOPMENT-IMPLEMENTATION-V1.json`.
- State: `CANDIDATE_1_IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_AUTHORIZATION`.
  The economic hypothesis is untested; no Candidate #1 market outcome has been inspected.

## Required decision (Research Director)

Review the implementation against the frozen protocol, including the implementation readings
listed in the checkpoint report. Then either request conforming corrections, or issue a separate
explicit repository task that authorizes the single Development execution.

## Executor instruction

The Candidate #1 Development market run is **forbidden** until the Research Director has reviewed
the implementation and a subsequent task explicitly authorizes it (state
`governance_transition_v3.candidate_1.development.execution_authorized` stays `false`).

- Do not run `scripts/run_candidate_1_development.py --execute`.
- Do not compute Candidate #1 entry-to-exit returns, matched outcomes or economic metrics on
  historical prices; do not read execution bars.
- No post-cutoff or sealed data; no new market data.

Sealed queries 0. Champion NONE. Real money false.
