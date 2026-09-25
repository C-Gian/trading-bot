# Candidate Card #1 — Positioning-conditioned recovery after a sharp BTC spot sell-off

Allocated under [ADR-0036](../../decisions/ADR-0036-OWNER-PRACTICAL-ECONOMIC-OBJECTIVE-AND-CONSTITUTION-V3.md)
(strategic authority: Astra directive V2). This is the only Candidate Card allocated; Candidate
Card #2 is not allocated.

The operative disposition lives in `state/current_state.json`
(`governance_transition_v3.candidate_1.disposition`) and in the admission-result decision
record; this card does not duplicate it.

## Scientific question

> Among comparable sharp BTC sell-offs, does simultaneous contraction in leveraged positioning
> and deterioration in perpetual-relative pricing identify temporarily pressured episodes with
> a materially better subsequent long outcome?

Observational predictive/economic hypothesis. Falling OI does not prove forced liquidation;
a perpetual discount does not prove mispricing. The legitimate distinct mechanism is the
conditional economic response of a jointly defined positioning state among comparable price
sell-offs. It must not be an old pullback rule plus another gate, old aggressive-flow logic
renamed deleveraging, marginal OI/funding prediction with a new label, or an exposed old
fixed-barrier target under another model.

## Lineage (adjudicated; not repeated)

The historical evidence-salvage audit classified the candidate
**`DISTINCT_BUT_HEAVILY_PRIOR_CONSTRAINED`**. Historical parents:

- pullback / sell-off recovery: `PULLBACK_RECOVERY_V1` (EXP-ALG-010, EXP-ALG-011) — closed;
- OI quantity as a predictor: EXP-PRED-005/006 — `REJECTED_DEVELOPMENT_NO_SEALED`, contract
  `PREDICTIVE_OPEN_INTEREST_STRUCTURE_V1`;
- settled funding: EXP-PRED-003/004, `FAM-DERIVATIVES-SENTIMENT-CONTEXT` (WP-015);
- regulated-futures positioning: `FAM-CFTC-REGULATED-FUTURES-POSITIONING` (WP-017);
- aggressive order flow: `FAM-ORDER-FLOW` (WP-007) and `FAM-PUBLIC-TAKER-FLOW-PROBABILITY`
  (EXP-PRED-V2-005; EXP-PRED-V2-006 power-blocked), whose controls already contained the 1h
  spot-minus-perpetual return.

Programme descriptors: allocation posture `LATE_STAGE_WITHIN_CURRENT_ENVELOPE` /
`RESEARCH_WARNING`; scientific coverage
`MATURE_NEGATIVE_PREDICTOR_RESEARCH_WITH_LIMITED_PLAYBOOK_COVERAGE`.

## Admission history

1. **Executor support diagnostic** —
   `EXPOSED_SUPPORT_DIAGNOSTIC — DIRECTOR_UNAPPROVED_SPECIFICATION`, preserved in
   `evidence/CANDIDATE-1-EXECUTOR-SUPPORT-DIAGNOSTIC-V1/` (24h `<= -5%`, 72h separation,
   joint 24h state, 30-per-arm floor; 73 events / 25 joint-state). Non-authoritative per Astra
   (`PRIOR_SUPPORT_DIAGNOSTIC_NONAUTHORITATIVE — ONE_DIRECTOR_FROZEN_ADMISSION_ALLOWED`).
2. **Director-frozen admission** —
   `research/protocols/CANDIDATE-1-FROZEN-ADMISSION-V1.md`
   ([ADR-0037](../../decisions/ADR-0037-CANDIDATE-1-ASTRA-ADJUDICATION-AND-FROZEN-ADMISSION-SPEC.md)),
   exactly one calculation by `scripts/audit_candidate_1_frozen_admission.py`, record
   `reports/validation/CANDIDATE-1-FROZEN-ADMISSION-V1.json`.

No forward return, trade outcome, label or model has been computed for this candidate.
