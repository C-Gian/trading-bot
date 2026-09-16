# Predictive evaluation contract V1

Canonical. Owner-authorized prediction-first objective; see
[ADR-0026](../../decisions/ADR-0026-PREDICTION-FIRST-RESEARCH-OBJECTIVE.md) and
[the Constitution](../../governance/SCIENTIFIC_CONSTITUTION.md).

This document freezes how a BTCUSDT prediction is defined, scored and reported, **before**
the first predictive result of the new research generation is produced. It may be extended
by a later canonical version, but never weakened, and never after a result it would govern
has been observed.

It does not authorize an experiment. It does not train anything. Machine-readable current
state lives only in `state/current_state.json`.

## 1. Frozen predictive target

| Item | Value |
| --- | --- |
| Market | BTCUSDT spot |
| Canonical source resolution | 1 minute |
| Forecast decision cadence | 1 hour (closed-bar boundaries, UTC) |
| Primary forecast horizon | 24 hours, terminal |
| Prediction target | `r_24h = log(close[t + 24h] / close[t])` |
| Real money | forbidden |

`t` is a decision timestamp: the close of a completed 1h bar. `close[t]` is that bar's
close. `close[t + 24h]` is the close of the 1h bar 24 hours later. Both are canonical
1m-derived closes. No intra-horizon path information enters the primary target — the
primary horizon is terminal, not path-dependent.

Direction truth:

- `UP` when `r_24h > 0`;
- `DOWN` when `r_24h < 0`;
- `NEUTRAL` when `r_24h == 0` exactly.

`NEUTRAL` truth is undefined for directional scoring. It is excluded from the win-rate
numerator and denominator and **must be counted and reported explicitly**; it may never be
silently dropped, nor counted as a win.

The predictor may emit both `UP` and `DOWN` even though the V1 trade-action layer remains
`LONG` / `NO_TRADE` for spot. Prediction and trade action are separate concepts. This
checkpoint adds no leverage and no short execution.

A label is only admissible when the full forward window is present in canonical data and
strictly after the decision timestamp. A decision timestamp whose forward window is
incomplete or unavailable is **not** an eligible decision timestamp and is excluded from
every denominator, with the exclusion counted.

## 2. Canonical prediction fields

| Field | Meaning |
| --- | --- |
| `direction` | `UP`, `DOWN`, or `NEUTRAL_UNCERTAIN` |
| `probability` | calibrated probability that the declared `direction` is correct at the primary horizon |
| `expected_return_pct` | predicted signed 24h terminal return, in percent |
| `expected_move_quote` | UI-only conversion of `expected_return_pct` to approximate BTCUSDT quote-currency movement at the decision price |
| `strength` | 0–100 magnitude scale; **not** a probability |

### Probability

`probability` is the empirically calibrated probability that the declared direction is
correct at the primary horizon. A raw model score is not a probability. Any model score
must pass through a calibration map fitted on training-only data before it may be exposed
as `probability`, and the calibration must itself be evaluated (§4).

`NEUTRAL_UNCERTAIN` is a legitimate output. It means the predictor declines to declare a
direction, and such a timestamp is eligible but not actionable (§3).

### Strength

For V1, `strength` is the percentile rank, on a 0–100 scale, of the predicted absolute 24h
move `|expected_return_pct|` within the training-only distribution of realized absolute 24h
moves available at model-fit time.

This makes probability and strength orthogonal by construction. A prediction of 90%
probability with 30% strength means high confidence in direction with a relatively modest
expected move. Strength is never displayed, described or aggregated as a probability.

The reference distribution is frozen at model-fit time from training data only. It is never
refitted using validation, test, sealed or post-decision information.

### Expected move in quote currency

`expected_move_quote = close[t] * (exp(r_hat_24h) - 1)`, where `r_hat_24h` is the predicted
log return. It is a presentation convenience for one unit of BTC at the decision price. It
carries no fee, slippage, capital or position-size assumption and is never an input to any
predictive metric.

## 3. Primary metric and coverage

**Primary human-facing metric — actionable directional win rate:**

```
win_rate = correct_directional_predictions / actionable_directional_predictions
```

- An *eligible decision timestamp* is an hourly boundary in the evaluation window whose
  24h forward label is admissible (§1).
- An *actionable directional prediction* is a prediction at an eligible timestamp whose
  `direction` is `UP` or `DOWN` and whose realized truth is not `NEUTRAL`.
- A prediction is *correct* when its declared direction equals the realized direction.

```
coverage = actionable_directional_predictions / eligible_decision_timestamps
```

Win rate is never reported, quoted or interpreted without coverage and sample size in the
same view. A predictor that abstains on all but a handful of timestamps has not earned a
high win rate; it has chosen a small sample.

## 4. Mandatory companion metrics

Every predictive result must report all of the following. None is optional, and none may
be replaced by a more favourable alternative after results are observed.

1. **Coverage** — as defined in §3.
2. **Sample size and chronological distribution** — eligible timestamps, actionable
   predictions, abstentions, `NEUTRAL` truths, and inadmissible-label exclusions, each
   broken down by chronological fold so a result cannot rest on one short period.
3. **Calibration** — Brier score over the declared-direction probability, plus a reliability
   table with fixed predeclared probability bins
   `[0.0,0.1), [0.1,0.2), …, [0.9,1.0]`, reporting per bin: count, mean predicted
   probability, empirical frequency correct. Bins are never merged or re-cut after results.
4. **Magnitude error** — MAE of the signed 24h return prediction, reported in percentage
   points and in basis points, over the admissible-label set. Median absolute error is
   reported alongside as a robustness companion.
5. **Signed magnitude-match diagnostic** — §6.
6. **Directional baseline comparison** — §5, each baseline scored on the identical eligible
   universe.
7. **Uncertainty interval for the directional win rate** — §7.
8. **Performance by major chronological folds / regimes** — reported for every fold,
   including unfavourable ones. Post-result threshold rescue, fold selection, fold
   re-cutting and coverage re-tuning are forbidden.

## 5. Required naive baselines

At minimum, and on the identical eligible universe as the model:

| Baseline | Definition |
| --- | --- |
| `TRAINING_UP_BASE_RATE` | always predicts the majority direction of the training set, with constant probability equal to the training-set empirical UP base rate |
| `ALWAYS_UP` | always predicts `UP` |
| `PREVIOUS_24H_SIGN_PERSISTENCE` | predicts the sign of the trailing realized 24h return ending at the decision timestamp |
| `ZERO_RETURN_MAGNITUDE` | predicts `r_hat_24h = 0` for every timestamp; a magnitude baseline only, with no directional claim |

Baselines use only information available at the decision timestamp, exactly like the model.

A model is **not** scientifically interesting merely because its win rate exceeds 50%. It
must beat the relevant predeclared baselines with credible out-of-sample evidence and
nontrivial coverage. No arbitrary win-rate target — 70%, 80%, 90% or any other — is
declared before evidence establishes what is feasible.

## 6. Signed magnitude-match diagnostic

A transparent secondary diagnostic that expresses "how close was the predicted move to the
realized move, and was it even the right way". It is a companion to MAE, never a
replacement, and never the sole scientific metric.

Let `p` be the predicted signed 24h return and `a` the realized signed 24h return, in the
same units. Let `eps = 1e-4` (one basis point in return units).

```
floor(x)      = max(|x|, eps)
ratio(p, a)   = min(floor(p), floor(a)) / max(floor(p), floor(a))          in (0, 1]
agreement     = +1 if sign(p) == sign(a) else -1
MMS(p, a)     = 100 * agreement * ratio(p, a)                              in [-100, +100]
```

Properties, by construction:

- exact magnitude in the correct direction scores `+100`;
- same direction, ten-times under-prediction scores `+10`; ten-times over-prediction also
  scores `+10` — the score is symmetric in `p` and `a`;
- a wrong direction carries a negative sign and the same magnitude closeness;
- the score is bounded, so no single observation can dominate an aggregate.

Deterministic zero / near-zero rules, applied in this order:

1. if `|p| < eps` **and** `|a| < eps`, the record is classified `NEAR_ZERO_BOTH`, excluded
   from the aggregate, and counted;
2. else if `a == 0` exactly, the record is classified `NEUTRAL_REALIZED`, excluded from the
   aggregate, and counted;
3. else if `|p| < eps` — the predictor asserted essentially no move — the prediction is not
   an actionable directional prediction; it is classified `ABSTAINED_MAGNITUDE`, excluded
   from the aggregate, and counted;
4. otherwise the formula above applies, with `floor` guaranteeing a non-zero denominator.

The aggregate is the arithmetic mean of `MMS` over included records, always reported with
the three exclusion counts and the included-record count. An aggregate reported without its
exclusion counts is invalid.

## 7. Uncertainty

At a 1h decision cadence with a 24h terminal horizon, consecutive labels overlap by up to
23 hours. Independence is false by construction, so:

- the **primary** uncertainty interval for the directional win rate is a dependence-aware
  interval: a moving-block bootstrap over contiguous chronological blocks of length at
  least the label horizon, with the block length declared before results are observed;
- a naive Wilson interval may be reported **only** when explicitly labelled as an
  optimistic independence-assuming reference. It is never the headline interval;
- the same dependence treatment applies to any baseline-versus-model comparison.

Chronological evaluation is purged and embargoed by at least the label horizon on both
sides of every fold boundary. Standard random K-fold remains forbidden.

## 8. Layer separation

```
PREDICTION LAYER  ->  DECISION / POLICY LAYER  ->  ECONOMIC / EXECUTION SIMULATION
```

- **Prediction layer.** Direction, calibrated probability, expected magnitude, strength.
  Scored by §3–§7. Its quality must not depend on capital size, exchange fee schedule,
  leverage, slippage, blockchain/network costs, or position sizing.
- **Decision / policy layer.** Turns a prediction into an action under a declared policy —
  for V1 spot, `LONG` or `NO_TRADE`. A policy threshold is a policy choice, not a
  prediction-quality parameter, and tuning it never changes a prediction-layer result.
- **Economic / execution simulation.** Applies costs, fills, capital and sizing to a
  decision stream. Transaction costs and execution assumptions are mandatory and versioned
  here, and only here, for any claim of economic or trading profitability.

`EUR 5,000` is retained solely as a configurable future scenario and display assumption in
the economic layer. It is never a training target, never a prediction-quality parameter,
and never an input to any metric in §3–§7. An economic claim may never be supported by
prediction-layer evidence alone.

## 9. Product output

The intended Analyze Market output for V1 is:

- BTCUSDT and the forecast horizon;
- predicted direction;
- calibrated probability;
- strength, 0–100, labelled as magnitude and not as probability;
- expected move in percent and in approximate quote-currency units;
- an uncertainty/context explanation, including coverage and sample size;
- separately, the resulting action: `LONG` or `NO_TRADE`, paper-only in V1;
- later, trade economics shown separately from prediction quality.

The UI must never present an uncalibrated model score as a probability and must never claim
certainty. Until a calibrated predictor exists and has been reviewed, the surface states
that no approved predictor exists rather than displaying a placeholder number.

## 10. What this contract forbids

- Reporting a win rate without sample size and coverage.
- Treating a high win rate obtained by trivial abstention, class imbalance or selective
  reporting as predictive success.
- Choosing thresholds, folds, horizons, probability bins or coverage after observing the
  metric they affect.
- Presenting uncalibrated scores as probabilities, or strength as probability.
- Scoring prediction quality with fees, capital, leverage or slippage.
- Claiming economic profitability from prediction-layer evidence.
- Declaring a win-rate target before evidence establishes feasibility.
- Using any information not available at the decision timestamp.
