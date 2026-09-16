# Trading Bot — Roadmap

Phases 0-3 describe the substrate, which is generation-independent and stands unchanged.

Phases 4-7 were written for the superseded cost-adjusted strategy-selection generation
`COST_EXPECTANCY_RESEARCH_GENERATION_V1`. They are preserved as the historical plan of that
generation and are not the current plan. The Owner-authorized prediction-first programme is
Phase P below; see [ADR-0026](../../decisions/ADR-0026-PREDICTION-FIRST-RESEARCH-OBJECTIVE.md),
[`PREDICTIVE_EVALUATION_CONTRACT_V1.md`](PREDICTIVE_EVALUATION_CONTRACT_V1.md) and
[`PREDICTIVE_SOURCE_ROADMAP_V1.md`](PREDICTIVE_SOURCE_ROADMAP_V1.md).

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

Primary objective of that generation:
robust net expectancy after costs. Superseded by the prediction-first objective; the
results it produced remain valid answers to the question it asked.

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

`ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1` is closed
`POWER_BLOCKED_INFERENCE_CALIBRATION_FAILED_NOT_EXECUTED`: not `REJECT`, not
`INCONCLUSIVE` market evidence, and not evidence that `beta <= 0`. No same-hypothesis
inference rescue is authorized.

The 3,380 to 3,378 signal difference between the frozen support artifact and the power
panel is reconciled exactly to one typed rule — `epoch_decision_rows < 504`, the
participation requirement of the retired position-shift placebo — which removed 35
epochs, of which one carried the two missing events. That rule's input is a whole-sample
epoch length, so `EVENT_RECONCILIATION_STATUS = FAIL_CLOSED_NON_POINT_IN_TIME_PARTICIPATION_RULE`.

One final ALIGNED development descendant, `ALIGNED_GATE_INTENSITY_COMMON_EFFECT_V1`, is
frozen: the unweighted integer score `int(direction) + int(breakout) + int(participation)`
over the unchanged gates, verified to satisfy `ALIGNED == (score == 3)` on 2,556,535 rows,
with one primary `beta_gate`, 8.0 bps/gate MESI, alpha `0.05/13`, target power `0.80`, and
a new calendar-synchronous whole-week randomization family of 1,024 unique vectors.

Because the reconciliation prerequisite failed closed, the randomization support gate and
the prospective power stages were not run. `GATE_INTENSITY_POWER_GATE_STATUS =
REDESIGN_REQUIRED` and therefore `ALIGNED_DEVELOPMENT_FAMILY_STATUS =
PARKED_DEVELOPMENT_SEARCH_EXHAUSTED`. The park is an inherited bookkeeping defect, not a
demonstrated power failure of the gate-intensity design, which remains frozen and
unmeasured for a Research Director who chooses to reopen it.

Next: `RESEARCH-DIRECTOR-REVIEW-ALIGNED-DEVELOPMENT-PARK`.

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

## Phase P — Prediction-first research generation

The current programme. Staged, and each stage gates the next.

- **P0 — Predictive foundation.** Deterministic 24h labels and the frozen evaluation
  implementation, then simple chronological baselines. Proves label causality and
  evaluation correctness before any model complexity. No external information family.
- **P1 — Internal-structure predictor.** First candidate predictors on internal price,
  volume and volatility structure, scored against the predeclared baselines with coverage,
  calibration, magnitude error and dependence-aware intervals.
- **P2 — Calibration and coverage policy.** Turn a raw score into a calibrated probability
  and a defensible abstention rule; establish the strength percentile reference.
- **P3 — Staged information families.** One preregistered incremental-information
  experiment per family, in the order and under the conditions of
  [`PREDICTIVE_SOURCE_ROADMAP_V1.md`](PREDICTIVE_SOURCE_ROADMAP_V1.md).
- **P4 — Prospective predictive evidence.** Forward-collected predictions scored by the
  same frozen contract. Prospective evidence outranks any historical holdout.
- **P5 — Economic layer.** Only once a predictor is credible: policy, costs, sizing and
  execution simulation, reported separately from prediction quality.

Sealed evaluation and the real-capital gate are unchanged and remain later, Owner-gated
steps. No stage may be skipped because an earlier one looked promising.
