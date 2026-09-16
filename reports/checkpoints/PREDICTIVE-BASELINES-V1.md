# Predictive baselines V1

The predictive foundation of `PREDICTIVE_RESEARCH_GENERATION_V1`. Deterministic 24h labels,
chronological folds with purge and embargo, the frozen scorer, and the four required naive
baselines. No predictor was trained, no information family was admitted, no sealed data was
touched, and no candidate or Champion was created.

Full numbers: `reports/research/PREDICTIVE-BASELINES-V1.md` and its JSON.

## The pre-result correction came first

Implementing the contract exposed a contradiction inside it, and it was corrected before any
baseline number was computed on market data. That ordering is the whole point:
[ADR-0027](../../decisions/ADR-0027-BASELINE-PROBABILITY-SEMANTICS-AND-METRIC-APPLICABILITY.md)
and Amendment A1 of `PREDICTIVE_EVALUATION_CONTRACT_V1` were recorded, then the baselines ran.

§5 had defined `TRAINING_UP_BASE_RATE` as "the majority direction of the training set, with
constant probability equal to the training-set empirical UP base rate". Those clauses
disagree whenever the majority is `DOWN`: at `p_up = 0.45` the baseline declares `DOWN` while
carrying `probability = 0.45`, which reads as a 45% chance the declared direction is right
when the construction implies 55%. §2 defines `probability` as `P(declared direction
correct)` everywhere else, so the Brier score and reliability table would have measured an
inversion introduced by the definition rather than anything about the market.

§4 compounded it by making calibration and magnitude metrics unconditional for "every
predictive result", which would have forced an invented probability onto `ALWAYS_UP` and
`PREVIOUS_24H_SIGN_PERSISTENCE` purely to fill a required field.

Amendment A1 fixes the construction — `p_up` from the fold's training portion only, majority
declared, `probability = p_up` for `UP` and `1 - p_up` for `DOWN`, tie rule `p_up >= 0.5 ->
UP` — and makes each metric mandatory exactly when the quantity it scores is declared.
Deterministic directional baselines now report `probability: null`,
`PROBABILITY_NOT_DECLARED`, no Brier, no reliability table. `ZERO_RETURN_MAGNITUDE` stays
magnitude-only. Nothing was weakened: §4 also states that anything used as a confidence,
ranking, threshold or sizing input **is** probabilistic and must be calibrated, so "declare
no probability" cannot become an escape route for a real model.

## Labels and eligibility

`r_24h = log(close[T + 24h] / close[T])` on the hourly decision grid, 1m-derived closes,
strictly inside the development cutoff.

64,652 grid instants, 64,323 admissible labels, 329 excluded and fully typed:
`DECISION_BAR_MISSING` 127, `DECISION_BAR_INCOMPLETE` 31, `HORIZON_BAR_MISSING` 118,
`HORIZON_BAR_INCOMPLETE` 29, `HORIZON_BAR_BEYOND_COVERAGE` 24, `NON_POSITIVE_PRICE` 0. The
accounting closes exactly. Canonical gaps yield inadmissible labels; nothing is interpolated
and no nearest-bar substitution exists.

Direction truth: UP 33,637, DOWN 30,681, **NEUTRAL 5** — counted, excluded from directional
scoring, never counted as wins.

Folds are expanding chronological walk-forward over 2019–2024 with a 24h purge and embargo on
both sides of every boundary, so no label window crosses a fold edge in either direction.
Eligible universe 52,315; the remaining admissible labels are 11,893 warmup training and 115
removed by the boundary embargo. 52,315 + 11,893 + 115 = 64,323.

## Proofs, not prose

Causality is proven on synthetic bars: the label reads exactly `close[T]` and `close[T+24h]`
and is invariant to every bar between them and before them; a forward shift moves labels
exactly one shift; a backward shift is detected; the look-ahead guard rejects any
decision-time feature that reads a later bar; the last admissible decision is exactly one
horizon before coverage ends; gaps and incomplete bars are excluded and typed; an exactly
flat window is `NEUTRAL` and is counted.

Scorer correctness is proven on fixtures with hand-computed answers: a perfect predictor
scores 1.0 at coverage 1.0; an always-wrong one scores 0.0; abstaining everywhere but one
correct call scores 1.0 at coverage 0.01 and the report makes that visible; Brier and the
reliability table reproduce hand values, with the closed final bin and empty bins reported
rather than merged; the magnitude diagnostic returns +100, +10 either way, and the negative of
that on a wrong direction, with each of the three near-zero classes excluded and counted; the
moving-block interval is wider than naive Wilson on deliberately overlapping labels and is
deterministic under the frozen seed; the directional sample accounting closes on every path.

## What the baselines say

Pooled over 52,315 eligible timestamps: `TRAINING_UP_BASE_RATE` and `ALWAYS_UP` both
**0.5262** at coverage 0.99996, moving-block 95% [0.5109, 0.5412]; Brier 0.2497 for the
probabilistic one. `PREVIOUS_24H_SIGN_PERSISTENCE` **0.4667** at coverage 0.99845,
[0.4547, 0.4792]. `ZERO_RETURN_MAGNITUDE` MAE **2.2635 pp** (226.35 bps), median 1.4599 pp.

Four things matter for what comes next.

**The bar is 0.526, not 0.500.** A predictor reaching 53% has demonstrated nothing. The
comparison that counts is against `ALWAYS_UP`.

**The `DOWN`-majority branch was never exercised.** The training majority was UP in all six
folds (p_up 0.5095–0.5335), so `TRAINING_UP_BASE_RATE` and `ALWAYS_UP` are numerically
identical here and the tie rule never fired. The branch Amendment A1 exists to get right is
proven by test, not by this run — recorded in state as
`down_majority_branch_exercised: false`.

**Persistence is anti-predictive at this horizon**, below 50% in all six folds, pooled 0.4667
with an interval comfortably excluding 0.5. Its inverse would score ~0.533. Inverting it now
would be precisely the result-driven adaptation the protocol forbids; it is recorded and
nothing is built on it.

**The dependence correction is not cosmetic.** The moving-block interval is ~3.5× wider than
naive Wilson (0.0304 vs 0.0086 for `ALWAYS_UP`). Treating 52,315 overlapping 24h labels as
independent would have made a ~1pp edge look decisive.

## Validation and accounting

Backend tests, `check.py --no-data`, ruff, format, mypy and frontend validation all pass. The
committed report is replayed byte-for-byte against the installed market data in the data-mode
branch of repository validation, and validated for internal consistency against the frozen
protocol without data, so CI guards it too.

Model fits 0. Sealed queries 0. Historical accounting untouched: 26 experiments, 12 observed
material historical hypotheses. The prospective ALIGNED observer remains
`SUSPENDED_BY_OWNER_OBJECTIVE_PIVOT` with its preserved evidence byte-identical. Champion
`NONE`, real money `false`.

## Next

`PREDICTIVE-INTERNAL-STRUCTURE-V1`: the first candidate predictors on internal price, volume
and volatility structure, scored by this frozen contract against these baselines, with
coverage, calibration, magnitude error and dependence-aware intervals. No external
information family enters until Stage 1 has been answered.
