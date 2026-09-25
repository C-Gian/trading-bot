# ADR-0039 — Freeze Candidate #1 Development Lab protocol

Status: ACCEPTED — Research Director, 2026-09-25

## Context

ADR-0038 admitted Candidate #1 for protocol design after the single Director-frozen source/support
admission passed every gate. The economic hypothesis remains untested.

Strategic authority remains `ASTRA_TRADING_BOT_STRATEGIC_OPERATING_DIRECTIVE_V2`. Constitution
3.0 and `RESEARCH_STAGE_POLICY_V1` delegate ordinary pre-result protocol choices inside the admitted
allocation to the Research Director.

No Candidate #1 forward return, trade payoff, model result or economic outcome was inspected before
this decision.

## Decision

Freeze:

`research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md`

as the sole Development Lab protocol for the current allocation.

The frozen design uses:

- the already-admitted prior-risk-normalized sharp-sell-off population;
- the already-admitted joint OI-contraction + traded-perpetual-relative-weakness state;
- LONG / NO_TRADE only;
- a deterministic ~4h timed LONG with no stop/target search;
- the existing 24 bp conservative development cost convention;
- a price-only sell-off control matched outcome-blind within year on shock severity and prior
  volatility;
- primary absolute net expectancy and incremental matched net-return advantage;
- predeclared economic, risk, stability, cost/delay robustness and prospective-detectability gates;
- exactly one primary, one control, one higher-cost stress and one longer-delay stress;
- no model search, horizon search, parameter rescue, source expansion or Candidate #2.

The economic materiality floors are frozen at:

- absolute Candidate net expectancy: +25 bp/trade;
- incremental Candidate-minus-control advantage: +20 bp/matched pair;
- conservative annual simple fixed-notional contribution: >=500 bp;
- prospective confirmation feasibility must support both economic MESIs with family-wise alpha 0.05,
  target power 0.80 and <=12 months.

These thresholds express the late-stage programme's requirement for a materially useful effect rather
than a merely positive exposed-history result. They are not chosen from Candidate #1 outcomes or an
observed attainable MDE.

## Staging decision

This ADR does **not** authorize outcome inspection.

The next executor package is implementation-only:

1. implement the frozen protocol;
2. add deterministic/synthetic tests;
3. perform only outcome-free validation;
4. stop at `IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_AUTHORIZATION`.

A later explicit task is required for the one permitted Development execution.

## Consequences

- The protocol's event/state/population, holding semantics, control, matching, costs, stresses,
  materiality thresholds and inference may not change after implementation sees real outcomes.
- A demonstrated implementation defect may be corrected only to conform to this frozen protocol.
- `PROMOTION_ELIGIBLE` is the only result that can advance to prospective confirmation.
- Every other valid terminal disposition closes Candidate #1 and moves the project to
  `STRONG_STOP_PENDING_ASTRA`.
- Candidate #2 remains unallocated.
- Champion NONE; sealed queries 0; real money false.
