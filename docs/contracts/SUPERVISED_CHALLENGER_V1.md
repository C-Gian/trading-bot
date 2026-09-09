# SUPERVISED_CHALLENGER_V1

Status: frozen prospectively for WP-008 before any validation result.

## Purpose and scope

This contract governs one interpretable BTCUSDT Spot supervised challenger,
`LINEAR_NET_R_SELECTION_V1`. It is a predictive hypothesis, not a causal claim.
There are exactly two configurations: primary `LINEAR_FULL` uses F1–F8 and structural
ablation `LINEAR_NO_FLOW` uses F1–F6. No other model, feature subset, interaction,
regularization value, threshold, exit, barrier, or horizon is authorized.

## Signal-time rows

At hourly boundary `t`, the current 1h bar is the bar `[t-1h,t)`. All hourly windows
must be contiguous, complete, and outside source-grid quarantine. The 4h context is the
latest completed, non-overlapping 4h bucket whose close is at or before `t-1h`; its
43-bar window must also be contiguous, complete, and unquarantined. Missing values are
never forward-filled.

Feature order is fixed:

1. `LOG_RETURN_1H`: `ln(current close/current open)`.
2. `LOG_RETURN_24H`: `ln(current close/close 24 hours earlier)`.
3. `LOG_DISTANCE_TO_PRIOR_24H_HIGH`: `ln(current close/max(previous 24 highs))`.
4. `REALIZED_VOL_24H`: square root of the mean squared value of exactly 24 contiguous
   close-to-close hourly log returns ending at the current close; not annualized.
5. `LOG_RELATIVE_VOLUME_1H`: `ln(current base volume/arithmetic mean(previous 24 base
   volumes))`; numerator and denominator must be positive.
6. `DIRECTIONAL_EFFICIENCY_4H`: over 42 changes from 43 completed 4h closes,
   `(U-D)/(U+D)`, where `U` sums positive changes and `D` is the absolute sum of
   negative changes; `U+D` must be positive. The historical 2:1 gate is not applied.
7. `TAKER_BUY_SHARE_1H_CENTERED`: current eligible `ORDER_FLOW_FEATURES_V1` hourly
   taker-buy base share minus `0.5`.
8. `TAKER_BUY_SHARE_4H_CENTERED`: eligible `ORDER_FLOW_FEATURES_V1` context share
   minus `0.5`.

## Training label

`ISOLATED_FIXED_PLAN_DEFAULT_NET_R_V1` is computed for training only. At each eligible
signal, reference is the just-completed hourly close; entry is the next canonical 1m
open; stop is reference × `0.98`; target is reference × `1.04`; horizon is 1,440
minutes. `BACKTEST_ENGINE_V2`, `EXECUTION_MODEL_V2`, and default
`BTCUSDT_SPOT_COST_V1` apply. Each plan is isolated: position occupancy is not applied
between labels. Invalid, unresolved, or missing-future-path labels are excluded and
counted, never imputed, clipped, or winsorized.

## Chronological folds and leakage controls

The six validation folds and their signal containment are exactly those in
`DEVELOPMENT_WALK_FORWARD_V1`: 2019–2024, with validation beginning January 2 and the
last full-horizon signal at December 31 00:00 UTC. For a fold beginning at `v`, the
training interval expands from the earliest eligible history and ends exclusively at
`v-216h`. Therefore the latest permitted training signal is one hour earlier, and a
maximum 24h label outcome ends at least 193h before validation. Every recorded label
outcome must be strictly earlier than validation start; violation hard-fails.

No validation-year information enters label construction, feature selection, feature
scaling, model fitting, threshold selection, or model specification. Normalization is
fit separately on each fold's training rows only (`ddof=0`). Full-history scaling and
random K-fold are forbidden.

## Model and production evaluation

For each fold/configuration, deterministic NumPy float64 ordinary least squares fits
an intercept and all declared standardized features. Feature standard deviation must
exceed `1e-12`; the design matrix must have full column rank. Means, standard
deviations, intercept, coefficients, rank, condition number, input hashes, dependency
hash, and prediction hash are retained.

LONG is emitted exactly when `predicted_default_net_R > 0.0`. Normal one-position
occupancy then applies to the unchanged 2% stop, 4% target, 1,440-minute production
execution plan. Models train once from DEFAULT-cost labels. ZERO, DOUBLE, and DELAY_1H
never refit; DELAY_1H uses at `t` the prediction from the exact `t-1h` feature vector,
while reference and execution geometry remain based on `t`.

The primary family conclusion always follows `LINEAR_FULL`. Even a promising exposed
development result authorizes no Champion, sealed query, or paper trade.
