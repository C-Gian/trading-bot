# ADR-0038 — Candidate #1 passes the frozen admission and is admitted for protocol design

Status: RECORDED (frozen rule applied mechanically, 2026-09-25; Research Director review of the
record pending)

## Evidence

The single calculation of `research/protocols/CANDIDATE-1-FROZEN-ADMISSION-V1.md`
([ADR-0037](ADR-0037-CANDIDATE-1-ASTRA-ADJUDICATION-AND-FROZEN-ADMISSION-SPEC.md)), frozen and
committed (`998f24c`) before it ran: `reports/validation/CANDIDATE-1-FROZEN-ADMISSION-V1.json`,
deterministic replay PASS. No forward return, trade outcome, label, model or post-cutoff data;
sealed queries 0; support calculations 1 of 1.

| Quantity | Value |
|---|---|
| Intended sell-off episodes (2022-2024) | 336 |
| Valid synchronized episodes | 335 (coverage 0.997; 1 excluded, `OI_NON_POSITIVE`) |
| Candidate / control | 116 / 219 |
| By year (candidate / control) | 2022 41 / 80, 2023 40 / 54, 2024 35 / 85 |
| Common support | years 2022-2024; `shock_z` overlap [-6.80, -2.00]; prior-vol overlap [0.00166, 0.01279] |
| Conservative 12-month candidate arrivals | 35 (minimum annual count) |
| Required standardized matched effect | 0.4203 (<= 0.50) |

Gates: `AVAILABILITY_ASSUMPTION`, `SOURCE_RELIABILITY`, `COMMON_SUPPORT`, `DETECTABILITY_12M` —
all pass.

## Decision

`CANDIDATE_1_ADMITTED_FOR_PROTOCOL_DESIGN`. This is the single operative Candidate #1
disposition. The preserved executor diagnostic (73 / 25) remains
`EXPOSED_SUPPORT_DIAGNOSTIC — DIRECTOR_UNAPPROVED_SPECIFICATION` and plays no role here.

Admission is not evidence about Candidate #1's economics: the economic hypothesis remains
untested. The detectability screen is a necessary condition under an optimistic
independent-episode approximation; it is not a MESI, an expected effect or a promotion signal.

## Consequences

- Next: a Research-Director protocol-design checkpoint (Development Lab freeze per
  `docs/canonical/RESEARCH_STAGE_POLICY_V1.md` §1). No market trial, backtest or outcome
  inspection is authorized by this decision.
- Admission counts and descriptors are now exposed support information; the protocol may not
  re-define the event, state or population to chase them.
- Candidate Card #2 remains unallocated. Champion NONE; sealed queries 0; real money false.
