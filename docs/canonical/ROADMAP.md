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

Next: `DESIGN_ALIGNED_SIGNAL_PERSISTENCE_V1`.

P1A is a design question: **does an ALIGNED signal contain directional information that
persists beyond the current 24-hour horizon?** It is not a stop/target rescue. Before any
execution, P1A must:

- use frozen ALIGNED raw signal timestamps;
- separate informational events from one-position-at-a-time execution;
- freeze an externally motivated primary horizon (120h is the current research
  direction, not a preregistered choice);
- measure raw event returns in price basis points rather than R;
- use a matched/random timing control with the same horizon to distinguish signal from
  market beta;
- preregister a dependence method suited to irregular, overlapping or clustered events;
- translate `ECONOMIC_SIGNIFICANCE_POLICY_V1` into the event metric before execution;
- calculate MDE and power before execution;
- treat low-resolution evidence as low resolution, not proof of no effect.

Only if P1A supports persistent information may a distinct P1B be designed. P1B asks
whether that information can be monetized under realistic execution, occupancy,
turnover, costs, and risk. P1B is outside P0.

### Future cross-sectional replication

“ALIGNED has edge on BTC” and “an ALIGNED-like mechanism has a common positive effect
across crypto” are different economic hypotheses. Additional assets are not independent
BTC observations. Any authorized replication must freeze a point-in-time asset universe,
inclusion/exclusion rules, delisting and survivorship treatment, per-asset realistic
costs, a pooled primary endpoint, time/asset dependence treatment, and a prohibition on
selecting winners after observation. Cross-sectional research is not currently
authorized; the product remains BTCUSDT spot V1.

### Future cyclical research

A spectral null falsifies only the frozen periodicity hypothesis tested, not every idea
within “Ciclica Evoluta.” Before any cyclic outcome is observed, freeze one material
primary cycle hypothesis plus a finite number of preregistered diagnostics/ablations.
Diagnostics cannot rescue a failed primary. A diagnostic-inspired successor is a new
material hypothesis and consumes new search budget. Open-ended time, swing, volume,
inverse, constraint, raccordo, or similar searches after observation are forbidden.

### Future runtime engineering

`RESEARCH_RUNTIME_V3_PERFORMANCE` is a future engineering checkpoint. WP017 timing shows
the wall-time bottleneck in `BUILD_FEATURES`, `RECONCILIATION`, and `PROFILES`, while
`FIT` and `PREDICT` were already fast under Runtime V2. V3 may investigate vectorized
feature construction, immutable hash-bound intermediate caching, deterministic reuse,
faster independent reconciliation, and removal of duplicate safe computations.
`RESEARCH_RUNTIME_V2_BATCH` remains immutable for experiments already bound to it. V3
must demonstrate numerical and scientific equivalence before any future candidate uses
it. Runtime V3 is not implemented in P0.
