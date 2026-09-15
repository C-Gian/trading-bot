# Trading Bot — Roadmap

## Phase 0 — Scientific + engineering foundation

Create:
- governance;
- experiment lifecycle;
- preregistration contract;
- project state;
- data contract;
- evaluation stages;
- anti-overfitting controls;
- backend/frontend skeleton;
- deterministic validation;
- one-command local developer bootstrap where practical.

No market-data backfill.
No strategy search.

## Phase 1 — Data foundation

Build and validate:
- BTCUSDT canonical 1m history;
- immutable raw source archive;
- normalized Parquet;
- gap/integrity reports;
- deterministic 1h and 4h aggregation;
- dataset manifests and hashes;
- API endpoint for read-only market data;
- Market page fed from real canonical data.

## Phase 2 — Credible backtest substrate

Implement:
- fees;
- spread/slippage assumptions;
- next-bar execution;
- 1m intrabar resolution;
- ambiguous TP/SL policy;
- deterministic reproducibility;
- Freqtrade integration or equivalent validated substrate;
- web views for backtest/evidence inspection.

## Phase 3 — Baselines and negative controls

Before complex strategy research:
- Buy & Hold reference;
- random-entry control;
- simple trend;
- simple breakout;
- shifted-signal / future-feature leak controls.

Goal: prove the laboratory can distinguish credible implementation behavior from nonsense.

## Phase 4 — Strategy research

Prospectively research:
- trend;
- breakout;
- momentum;
- volatility/regime;
- volume;
- combinations after component ablations.

Primary objective:
robust net expectancy after costs.

## Phase 5 — Locked evaluation

Introduce:
- sealed holdout;
- limited query budget;
- coarse evaluator feedback;
- red-team promotion gates;
- independent finalist validation.

## Phase 6 — Local Paper Advisor V1

Complete the intended local product:

```text
open Trading Bot
→ Analyze Market
→ sync latest data
→ approved strategy evaluation
→ NO_TRADE
   or
→ LONG BTCUSDT
   signal timestamp
   entry
   stop loss
   take profit / exit
   expiry
   strategy version
→ record paper outcome
```

Dashboard, chart, trade history and statistics become Owner-ready.

Still no real money.

## Phase 7 — Long-running prospective evidence

Run the approved strategy prospectively for months.

Never rewrite historical paper signals.

## Phase 8 — Always-on Server V2

Move:
- collection;
- signal generation;
- paper trading;
- scheduler;
- web dashboard;
- notifications

to an always-on server.

Notify the Owner only for approved signals.

## Phase 9 — Research extensions

Only after the BTC pipeline is credible:
- ETH and other assets;
- cross-asset robustness;
- ML challengers;
- perpetual / SHORT research;
- microstructure / alternative data.

## Phase 10 — Possible real-capital gate

Only after sufficiently strong future evidence.

Requires explicit Owner decision.

## Governed next research sequence after P0

The previous default loop of acquiring a new source, testing a candidate, and moving to
another source is stopped. Future work separates statistical credibility, signal
information, economic monetization/execution, and product validation.

P1A design and prospective power analysis are complete. Its frozen 24.0 bps/event MESI
is not statistically resolvable with the available clustered BTC evidence: empirical MDE
285.640052 bps/event and power 0.01424888. Research Director disposition is
`POWER_BLOCKED_NOT_EXECUTED`, not market `REJECT` or `INCONCLUSIVE`. The true zero-shift
120h ALIGNED outcome remains unavailable. No P1A rescue, tuning, alternate horizon,
cross-section, or execution is authorized.

P2 was one structural time-only hypothesis, `BTC_TIME_CYCLE_STRUCTURE_V1`, on a 4h context
series derived from canonical BTCUSDT 1m development data. Its protocol froze one primary,
at most two non-rescuing diagnostics, a colored/dependent-noise null, synthetic cycle
injection, multiple-frequency correction, chronological outer evaluation, and a target
power of 0.80 before any actual cycle result could be exposed. It created no trading rule
and consumed no material economic hypothesis.

P2 is closed as `METHODOLOGY_BLOCKED_NOT_EXECUTED`. The frozen inference design could not
produce a scientifically acceptable dependence-preserving null without violating its own
preregistered safeguards: Null V1 is `FAILED_FIDELITY_REJECTED_FOR_INFERENCE` and Null V2
is `FAILED_BLOCK_SUPPORT_REJECTED_FOR_INFERENCE`. The actual BTC cycle primary result was
never observed, so this is not `REJECT`, not `NOT_SUPPORTED`, not
`INCONCLUSIVE_MARKET_EVIDENCE`, and not evidence against cyclic structure. No Null V3 is
authorized, and no alternate block length, period band, representation,
GARCH/HAR/FIGARCH model, bootstrap or spectral estimator may be tried inside P2 V1. The
cycle family is `PARKED_METHODOLOGY_BLOCKED`.

`RESEARCH_ARCHITECTURE_SYNTHESIS_V2`
(`research/design/RESEARCH_ARCHITECTURE_SYNTHESIS_V2.md`) records the resulting
allocation. Primary next research direction:
`CROSS_SECTIONAL_FEASIBILITY_AND_POWER_DESIGN`. Secondary parallel direction:
`PROSPECTIVE_PAPER_EVIDENCE_CONTINUES`. BTC-only new source/model search is
`DEPRIORITIZED`. New alternative data, a new ML architecture, new threshold optimization
and another cycle-null method stay closed without a later explicit Research Director
allocation.

Next: `CROSS-SECTION-FEASIBILITY-AND-POWER-DESIGN-V1`.

### Future cross-sectional replication

“ALIGNED has edge on BTC” and “an ALIGNED-like mechanism has a common positive effect
across crypto” are different economic hypotheses. Additional assets are not independent
BTC observations. Cross-sectional work is now the primary research direction, as a
scientific generalization and power investigation only.

`CROSS-SECTION-FEASIBILITY-AND-POWER-DESIGN-V1` is complete. It froze point-in-time
universe construction, listing/delisting handling, survivorship controls, liquidity
eligibility, per-asset data requirements, the frozen ALIGNED transfer, the pooled primary
endpoint, cross-asset/time dependence treatment, the matched non-zero placebo, the
economic threshold, the power gate and the prohibition on per-asset winner selection —
all committed in `cb13309` before any cross-sectional signal was generated.

Its result is `CROSS_SECTION_POWER_GATE_STATUS = REDESIGN_REQUIRED` on two independent
grounds. The non-zero timing placebo invalidates the frozen two-way asset/UTC-week
clustered inference: empirical size 3.55% against a nominal 0.05/13, a 9.2x inflation
with exact binomial p = 1.26e-8. And the design cannot resolve its own threshold: power
at the frozen 24.0 bps/event MESI is 0.2117 against a 0.80 target, with an MDE of
44.87 bps/event.

Neither failure is evidence about crypto markets. The true pooled beta, its t statistic,
its p value and every per-asset effect remain uncomputed. The product universe remains
`BTCUSDT_SPOT_V1_UNCHANGED`, the cross-sectional product is not authorized, no
cross-sectional market outcome has been observed, and no asset was cherry-picked. No
MESI, power target, universe threshold, liquidity cutoff, horizon or ALIGNED parameter
may be changed by an executor in response; the next move belongs to the Research
Director.

Next: `RESEARCH-DIRECTOR-REVIEW-CROSS-SECTION-POWER-BLOCK`.

### Cycle research boundary

`docs/canonical/CYCLE_RESEARCH_SOURCE_BOUNDARY_V1.md` distinguishes public concepts from
project-reconstructed rules and executable detail that remains unspecified. A spectral
null falsifies only the frozen timing representation tested, not every idea within
“Ciclica Evoluta.” P2 opened time structure only and is now closed
`METHODOLOGY_BLOCKED_NOT_EXECUTED`; swing, volume, inverse, vincolo, raccordo, target,
and cycle-based trading were never opened and remain closed. Diagnostics cannot rescue a
failed primary. A diagnostic-inspired successor requires a new prospective hypothesis
and search budget; any trading rule is a new `MATERIAL_ECONOMIC_HYPOTHESIS` with its own
MESI and power gate.

### Future runtime engineering

`RESEARCH_RUNTIME_V3_PERFORMANCE` is a future engineering checkpoint. WP017 timing shows
the wall-time bottleneck in `BUILD_FEATURES`, `RECONCILIATION`, and `PROFILES`, while
`FIT` and `PREDICT` were already fast under Runtime V2. V3 may investigate vectorized
feature construction, immutable hash-bound intermediate caching, deterministic reuse,
faster independent reconciliation, and removal of duplicate safe computations.
`RESEARCH_RUNTIME_V2_BATCH` remains immutable for experiments already bound to it. V3
must demonstrate numerical and scientific equivalence before any future candidate uses
it. Runtime V3 is not implemented in P0.
