# ADR-0018 — close P2 as methodology-blocked and allocate to cross-sectional feasibility

Status: ACCEPTED. Date: 2026-09-15. Checkpoint:
`P2-METHODOLOGY-BLOCK-CLOSURE + RESEARCH-ARCHITECTURE-SYNTHESIS-V2`.

## Context

`BTC_TIME_CYCLE_STRUCTURE_V1` was designed, power-gated and twice given a frozen null.
Null V1 failed its predeclared fidelity gate (ADR-0015). Null V2, an append-only
raw-return long-block redesign, failed its predeclared gap-topology support gate
(ADR-0016, ADR-0017). Neither failure exposed the actual cycle result, so P2 has never
been classified against market evidence and no further null is preregistered.

Separately, the accumulated evidence says the recurring blocker in this project is
information quantity rather than mechanism plausibility: P1A is power-blocked at
`power_at_MESI = 0.01424888` against a 24.0 bps/event MESI, and the supervised
internal/macro/funding/CFTC families produced no robust positive post-cost result — WP-017
being negative even at zero cost in its frozen specification.

## Decision

1. Record the Research Director disposition `METHODOLOGY_BLOCKED_NOT_EXECUTED` for
   `BTC_TIME_CYCLE_STRUCTURE_V1`. It is explicitly not `REJECT`, not `NOT_SUPPORTED`, not
   `INCONCLUSIVE_MARKET_EVIDENCE`, and not evidence against cyclic structure or against
   Ciclica Evoluta as a whole.
2. Disposition Null V1 as `FAILED_FIDELITY_REJECTED_FOR_INFERENCE` and Null V2 as
   `FAILED_BLOCK_SUPPORT_REJECTED_FOR_INFERENCE`. Both remain byte-identical.
3. Authorize no Null V3, and no alternate block length, period band, representation,
   GARCH/HAR/FIGARCH model, bootstrap or spectral estimator inside P2 V1. Park the cycle
   family as `PARKED_METHODOLOGY_BLOCKED`.
4. Record `RESEARCH_ARCHITECTURE_SYNTHESIS_V2` as the forward allocation:
   `CROSS_SECTIONAL_FEASIBILITY_AND_POWER_DESIGN` primary,
   `PROSPECTIVE_PAPER_EVIDENCE_CONTINUES` secondary parallel, BTC-only new source/model
   search `DEPRIORITIZED`.
5. Declare `CROSS-SECTION-FEASIBILITY-AND-POWER-DESIGN-V1` as the next checkpoint, which
   must complete before any aligned cross-sectional market outcome is inspected.

## Consequences

Accounting is untouched: 26 completed experiments, 12 known observed material economic
hypotheses, 15 adaptive decisions, 12 result-dependent forks, 0 sealed queries, Champion
`NONE`, real money false. Formally recording this review adds no adaptive decision.

Choosing the cross-sectional direction does not validate ALIGNED or BTC, does not make
the product multi-asset, does not turn N assets into N hypotheses, and does not permit
cherry-picking assets. The product universe remains `BTCUSDT_SPOT_V1_UNCHANGED` and
`cross_section_product_authorized` is false. No numeric universe threshold is frozen by
this decision; those require their own rationale and feasibility audit in the next
checkpoint. Paper strategy semantics are unchanged.

Reopening cycle research, new alternative data, a new ML architecture, new threshold
optimization, or another cycle-null method each requires a later explicit Research
Director allocation.
