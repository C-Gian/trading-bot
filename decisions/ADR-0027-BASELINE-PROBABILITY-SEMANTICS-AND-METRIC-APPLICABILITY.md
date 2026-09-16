# ADR-0027 — Baseline probability semantics and metric applicability

Status: ACCEPTED (2026-09-16)

Amends [ADR-0026](ADR-0026-PREDICTION-FIRST-RESEARCH-OBJECTIVE.md) and
`docs/canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md` §4 and §5, recorded as Amendment A1
in §11 of that contract. Every other decision in ADR-0026 remains in force.

## Context

`PREDICTIVE_EVALUATION_CONTRACT_V1` was frozen before the first predictive result. Its
first use — implementing the four required baselines for `PREDICTIVE-BASELINES-V1` — exposed
an internal contradiction in the frozen text, **before** any baseline number was computed on
market data.

§2 defines `probability` as the calibrated probability that the *declared* direction is
correct. §5 defined `TRAINING_UP_BASE_RATE` as

> always predicts the majority direction of the training set, with constant probability
> equal to the training-set empirical UP base rate

Those clauses are incompatible whenever the training majority is `DOWN`. With
`p_up = 0.45` the baseline declares `DOWN` and carries `probability = 0.45`, which reads as
a 45% chance the declared direction is correct when the construction implies 55%. The Brier
score and reliability table would then have measured an inversion introduced by the
definition, not a property of the market — and the naive baseline would have looked
badly miscalibrated for a purely clerical reason.

§4 compounded it. It made calibration and magnitude metrics unconditional for "every
predictive result". `ALWAYS_UP` and `PREVIOUS_24H_SIGN_PERSISTENCE` assert no probability
at all; applied literally, §4 would have forced an invented probability — 1.0, 0.5 or the
base rate — purely to fill a mandatory field, and produced a Brier score for a claim no
baseline ever made. `ZERO_RETURN_MAGNITUDE` asserts no direction and would likewise have
been forced into a win rate.

A calibration requirement that can be satisfied by fabricating the input it scores is worse
than no requirement, because the fabricated number is indistinguishable from a real one in
the record.

## Decision

Correct the contract before observation, not after.

1. **`TRAINING_UP_BASE_RATE` is reconstructed** so its probability means what every other
   probability in the contract means. `p_up` is computed exclusively on the fold's
   chronological training portion as `UP / (UP + DOWN)`, with `NEUTRAL` labels excluded and
   counted. The majority direction is declared. `probability = p_up` when `UP` is declared
   and `1 - p_up` when `DOWN` is declared. The tie rule is preregistered and deterministic:
   `p_up >= 0.5` declares `UP`, so an exact tie declares `UP` at `probability = 0.5`.
   Consequently `probability >= 0.5` always and is always `P(declared direction correct)`.
   No part of a fold's evaluation portion may enter `p_up`, the majority vote or the tie
   break.

2. **Deterministic directional baselines declare no probability.** `ALWAYS_UP` and
   `PREVIOUS_24H_SIGN_PERSISTENCE` report `probability: null` with the explicit flag
   `PROBABILITY_NOT_DECLARED`. They receive no Brier score and no reliability table. They
   are reported with win rate, coverage, sample accounting and the dependence-aware
   uncertainty interval, exactly as before.

3. **`ZERO_RETURN_MAGNITUDE` stays magnitude-only**, `DIRECTION_NOT_DECLARED`, excluded
   from win rate, coverage and calibration. Because its predicted magnitude is identically
   zero, every record falls under the `ABSTAINED_MAGNITUDE` rule of §6 and its
   magnitude-match aggregate is undefined by construction; the exclusion count is reported
   rather than suppressed.

4. **Metric applicability is made explicit.** A metric is mandatory exactly when the
   quantity it scores is declared. Direction metrics for direction, calibration for
   probability, magnitude metrics for magnitude. Which quantities a predictor declares is
   fixed before results are observed, and a predictor may never drop a declared quantity
   afterwards to escape the metric that scores it.

## Consequences

Nothing is weakened. No metric is removed, no threshold is relaxed, no baseline is dropped,
and no predictor becomes easier to pass. The amendment closes a loophole rather than
opening one: §4 now states that anything used as a confidence, ranking, threshold or sizing
input **is** probabilistic and must be calibrated, so "declare no probability" cannot become
a route around calibration for a real model.

The timing is the point. This was found while implementing the contract and corrected before
`PREDICTIVE-BASELINES-V1` computed a single baseline number on market data, so no observed
result influenced the correction and none was reinterpreted by it. Had it been found after
observation, the contract would have had to stand and the artifact would have had to be
reported as an artifact.

One residual risk is recorded rather than resolved. `TRAINING_UP_BASE_RATE` now declares
`probability >= 0.5` by construction, so its reliability table can only ever populate the
upper bins. That is a true property of the baseline, not a defect: a constant predictor has
nothing to calibrate across. It means its Brier score is a reference point for a real
probabilistic model, not evidence of calibration quality in itself.
