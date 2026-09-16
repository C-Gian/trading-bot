# Predictive research rebaseline V1

Owner-authorized change of scientific and product objective, executed as a governance and
architecture rebaseline. No predictor was trained, no market experiment was run, no sealed
data was queried, and no result was produced. See
[ADR-0026](../../decisions/ADR-0026-PREDICTION-FIRST-RESEARCH-OBJECTIVE.md).

## New mission

The primary objective is a statistically credible BTCUSDT predictor estimating future
price direction, calibrated probability and expected movement magnitude over explicitly
declared horizons. The Constitution is reissued as Version 2.0, prediction-first, with
Version 1.0 preserved verbatim in its Appendix A and every rigour rule carried forward
unweakened.

The single material rule replaced is Version 1.0's "hit rate is secondary to robust net
expectancy". Directional win rate becomes a primary human-facing predictive metric — and
becomes meaningless alone. The countermeasure is mandatory, not advisory: coverage, sample
size and chronological distribution, Brier score with a fixed-bin reliability table,
magnitude MAE, a signed magnitude-match diagnostic, four predeclared baselines, a
dependence-aware uncertainty interval, and per-fold reporting including unfavourable folds.

Costs leave the primary score. They remain mandatory and versioned for any claim of
economic or trading profitability, and are no longer part of scoring a pure prediction.

## Frozen target and definitions

BTCUSDT spot, canonical 1m source data, 1h closed-bar decision cadence, primary horizon 24h
terminal: `r_24h = log(close[t+24h] / close[t])`. `UP` when positive, `DOWN` when negative,
exact zero `NEUTRAL` — excluded from directional scoring and counted explicitly, never
silently dropped and never counted as a win.

`probability` is the calibrated probability that the declared direction is correct at the
primary horizon. `strength` is the percentile rank, 0–100, of the predicted absolute 24h
move within the training-only distribution of absolute 24h moves at model-fit time. The two
are orthogonal by construction: 90% probability with 30% strength means high directional
confidence in a modest move. An uncalibrated score is never displayed as a probability.

The Owner's magnitude-quality intuition is preserved as a bounded secondary diagnostic:
`100 * sign_agreement * min(|p|,|a|) / max(|p|,|a|)`, both magnitudes floored at 1e-4. Exact
magnitude in the right direction scores +100, a ten-times miss either way scores +10 — the
score is symmetric — and a wrong direction carries the negative sign. Near-zero and neutral
records are excluded by an explicit deterministic rule and counted. MAE remains the standard
magnitude metric alongside it.

Layer separation is architectural:
`PREDICTION -> DECISION/POLICY -> ECONOMIC/EXECUTION SIMULATION`. Prediction quality must
not depend on capital, fees, leverage, slippage, network costs or sizing. `EUR 5,000`
survives only as a display/scenario assumption in the economic layer.

Both contracts are canonical and frozen before the first predictive result:
`docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md` and
`docs/canonical/PREDICTIVE_SOURCE_ROADMAP_V1.md`. The roadmap stages information families
from internal structure through derivatives, cross-asset and macro vintage, public news and
attention, to on-chain — each entering only through a preregistered
incremental-information experiment with a defensible point-in-time availability rule.

## Legacy generation

The prior programme is recorded as `COST_EXPECTANCY_RESEARCH_GENERATION_V1`, disposition
`SUPERSEDED_BY_OWNER_PREDICTION_FIRST_OBJECTIVE`. Its 26 experiments, 12 observed material
historical hypotheses and every negative result stand unchanged. ALIGNED remains a
historical/paper baseline: not Champion, not the new research target. The complete
pre-pivot implementation is preserved on `archive/cost-expectancy-v1` at
`01c629e81f4434034da60acc6a79c4be3cdbde19`, verified as an ancestor of this HEAD. That
generation transfers no predictive evidence — only substrate, tooling and discipline.

## Prospective ALIGNED observer — genuine evidence existed

The observer was inspected before any lifecycle code changed, and it had produced genuine
evidence after the last Research Director review. The claim of zero observations that held
at the previous checkpoint is no longer true, and was not repeated.

| Fact | Value |
| --- | --- |
| Decision records | 3 |
| Genuine observations | 1 — `2026-09-16T15:00:00Z`, decision `NO_TRADE` |
| Missed decisions | 2 — `13:00Z`, `14:00Z`, `BACKEND_DOWNTIME` |
| Evaluated boundaries / market fetches | 1 / 1 |
| Raw prospective LONG signals | 0 |
| Shadow trades open / completed | 0 / 0 |
| Audit chain events / integrity | 4 / `VALID` |
| Build provenance | `BUILD_PROVENANCE_V1_1`, verified, clean worktree |
| First / final activation | `2026-09-16T12:58:55Z` / `2026-09-16T14:26:06Z` |
| Review boundary (20 completed shadow trades) | not reached |
| Final disposition | `SUSPENDED_BY_OWNER_OBJECTIVE_PIVOT` |

The runtime evidence and health stores were copied verbatim into `research/prospective/`
and are now tracked. The disposition record is derived deterministically from those copies
by `scripts/finalize_prospective_observer.py`, whose `--check` mode re-derives it from the
preserved artifacts alone and runs inside repository validation — so a clean checkout that
has never run an observer still verifies the accounting. Nothing was backfilled, no missed
boundary was reconstructed, no evidence was rewritten, the runtime stores were not deleted
and remain untracked, and the implementation was not deleted.

Automatic collection on `main` is off as a code fact, not a declaration: `main` constructs
no observer, guarded by `AUTOMATIC_COLLECTION_ENABLED` and asserted in validation. The
status endpoint reports the suspension. One `NO_TRADE` observation supports no scientific
conclusion; it is recorded because it happened.

## Product intent

Canonical product intent is updated, not the full frontend. The intended Analyze Market
output is a forecast block — horizon, direction, calibrated probability, strength 0–100
labelled as magnitude, expected move in percent and approximate quote units, uncertainty
with coverage and sample size — and a separate action block, `LONG` or `NO_TRADE`,
paper-only. Trade economics, when shown, are shown separately from prediction quality.
Until an approved predictor exists the surface says so rather than showing a placeholder.

## Validation and accounting

Backend tests, `check.py --no-data`, ruff, format, mypy and the frontend lint / typecheck /
test / build all pass. Historical accounting is untouched by a change of objective: 26
experiments completed, 12 observed material historical hypotheses, 0 sealed queries,
Champion `NONE`, real money `false`. The predictive generation starts its own accounting at
zero — 0 predictive experiments, no predictor trained, no predictive result observed, no
win-rate target declared — and the two are never pooled.

## Next

`PREDICTIVE-BASELINES-V1`: deterministic 24h labels and the frozen evaluation
implementation, then the four simple chronological baselines. Label causality and
evaluation correctness are proven before any model complexity and before any external
information family.
