# ADAPTIVE_MULTISIGNAL_ARCHITECTURE_OPTIONS_V1

**DESIGN ONLY — ZERO MARKET TESTS**

The Owner's requirement is that the relative importance of internal market signals
and point-in-time exogenous context may change through time and regime. WP-009 defines
exactly three future candidates without choosing one, fitting a model, calculating a
BTC relationship, or allocating a strategy experiment.

## Candidate A — exponentially weighted dynamic linear model

An expanding or rolling recursive linear estimator assigns exponentially decreasing
weight to older training observations. It is the most interpretable option: the active
coefficient vector and each standardized feature contribution are directly auditable.

- Required data: leakage-safe internal features, `EXOGENOUS_CONTEXT_V1`, a separately
  preregistered outcome label, and chronological availability/training cutoffs.
- Free hyperparameters: decay or half-life, regularization kind/strength if any,
  initialization, minimum history, refit cadence, and missing-feature policy.
- Deterministic controls: static linear baseline, frozen no-exogenous ablation,
  timestamp-matched no-update control, and exact coefficient/contribution replay.
- Leakage protection: training labels must be complete before each update; scaling and
  weights use only the then-available training window; no full-history half-life choice.
- Failure modes: unstable coefficients, friction-dominated turnover, one-regime
  dominance, collinearity, and false responsiveness from monitoring drift.
- Tuning risk: half-life and regularization are powerful hidden search dimensions and
  require a small explicit budget selected without validation outcomes.
- Integration/audit: all internal and exogenous groups enter a frozen feature order;
  prediction-time coefficients, standardized contributions, turnover, sign changes,
  and grouped influence are retained.

## Candidate B — regime-conditioned mixture of linear experts

Several simple linear experts are combined by a contemporaneous gating rule. It makes
changing importance explicit but introduces a second model layer and regime-definition
risk.

- Required data: the same point-in-time internal/exogenous substrate, a frozen label,
  and regime inputs available at each timestamp.
- Free hyperparameters: number of experts, regime/gating definition, transition rule,
  minimum samples per regime, expert regularization, and update cadence.
- Deterministic controls: one global linear expert, frozen externally defined regimes,
  hard versus probabilistic gating as separately budgeted alternatives, and expert
  sample-count floors.
- Leakage protection: regimes cannot be defined by future outcomes, full-sample
  clustering, or ex-post profitable periods; training and gating updates are purged
  chronologically.
- Failure modes: sparse regimes, unstable transitions, label leakage through regime
  construction, expert collapse, discontinuous trading, and multiplicative search
  burden.
- Integration/audit: each expert may combine all governed groups; retain expert-level
  contributions, gating probabilities, active sample counts, transition provenance,
  and the probability-weighted grouped total at prediction time.

## Candidate C — online Bayesian/state-space dynamic regression

Coefficients evolve as latent states and are updated sequentially. Filtered posterior
uncertainty can distinguish weak evidence from apparent coefficient movement, but the
method has the highest implementation and hidden-tuning complexity.

- Required data: the point-in-time internal/exogenous substrate, a sequential label
  stream with completion times, prior definitions, and deterministic numeric routines.
- Free hyperparameters: coefficient process noise, observation noise, prior covariance,
  shrinkage structure, update cadence, and missing-observation treatment.
- Deterministic controls: static Bayesian regression, zero-process-noise state model,
  synthetic coefficient-drift recovery, and filtered-versus-smoothed guard tests.
- Leakage protection: only filtered states may predict; backward smoothing is forbidden
  for historical signals; labels update the state only after complete outcomes.
- Failure modes: process noise masquerading as adaptability, posterior overconfidence,
  numeric sensitivity, unstable coefficients, and extensive implicit tuning.
- Integration/audit: latent coefficients cover the frozen internal/exogenous groups;
  retain filtered means/covariances, per-feature contributions, credible intervals,
  state innovations, and grouped influence at every prediction.

## Decision boundary

The Research Director selects one candidate only after reviewing WP-009 source
coverage, drift, and as-of integrity. Selection must not use a WP-009 BTC result because
none exists. A separate work package must freeze the label, features, hyperparameters,
controls, trial budget, model-update timing, and attribution method before any market
evaluation. No architecture receives a sealed query, Champion status, paper action, or
real-capital authority from this design.
