# ADR-0026 — Prediction-first research objective

Status: ACCEPTED (Owner-authorized, 2026-09-16)

Material Owner-controlled change of scientific and product objective. It supersedes the
mission of [ADR-0001](ADR-0001-HISTORICAL-DEVELOPMENT-BOUNDARY.md)'s research programme as
carried forward through [ADR-0024](ADR-0024-PROSPECTIVE-COLLECTION-ARM-AND-OPERATING-POLICY.md),
and suspends the prospective observer armed by that ADR. No prior scientific result is
altered, reinterpreted or deleted.

## Context

The repository has, until now, searched for a cost-adjusted, economically positive trading
strategy. That programme ran to exhaustion within its own terms: 26 completed experiments,
12 observed material economic hypotheses, zero sealed queries, Champion `NONE`. Every
candidate family terminated in `REJECT`, `REJECT_COST_DOMINATED`, methodology-blocked or
power-blocked. ALIGNED development parked `PARKED_DEVELOPMENT_SEARCH_EXHAUSTED`, and the
only remaining direction was slow prospective shadow observation of an already-parked
strategy.

The Owner has changed the objective. The question is no longer "which strategy survives
costs" but "can BTCUSDT price movement be predicted at all, and how well". Those are
different questions, and conflating them was expensive: a prediction that was directionally
right could be scored as a failure because a fee schedule ate it, and the scientific record
could not distinguish "the market is unpredictable at this horizon" from "this execution
policy is uneconomic".

Both are worth knowing. Only one of them is a claim about the market.

## Decision

The primary mission becomes: develop a statistically credible BTCUSDT predictor that
estimates future price direction, calibrated probability, and expected movement magnitude
over explicitly declared horizons.

1. **Constitution Version 2.0.** The Owner-controlled Constitution is reissued
   prediction-first. Version 1.0 is preserved verbatim in its Appendix A. Every
   anti-leakage, anti-overfitting, preregistration, chronological-evaluation, sealed-data,
   multiplicity, audit and provenance rule is carried forward unweakened.

2. **Hit rate is promoted, not excused.** Version 1.0's rule that "hit rate is secondary to
   robust net expectancy" is replaced. Directional win rate becomes a primary human-facing
   predictive metric — and is never interpretable alone. Every win rate must be paired with
   sample size and coverage; probabilities must be calibrated; magnitude must be scored
   separately; everything must beat predeclared chronological baselines with a
   dependence-aware uncertainty interval. A win rate bought by abstaining on all but a few
   timestamps is not a result.

3. **Costs leave the primary score.** Transaction costs and execution assumptions remain
   mandatory and versioned for any claim of economic or trading profitability. They are no
   longer part of the primary scoring of a pure prediction experiment.

4. **Frozen initial target.** BTCUSDT spot, canonical 1m source data, 1h decision cadence,
   primary horizon 24h terminal return, `r_24h = log(close[t+24h] / close[t])`. `UP` when
   positive, `DOWN` when negative, exact zero `NEUTRAL` and counted explicitly. The
   predictor may estimate both directions even though the V1 action layer remains
   `LONG` / `NO_TRADE`; no leverage and no short execution enter V1.

5. **Probability and strength are orthogonal.** `probability` is the calibrated probability
   that the declared direction is correct at the primary horizon. `strength` is the
   percentile rank of the predicted absolute 24h move within the training-only distribution
   of absolute 24h moves at model-fit time, on a 0–100 scale. Strength is never a
   probability, and an uncalibrated model score is never displayed as one.

6. **Layer separation is architectural.**
   `PREDICTION -> DECISION/POLICY -> ECONOMIC/EXECUTION SIMULATION`. Prediction quality
   must not depend on capital size, fee schedule, leverage, slippage, network costs or
   position sizing. `EUR 5,000` survives only as a configurable display/scenario assumption
   in the economic layer.

7. **Canonical contracts.** `docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md` freezes
   the metric set, the baselines, the signed magnitude-match diagnostic and the uncertainty
   treatment before the first predictive result. `docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`
   stages the information families and the admission rule for each.

8. **Legacy generation preserved.** The prior programme is recorded as
   `COST_EXPECTANCY_RESEARCH_GENERATION_V1` with disposition
   `SUPERSEDED_BY_OWNER_PREDICTION_FIRST_OBJECTIVE`. All experiments, negative results and
   terminal classifications stand unchanged. ALIGNED remains a historical/paper baseline —
   not Champion, not the new research target. The complete pre-pivot implementation is
   preserved on `archive/cost-expectancy-v1` at
   `01c629e81f4434034da60acc6a79c4be3cdbde19`.

9. **Prospective ALIGNED observer suspended.** Automatic collection on `main` ends with
   disposition `SUSPENDED_BY_OWNER_OBJECTIVE_PIVOT`. The implementation is not deleted.

## Genuine prospective evidence existed and is preserved

The observer was inspected before any lifecycle code changed. It had produced genuine
evidence after the last Research Director review, and that evidence is preserved exactly:

| Fact | Value |
| --- | --- |
| Decision records | 3 |
| Genuine observations | 1 (`2026-09-16T15:00:00Z`, decision `NO_TRADE`) |
| Missed decisions | 2 (`13:00Z`, `14:00Z`, `BACKEND_DOWNTIME`) |
| Raw prospective LONG signals | 0 |
| Shadow trades opened / completed | 0 / 0 |
| Audit chain events / integrity | 4 / `VALID` |
| Build provenance | `BUILD_PROVENANCE_V1_1`, verified |
| Review boundary (20 completed shadow trades) | not reached |

The runtime stores were copied verbatim into `research/prospective/` and the disposition
record is derived deterministically from those copies by
`scripts/finalize_prospective_observer.py --check`, which runs in repository validation.
Nothing was backfilled, no missed boundary was reconstructed, no evidence was rewritten,
and the runtime stores were not deleted. One `NO_TRADE` observation supports no scientific
conclusion whatsoever; it is recorded because it happened, not because it means anything.

## Consequences

The next checkpoint is a bounded `PREDICTIVE-BASELINES-V1` foundation: deterministic labels
and evaluation, then simple chronological baselines. It proves label causality and
evaluation correctness before any model complexity and before any external information
family. This checkpoint deliberately trains nothing.

Accounting is untouched by a change of objective: 26 experiments completed, 12 observed
material historical hypotheses, 0 sealed queries, Champion `NONE`, real money `false`. The
predictive generation starts its own accounting at zero, and the two are never pooled.

The cost of this pivot is honest: roughly a full research generation of historical search
does not transfer as evidence. Its data manifests, integrity tooling, execution substrate,
evaluation discipline and negative results do transfer, and the superseded results remain
valid answers to the question they were asked.

One risk is recorded rather than resolved. A prediction-first objective with a prominent
win-rate metric is easier to fool oneself with than a cost-adjusted one, because a win rate
is intuitive and can be inflated by abstention, class imbalance and horizon choice. The
countermeasure is the mandatory companion metric set: coverage, calibration, magnitude
error, predeclared baselines and dependence-aware intervals are not optional additions to
the win rate — without them the win rate is not a result.
