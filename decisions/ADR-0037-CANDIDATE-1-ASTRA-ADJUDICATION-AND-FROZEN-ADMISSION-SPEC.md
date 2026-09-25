# ADR-0037 — Candidate #1: executor diagnostic is non-authoritative; one Director-frozen admission

Status: ACCEPTED (Astra adjudication and Research Director freeze, 2026-09-25)

Strategic authority remains `ASTRA_TRADING_BOT_STRATEGIC_OPERATING_DIRECTIVE_V2`
([ADR-0036](ADR-0036-OWNER-PRACTICAL-ECONOMIC-OBJECTIVE-AND-CONSTITUTION-V3.md)).

## Context

During `GOVERNANCE-TRANSITION-AND-CANDIDATE-ADMISSION-V1` the executor ran an outcome-free
support audit of Candidate #1 under a specification it chose itself (24h spot log return
`<= -5%`, 72h separation, 24h OI falling **and** 24h relative price falling, `>= 30` per arm) and
drafted a support block (73 events, 25 joint-state). No Research Director or Astra
specification existed; the draft was never committed.

## Decision

1. **Astra adjudication:** `PRIOR_SUPPORT_DIAGNOSTIC_NONAUTHORITATIVE — ONE_DIRECTOR_FROZEN_ADMISSION_ALLOWED`.
2. The executor audit is permanently preserved, verbatim, as
   **`EXPOSED_SUPPORT_DIAGNOSTIC — DIRECTOR_UNAPPROVED_SPECIFICATION`** in
   `research/candidates/evidence/CANDIDATE-1-EXECUTOR-SUPPORT-DIAGNOSTIC-V1/` (committed before
   any record was changed). It is not a Candidate #1 disposition, not an admission input and not
   a rejection. Its counts remain exposed lineage information.
3. The Research Director froze the Candidate #1 admission specification
   `research/protocols/CANDIDATE-1-FROZEN-ADMISSION-V1.md` before any new calculation: 4h shock
   standardized by 168h prior realized volatility ending at `T-4h`, first crossing of
   `shock_z <= -2.0`, 4h suppression; joint state = 4h OI-quantity contraction **and** 4h traded
   perpetual relative weakness; decision at `T + 15m` with inputs stamped `<= T`; 2022-2024 only;
   gates for source reliability (`>= 95%`), common support (two years, overlapping `shock_z`
   and prior-volatility ranges) and a 12-month necessary detectability screen
   (`required_standardized_effect <= 0.50`).
4. Budget: exactly one support calculation (`scripts/audit_candidate_1_frozen_admission.py`);
   a deterministic rerun only to correct a demonstrated implementation defect. No grid, preview,
   alternate definition, new source or outcome inspection.
5. Dispositions are fixed in advance: all gates pass →
   `CANDIDATE_1_ADMITTED_FOR_PROTOCOL_DESIGN` (no market trial); any gate fails →
   `CANDIDATE_1_CLOSED_CURRENT_ALLOCATION_SUPPORT_OR_FEASIBILITY` and project state
   `STRONG_STOP_PENDING_ASTRA`, the economic hypothesis untested, and no Candidate #2 or
   successor designed.

There is exactly one operative Candidate #1 disposition, recorded in state
(`governance_transition_v3.candidate_1.disposition`) and by the admission-result ADR.
