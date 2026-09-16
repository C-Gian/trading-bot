# CURRENT TASK — PREDICTIVE-RESEARCH-REBASELINE-V1

Status: ACTIVE_GOVERNANCE_AND_ARCHITECTURE_REBASELINE

Starting HEAD: `01c629e81f4434034da60acc6a79c4be3cdbde19` on `main`.

Owner authorization: explicit. The Owner has changed the scientific/product objective from cost-adjusted strategy selection to a prediction-first BTCUSDT system. This is a material Owner-controlled change and is authorized by the Owner in chat on 2026-09-16.

A preservation branch already exists on GitHub:

`archive/cost-expectancy-v1` -> `01c629e81f4434034da60acc6a79c4be3cdbde19`

The archived branch preserves the complete pre-pivot cost/net-expectancy implementation. Do not rewrite or delete it.

This checkpoint is a rebaseline, not a market experiment. Do not inspect sealed post-cutoff BTC market data, do not run a result-bearing strategy experiment, and do not authorize real money.

## 1. New scientific mission

Update Owner-controlled governance, agent instructions, canonical product/research docs, and machine-readable state so the primary mission is:

Develop a statistically credible BTCUSDT predictor that estimates future price direction, calibrated probability, and expected movement magnitude over explicitly declared horizons.

The prediction layer must be scientifically evaluated independently of capital size, exchange fees, leverage, slippage, blockchain/network costs, or any other execution/economic choice.

Economic execution remains a downstream layer. It may later translate a prediction into a paper/live decision using costs and capital assumptions, but it must not define whether the underlying market prediction was correct.

Real money remains forbidden without a future explicit Owner gate.

## 2. Preserve scientific rigor

Do NOT weaken the existing anti-leakage, anti-overfitting, preregistration, chronological evaluation, sealed-data, multiplicity, audit, and provenance principles.

Rewrite only rules that conflict with the Owner-authorized prediction-first objective.

In particular, replace the old rule that hit rate is secondary to net expectancy.

New principle:

- directional win rate / hit rate is a primary human-facing predictive metric;
- it must never be interpreted alone;
- every reported win rate must be paired with sample size and prediction coverage;
- probabilistic predictions must be evaluated for calibration;
- magnitude forecasts must be evaluated separately;
- all metrics must be compared against simple chronological baselines and uncertainty intervals;
- no high win rate obtained by trivial abstention, class imbalance, or selective reporting may be treated as predictive success.

Transaction costs and execution assumptions remain mandatory only for experiments that claim economic/trading profitability. They are not part of the primary scoring of pure prediction experiments.

## 3. Frozen initial predictive target

For the first predictive research generation, retain the product universe:

- BTCUSDT spot market data;
- canonical 1m source data;
- 1h forecast decision cadence;
- primary forecast horizon: 24h terminal return;
- no real money.

Prediction target at decision time t:

`r_24h = log(close[t+24h] / close[t])`

Direction truth:

- UP when `r_24h > 0`;
- DOWN when `r_24h < 0`;
- exact zero may be treated as NEUTRAL/undefined for directional scoring and must be counted explicitly.

The predictor may estimate both UP and DOWN even though the V1 trade-action layer remains LONG / NO_TRADE for spot. Prediction and trade action are separate concepts.

Do not add leverage or short execution to V1 in this checkpoint.

## 4. Product meaning of probability and strength

Define canonical prediction fields for future implementation:

- `direction`: UP | DOWN | NEUTRAL/UNCERTAIN;
- `probability`: calibrated probability that the declared direction is correct at the primary horizon;
- `expected_return_pct`: predicted signed 24h terminal percentage return;
- `expected_move_quote`: UI-only conversion of expected return to approximate BTCUSDT quote-currency movement at the decision price;
- `strength`: a 0-100 magnitude scale, not a probability.

For V1, define `strength` as the percentile rank of the predicted absolute 24h move relative to the training-only distribution of absolute 24h moves available at model-fit time. This makes probability and strength orthogonal: e.g. 90% probability with 30% strength means high confidence in direction but a relatively modest expected move.

The UI must never present uncalibrated model scores as probabilities.

## 5. Predictive evaluation contract

Create a canonical design document for predictive evaluation. Freeze at least these metrics before the first new predictive result is inspected:

Primary human-facing metric:

- actionable directional win rate = correct directional predictions / actionable directional predictions.

Mandatory companion metrics:

- prediction coverage = actionable directional predictions / eligible decision timestamps;
- sample size and chronological distribution;
- calibration: Brier score plus reliability/calibration table or curve;
- magnitude error: MAE of signed 24h return prediction, reported in percentage points/bps;
- directional baseline comparison;
- uncertainty interval for directional win rate;
- performance by major chronological folds/regimes, without post-result threshold rescue.

Required naive baselines must include at minimum:

- empirical training-set UP base-rate predictor;
- always-UP directional baseline;
- previous-24h-sign persistence baseline;
- zero-return magnitude baseline.

A model is not scientifically interesting merely because win rate exceeds 50%. It must beat relevant predeclared baselines with credible out-of-sample evidence and nontrivial coverage.

Do not set an arbitrary target such as 70%, 80%, or 90% win rate before evidence supports feasibility.

## 6. User-facing magnitude-quality concept

Preserve the Owner's desired intuition as a transparent secondary diagnostic, but do not make it the sole scientific metric.

Design a bounded signed magnitude-match diagnostic where:

- exact predicted and realized magnitude in the correct direction is 100%;
- same direction but ten-times under/over prediction is approximately 10%;
- wrong direction carries a negative sign;
- the score is symmetric for over- and under-prediction;
- zero/near-zero denominators have an explicit deterministic rule.

Document the formula before using it on real results. Keep MAE as the standard magnitude metric alongside it.

## 7. Economic layer separation

Create a canonical architecture boundary:

PREDICTION LAYER -> DECISION/POLICY LAYER -> ECONOMIC/EXECUTION SIMULATION

Prediction quality must not depend on:

- whether future capital is EUR 5,000 or another amount;
- exchange fee schedule;
- leverage;
- slippage;
- blockchain/network costs;
- position sizing.

Those variables belong only to downstream scenario analysis and paper/live execution.

Record EUR 5,000, if retained at all, as a configurable future scenario/display assumption, never as a training target or prediction-quality parameter.

## 8. Research source roadmap

Create a canonical staged source-family roadmap. The long-run predictor may study causally timestamped information families including:

- internal price/return structure;
- volume/liquidity/volatility;
- technical patterns and market microstructure;
- derivatives/funding/open-interest/positioning where point-in-time valid;
- cross-asset context;
- macroeconomic data with publication/vintage controls;
- calendar/cycle structure;
- public news and event information;
- policy/political/geopolitical events as timestamped public information, without partisan interpretation;
- public attention/sentiment where provenance is valid;
- on-chain information where publication/availability semantics are defensible.

Do not ingest all families at once. Each family must enter through a preregistered incremental-information experiment with point-in-time availability rules and search-budget accounting.

Narrative plausibility alone is never evidence.

## 9. Historical work disposition

Preserve all existing experiments and negative results. Do not delete or rewrite them.

Record the prior research program as a completed/legacy research generation:

`COST_EXPECTANCY_RESEARCH_GENERATION_V1`

Disposition:

`SUPERSEDED_BY_OWNER_PREDICTION_FIRST_OBJECTIVE`

ALIGNED remains a historical/paper baseline, not Champion and not the new main research target.

Do not change its historical results.

## 10. Prospective ALIGNED observer

The old automated prospective observer measures the superseded ALIGNED strategy objective and must not continue automatically on the new `main`.

Before changing lifecycle code:

- inspect whether any genuine prospective observations were created after the last Research Director review;
- preserve all genuine evidence exactly;
- never backfill or rewrite missed boundaries;
- record the exact final observer/evidence counts and final disposition.

Then disable automatic ALIGNED prospective collection on `main` cleanly and explicitly. Do not delete the implementation; the archive branch already preserves the full old version and the code may remain as legacy infrastructure where sensible.

Use a disposition such as:

`SUSPENDED_BY_OWNER_OBJECTIVE_PIVOT`

Do not pretend zero observations if observations actually exist.

## 11. V1 product direction

Update canonical product intent, not necessarily the full frontend in this checkpoint.

New intended Analyze Market output:

- BTCUSDT forecast horizon;
- predicted direction;
- calibrated probability;
- strength 0-100;
- expected move in % and approximate quote-currency units;
- uncertainty/context explanation;
- separate action: LONG or NO_TRADE for paper-only V1;
- later trade economics shown separately from prediction quality.

Do not claim certainty. Probability must remain empirically calibrated.

## 12. Governance/state artifacts

At minimum update/create:

- `governance/SCIENTIFIC_CONSTITUTION.md` — Owner-authorized Version 2.0 prediction-first mission;
- `AGENTS.md` — new mission and scientific objective;
- `state/current_state.json` — one machine-readable current predictive objective and legacy disposition;
- `decisions/ADR-0026-PREDICTION-FIRST-RESEARCH-OBJECTIVE.md`;
- `decisions/INDEX.md`;
- a canonical predictive evaluation/design document under `docs/canonical/`;
- a canonical predictive source roadmap under `docs/canonical/`;
- one concise checkpoint report under `reports/checkpoints/`;
- `tasks/CURRENT_TASK.md` at completion, pointing to the next bounded implementation/research checkpoint.

Do not duplicate independently editable current state across documents.

## 13. Next checkpoint design

This checkpoint must NOT train the new predictor.

At completion, the next active work package should be a bounded `PREDICTIVE-BASELINES-V1` foundation that implements deterministic labels/evaluation and simple chronological baselines before any complex model or external information family.

The first predictive implementation should prove label causality and evaluation correctness before model complexity.

## 14. Validation

Run full deterministic repository validation appropriate to changed files.

Requirements:

- backend tests PASS;
- frontend validation PASS if touched;
- `check.py --no-data` PASS;
- ruff/mypy/format PASS;
- no sealed queries;
- no result-bearing new predictive experiment;
- Champion remains NONE;
- real money false;
- working tree clean;
- commit and push to `main`;
- exact-head CI SUCCESS.

## Final report

Return only:

`PREDICTIVE RESEARCH REBASELINE: PASS|PARTIAL|FAIL`

Then concise fields:

- Starting HEAD
- Ending HEAD
- Archive branch verified
- Constitution version
- New primary objective
- Primary horizon
- Direction target
- Probability definition
- Strength definition
- Primary win-rate metric
- Mandatory companion metrics
- Economic layer separation
- Legacy research disposition
- ALIGNED observer final evidence counts/disposition
- Sealed queries
- Champion
- Real money
- Validation
- Exact-head CI
- Next action
