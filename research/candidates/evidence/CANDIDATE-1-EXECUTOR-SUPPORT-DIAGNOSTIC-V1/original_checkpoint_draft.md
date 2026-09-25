# Checkpoint — GOVERNANCE-TRANSITION-AND-CANDIDATE-ADMISSION-V1

Status: **EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_REVIEW**. Starting HEAD
`c163887d16610ce884d0e3a8c326204df4122a79`.

## Governance transition ([ADR-0036](../../decisions/ADR-0036-OWNER-PRACTICAL-ECONOMIC-OBJECTIVE-AND-CONSTITUTION-V3.md))

- Constitution **Version 3.0 — practical economic usefulness** (Owner-authorized 2026-09-25,
  Astra directive V2). Version 2.0 is preserved verbatim as Appendix B, Version 1.0 verbatim as
  Appendix A; the diff to the Constitution is insertion-only. All rigour protections carried
  forward; the evidence hierarchy is preserved and prospective evidence outranks exposed
  historical development.
- Canonical `docs/canonical/RESEARCH_STAGE_POLICY_V1.md` (Development Lab, Promotion Gate,
  Confirmation, Frontier R&D, Astra escalation) and `docs/canonical/STRATEGIC_ALLOCATION_MAP_V1.md`.
- Hierarchy: Astra (strategic), ChatGPT Research Director (routine), Claude Code (sole
  executor; Codex out of the normal workflow) — `AGENTS.md`, `docs/operations/NEW_CHAT_BOOTSTRAP.md`,
  `governance/EXECUTOR_POLICY.md` (Version 1 preserved verbatim).
- Append-only `reports/reviews/METHODOLOGICAL-QUALIFICATIONS-V1.md`: Q-001 power-gate sign
  description, Q-002 macro contamination reasoning, Q-003 V2 pooled enrichment composition. No
  historical artifact was modified.

## Candidate #1 admission ([ADR-0037](../../decisions/ADR-0037-CANDIDATE-1-SOURCE-SUPPORT-ADMISSION-BLOCK.md))

Lineage `DISTINCT_BUT_HEAVILY_PRIOR_CONSTRAINED` recorded (not repeated). Deterministic,
outcome-free admission audit `scripts/audit_candidate_1_admission.py` →
`reports/validation/CANDIDATE-1-SOURCE-SUPPORT-ADMISSION-V1.json` (replay PASS).

- Source: feasible (verified spot and USD-M 1m klines; OI 5m quantity; 2022-2024 admissible).
- Timing: feasible (conservative OI rule `create_time <= T-5m`, age <= 15m).
- Support: **infeasible** under the rule declared before the run — reference sell-offs 73,
  joint positioning state 25 < 30.

Disposition **`CANDIDATE_1_REJECTED_OR_BLOCKED`** (support-blocked before protocol design; no
outcome inspected). No replacement candidate.

## Validation

State validates against `contracts/project_state.schema.json`; governance checks, targeted
tests and ruff pass (see the executor report). No market trial, backtest, model fit or
post-cutoff access; sealed queries 0; Champion NONE; real money false.

## Next

`STRATEGIC-REALLOCATION-AFTER-CANDIDATE-1-SUPPORT-BLOCK` — Research Director review, then Astra
reallocation. No executor work authorized.
