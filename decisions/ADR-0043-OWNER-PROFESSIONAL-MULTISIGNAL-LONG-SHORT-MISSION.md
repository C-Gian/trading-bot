# ADR-0043 — Owner redefines Trading Bot as a professional multi-signal LONG/SHORT system

Status: OWNER-AUTHORIZED — 2026-09-25

## Decision

The Owner clarifies the intended Trading Bot product and research mission in:

`docs/canonical/OWNER_PRODUCT_MISSION_V2.md`

This is a material product/scope clarification and a legitimate reopening trigger under ADR-0042.

The prior narrow programme assumptions:

- BTC spot only as the effective action model;
- LONG / NO_TRADE only;
- one primary signal horizon;
- continuation only when a single narrowly specified candidate independently demonstrates large
  economic alpha;

do not fully represent the intended product.

The intended V1 is a local BTC web application with:

- live BTC chart and live professional-signal board;
- continuous candle-level direction / magnitude / confidence / risk prediction;
- selective `LONG / SHORT / NO_TRADE` paper decisions;
- multi-timeframe state, including explicit multi-timeframe cyclical analysis;
- visual fast-forward historical replay;
- separate per-candle prediction and trade annotations;
- realistic trade outcome storage;
- post-backtest hot-period event/news reporting;
- local cached historical data where feasible;
- established professional trading mechanisms and playbooks as the primary design vocabulary.

The system is evaluated as a coherent professional multi-signal decision process. Individual signals
may add conditional/contextual value without being required to carry standalone profitable alpha.

Prediction evaluation and trade evaluation remain separate. Low-conviction candle-level prediction
errors remain visible but must not be conflated with failure of selective high-conviction trading.

## Relationship to prior evidence

All prior results remain valid for their exact frozen formulations and remain part of search memory.

Candidate #1 remains `DEVELOPMENT_REJECTED`; it is not reopened.

ADR-0042's parked decision remains the correct terminal disposition for the **previous narrower
programme**. This Owner scope change triggers strategic reconsideration; it does not erase or relabel
the parked evidence.

## Governance

No new market experiment is authorized by this ADR.

Active alpha allocation remains zero until Astra reviews the new mission and issues a bounded
strategic programme.

Real money remains forbidden. No leverage or execution venue for SHORT is authorized here; V1 may
paper-simulate SHORT while the eventual live execution mechanism remains a later product/risk
decision.

Astra must next determine the finite research/functional architecture that best implements the Owner
mission while preserving anti-leakage, anti-overfitting and evidence-quality rules.
