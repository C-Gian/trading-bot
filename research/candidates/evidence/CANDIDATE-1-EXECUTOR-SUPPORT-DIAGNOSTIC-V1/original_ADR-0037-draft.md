# ADR-0037 — Candidate #1 is source- and timing-feasible but support-blocked; closed without replacement

Status: EXECUTOR_RECORDED_PENDING_RESEARCH_DIRECTOR_REVIEW (2026-09-25)

## Context

[ADR-0036](ADR-0036-OWNER-PRACTICAL-ECONOMIC-OBJECTIVE-AND-CONSTITUTION-V3.md) allocated
exactly one Candidate Card: positioning-conditioned recovery after a sharp BTC spot sell-off,
lineage-adjudicated `DISTINCT_BUT_HEAVILY_PRIOR_CONSTRAINED`, admission only. The remaining
question was source / timing / support feasibility, decided without inspecting any market
outcome.

## Evidence

`reports/validation/CANDIDATE-1-SOURCE-SUPPORT-ADMISSION-V1.json`, deterministic and replayed
by `scripts/audit_candidate_1_admission.py --check`; summary in
`research/candidates/CANDIDATE-CARD-1-POSITIONING-CONDITIONED-SELL-OFF-RECOVERY.md`.
No forward return, label, outcome or model was computed; no post-cutoff data; sealed queries 0.

- Sources: verified traded spot and USD-M perpetual 1m klines (2020-01..2024-12) and USD-M OI
  5m quantity (2020-09..2024-12). Admissible window 2022-2024 (carried-forward OI restriction).
- OI integrity: quantity-only, strict grid; 448 exact-zero quantities treated as unavailable;
  as-of availability >= 0.9957 in 2022-2024; no material discontinuity; complete inputs at
  every declustered sell-off.
- Timing: conservative OI rule `create_time <= T - 5m`, age <= 15m is defensible and costless.
- Relative price: traded perpetual versus traded spot 1m close log ratio, same completed minute.
- Support (reference: 24h spot log return <= -0.05, 72h declustering): 73 admissible events,
  25 in the joint positioning state, 48 in the complement. The rule declared before the audit
  ran requires >= 30 per arm: **FAIL**.
- Outcome-free detectability context: ~8.3 joint-state events per year implies a 12-month
  one-sided MDE of about 0.86 per-event standard deviations.

## Decision

`CANDIDATE_1_REJECTED_OR_BLOCKED`, specifically blocked on support before protocol design.
It is not an outcome rejection: the candidate's economics are unknown. The candidate is closed
and no replacement candidate is designed. The broad allocation area "temporary inventory /
positioning-pressure mean reversion" keeps its disposition; opening any new candidate requires
Astra (Candidate Card #2 is not allocated).

Forbidden as rescue: changing the support floor, reference threshold, declustering window,
joint-state definition, OI timing rule or admissible years after this record, or re-admitting
the question under another name. Reopening requires Astra.

## Caveat for review

The diagnostic support definitions and the >= 30-per-arm floor were chosen by the executor and
fixed in code before the audit ran; they are not Research Director or Astra frozen rules. The
detectability arithmetic above does not depend on that floor.

## Consequence

Strategic reallocation is required before any new market research. Champion `NONE`, sealed
queries 0, real money false.
