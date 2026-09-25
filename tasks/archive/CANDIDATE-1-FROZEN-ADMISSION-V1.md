# CURRENT TASK — CANDIDATE-1-FROZEN-ADMISSION-V1

Status: ACTIVE — ONE FROZEN ADMISSION CALCULATION

## Authority

- Astra adjudication of the executor Candidate #1 support block:
  `PRIOR_SUPPORT_DIAGNOSTIC_NONAUTHORITATIVE — ONE_DIRECTOR_FROZEN_ADMISSION_ALLOWED`.
- Research Director freeze: `research/protocols/CANDIDATE-1-FROZEN-ADMISSION-V1.md`
  ([ADR-0037](../decisions/ADR-0037-CANDIDATE-1-ASTRA-ADJUDICATION-AND-FROZEN-ADMISSION-SPEC.md)).
- Strategic authority: Astra directive V2 / Constitution 3.0 ([ADR-0036](../decisions/ADR-0036-OWNER-PRACTICAL-ECONOMIC-OBJECTIVE-AND-CONSTITUTION-V3.md)).

## Preserved diagnostic

The earlier `73 total / 25 joint-state` result is permanently preserved as
`EXPOSED_SUPPORT_DIAGNOSTIC — DIRECTOR_UNAPPROVED_SPECIFICATION`
(`research/candidates/evidence/CANDIDATE-1-EXECUTOR-SUPPORT-DIAGNOSTIC-V1/`). It is not the
terminal Candidate #1 disposition.

## Work

1. Execute exactly one support calculation of the frozen specification with
   `scripts/audit_candidate_1_frozen_admission.py`, using only already-authorized cached
   pre-cutoff data and the admitted OI interval 2022-2024.
2. No forward returns, trade outcomes, labels, models or backtest performance. No threshold grid,
   preview run, alternate cooldown, alternate risk normalization, alternate state definition, new
   source or second admission calculation. A deterministic rerun is allowed only to correct a
   demonstrated implementation defect without changing the frozen specification.
3. Apply the frozen gates and record exactly one operative disposition:
   - every gate passes → `CANDIDATE_1_ADMITTED_FOR_PROTOCOL_DESIGN` (no market trial);
   - any gate fails → `CANDIDATE_1_CLOSED_CURRENT_ALLOCATION_SUPPORT_OR_FEASIBILITY`, project
     state `STRONG_STOP_PENDING_ASTRA`, economic hypothesis untested, no Candidate #2 or
     successor designed.
4. Run deterministic validation and commit locally on `main`. Do not push.

Sealed queries 0. Champion NONE. Real money false.
