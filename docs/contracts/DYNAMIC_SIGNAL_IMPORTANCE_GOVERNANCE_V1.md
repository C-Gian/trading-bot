# DYNAMIC_SIGNAL_IMPORTANCE_GOVERNANCE_V1

Status: prospective design governance; no adaptive model is authorized by WP-009.

## Purpose

Future adaptive multi-signal models must make time-varying influence reconstructable
without using future-fitted parameters or shopping among attribution methods after
results. Attribution is audit evidence, not a causal claim.

## Prediction-time record

For every emitted prediction, where the model class permits, retain or deterministically
reconstruct:

- signal timestamp and exact active feature values;
- model version and immutable executable/configuration identity;
- training-data cutoff and all point-in-time source cutoffs;
- coefficients or weights active at that timestamp;
- the training-only normalization state;
- standardized contribution per feature;
- prediction before any execution or occupancy filter;
- grouped contributions for exactly:
  `MARKET_PRICE`, `VOLATILITY_LIQUIDITY`, `ORDER_FLOW`, `MACRO_FINANCIAL`,
  `CRYPTO_NEWS_POLICY`, `GEOPOLITICAL`, and `SOCIAL`.

The contribution sum plus intercept/base value must reconcile to the recorded
pre-filter prediction within a preregistered numerical tolerance. Missing-feature
handling and group membership are frozen before results.

## Historical reconstruction

At historical time `t`, influence uses only weights whose training cutoff and all
source availability timestamps are `<= t`. Future-fitted weights, future revisions,
later regime assignments, smoothed posterior states, and retrospective relabeling may
not be projected backward. Filters that suppress execution do not erase the underlying
prediction or contributions.

## Model-specific attribution

Linear models use exact standardized `beta_i * z_i` contributions. Mixtures retain
both each expert's contribution and the contemporaneous gating weights. State-space
models retain the filtered, never smoothed, coefficient posterior used at prediction.

Any future nonlinear or interacting model must preregister one deterministic
attribution method, baseline/reference distribution, grouping rule, and reconciliation
tolerance before results. No post-hoc choice among SHAP, permutation, gradients,
ablation, or other explanations is permitted.

## Audit and failure

Each future experiment declares influence-stability diagnostics, missing-attribution
counts, contribution concentration, coefficient/weight turnover, and reconciliation
hashes. Missing prediction-time provenance, any future-fitted influence, or failure of
contribution reconciliation invalidates the affected result. Importance plots or
narratives never select features, regimes, thresholds, or model variants after result
observation.
