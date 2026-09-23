# PREDICTIVE V2 PUBLIC TAKER FLOW 1H INCREMENTAL V1

Status: RESEARCH_DIRECTOR_FROZEN_PREREGISTERED_EXECUTION_BLOCKED_PENDING_POWER_GATE

Experiment: `EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL`

Hypothesis: `H-PRED-V2-PUBLIC-FLOW-INCREMENTAL-001` (the single primary hypothesis of this
experiment; experiment and hypothesis identifiers are distinct).

Decision record: `decisions/ADR-0033-PUBLIC-TAKER-FLOW-FOUNDATION-1H-ONLY-AND-INCREMENTAL-ALLOCATION.md`

Parent foundation: `EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION`
(`FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY`).

## Question

Does the 1h BTCUSDT spot + USD-M taker-flow signal contain incremental out-of-sample
directional probability information beyond the contemporaneous 1h price movement of the same
two markets?

The alternative explanation being tested is that taker imbalance merely proxies
contemporaneous price momentum or relative spot-perpetual movement.

This is an incremental-information diagnostic. It is not a trading-policy experiment: no
action threshold (including the Generation V2 `p_up >= 0.60` LONG rule), no trading PnL, no
execution costs and no threshold search.

## Source

Exactly the official Binance development source already pinned by
`data/manifests/BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1.json`:

- BTCUSDT spot 1m klines;
- BTCUSDT USD-M perpetual 1m klines;
- 2020-01-01 through 2024-12-31 inclusive.

Every object is re-verified against that manifest before use. No other source, no
post-cutoff data and no sealed data.

## Target

Exactly one target:

`r_1h = log(spot_close[T+1h] / spot_close[T])`

UP if > 0, DOWN if < 0, exact zero NEUTRAL. `spot_close[T]` is the spot close of the minute
`[T-1m, T)`, exactly as in the foundation. NEUTRAL and label-unavailable instants are excluded
from scoring and counted. No 4h or 24h target; horizon search is forbidden.

## Common feature window

Decision instants `T` are the UTC hour boundaries. At `T` only the immediately preceding
completed 60 one-minute bars (open times `T-60m .. T-1m`) of each market are read. The
foundation's minute rules apply unchanged: any absent, duplicated, off-grid, incomplete or
non-finite minute in either market makes the instant unavailable. No interpolation, no
nearest-minute substitution, no future minute.

## Features

Price-only control, exactly:

1. `SPOT_LOG_RETURN_1H = log(spot_last_close / spot_first_open)`
2. `UM_LOG_RETURN_1H = log(um_last_close / um_first_open)`
3. `SPOT_MINUS_UM_LOG_RETURN_1H = SPOT_LOG_RETURN_1H - UM_LOG_RETURN_1H`

`first_open` is the open of the minute `[T-60m, T-59m)` and `last_close` the close of the
minute `[T-1m, T)` of that market. A non-positive or non-finite open or close makes the
instant unavailable.

Candidate, exactly the union, in this order:

1. `SPOT_LOG_RETURN_1H`
2. `UM_LOG_RETURN_1H`
3. `SPOT_MINUS_UM_LOG_RETURN_1H`
4. `SPOT_TAKER_IMBALANCE_1H`
5. `UM_TAKER_IMBALANCE_1H`
6. `SPOT_MINUS_UM_TAKER_IMBALANCE_1H`

Features 4-6 are byte/semantically identical to the completed foundation
(`backend/app/predictive/taker_flow_foundation.py`, implementation sha256
`4f633776a96716942bf4b8735395e7a233e59b721b2ea66bdded78d588a81d82`): per market
`(2 * sum(taker_buy_quote_volume) - sum(quote_asset_volume)) / sum(quote_asset_volume)`,
unavailable when the total is <= 0 or non-finite.

No lag, volatility, volume level, basis level, technical indicator, interaction, regime,
funding, OI or other feature. No feature search, pruning or alternative flow transformation.

## Comparison universe

Control and candidate are trained and evaluated on exactly the same instants: the
intersection of rows where every candidate feature and every control feature is available
and the label is UP or DOWN. A coverage difference cannot create apparent incremental skill.
Common-row coverage = common scored rows / label-eligible (UP or DOWN) rows, reported per fold
and pooled.

## Model

Identical for control and candidate, which differ only by features 4-6:

- `StandardScaler`;
- `LogisticRegression(penalty="l2", C=1.0, fit_intercept=True, solver="lbfgs",
  max_iter=2000, tol=1e-8, class_weight=None)`;
- chronological 80% base-fit / 20% calibration within each outer-training set;
- calibration embargo = 2h (2 x horizon), implemented exactly as the frozen foundation
  interpretation: base-fit candidates with `T + 2h` after the first calibration instant are
  dropped;
- training-only Platt calibration on the raw decision score with an unpenalized logistic
  regression (`penalty=None`, same solver, `max_iter`, `tol`).

No second model family, no HGBR, no hyperparameter, calibration-method or model search.

## Folds

Annual outer folds 2021, 2022, 2023, 2024. Each fold trains only on instants whose label end
`T + 1h` is at or before the fold start. No random CV.

## Primary metric

`INCREMENTAL_BRIER = PRICE_ONLY_CONTROL_BRIER - PRICE_PLUS_FLOW_CANDIDATE_BRIER`

pooled over all common outer rows. Positive means the taker-flow features add probability
information beyond contemporaneous price movement. The comparison is paired row by row.

Exactly one primary hypothesis; familywise alpha = 0.05; per-hypothesis alpha = 0.05.

## Inference

- paired fold-stratified moving-block bootstrap of the per-row Brier difference, laid on each
  fold's hourly timeline (an unscored hour keeps its slot);
- block length = 48h;
- 10,000 replicates, drawn in chunks of 500;
- blocks never cross an outer-fold boundary;
- candidate and control losses of one row are always resampled together;
- seed: `numpy.random.default_rng(2026092306)`, one stream, folds in chronological order;
- central 95% percentile interval.

No seed search.

## Secondary diagnostics (never rescue a failure)

- candidate vs control pooled and per-fold log loss;
- candidate and control ROC AUC;
- per-fold incremental Brier;
- per-fold and pooled common-row coverage;
- matched training-up-base-rate constant Brier reference (UP share of the fold's common
  outer-training rows);
- candidate reliability table (ten equal-width bins);
- the EXP-PRED-V2-005 1h flow-only result as a locked historical reference only. It is not a
  competing configuration, not part of model selection and may not select features,
  transformations or thresholds.

## Qualification

`INCREMENTAL_TAKER_FLOW_SUPPORTED_1H` only if all hold:

1. pooled common-row coverage >= 0.95;
2. every fold common-row coverage >= 0.90;
3. pooled `INCREMENTAL_BRIER > 0`;
4. lower bound of the paired 95% bootstrap interval of `INCREMENTAL_BRIER > 0`;
5. at least 3 of 4 folds have `INCREMENTAL_BRIER >= 0`;
6. candidate pooled log loss <= matched price-only control pooled log loss;
7. candidate pooled Brier <= matched training-up-base-rate constant Brier;
8. the pre-execution power gate has passed and been reviewed by the Research Director.

Otherwise `INCREMENTAL_TAKER_FLOW_NOT_SUPPORTED_1H`, or `POWER_BLOCKED_NOT_EXECUTED` when the
power gate does not pass. A positive result does not authorize a trading strategy, a sealed
query, a Champion or a product-horizon change.

## Pre-execution power gate (frozen, not yet computed)

`MDE_IS_ANALOG_EXPECTED_DETECTABILITY_NOT_REALIZED_INCREMENTAL_VARIANCE`

The gate estimates expected detectability under an explicitly frozen analogous dependence and
noise assumption. It does not estimate the variance of the future contrast
`PRICE_ONLY_CONTROL - PRICE_PLUS_FLOW_CANDIDATE`, whose predictions do not exist and must not be
computed by the gate.

- metric: absolute paired Brier improvement (`INCREMENTAL_BRIER`);
- MESI = 0.00020 (a predictive-information threshold, not an economic claim; never lowered if
  the gate blocks);
- proxy classification: `ANALOG_DEPENDENCE_AND_VARIANCE_PROXY`;
- proxy series: the already exposed EXP-PRED-V2-005 1h per-row paired Brier differences
  `FLOW_ONLY_BRIER_LOSS - TRAINING_BASE_RATE_CONSTANT_BRIER_LOSS`, on the existing eligible 1h
  foundation rows, rebuilt by exact deterministic replay of the frozen foundation code (any
  mismatch with the committed result fails closed);
- annual folds 2021-2024 preserved; moving-block bootstrap on each fold's hourly timeline,
  block length 48h, blocks never cross a fold boundary, 10,000 replicates, chunks of 500,
  seed `numpy.random.default_rng(2026092307)`;
- empirical noise distribution `D0`: the replicate pooled statistics minus the observed
  pooled proxy mean (centred on zero);
- alpha = 0.05, central confidence mass 0.95, target power 0.80;
- expected power at additive effect `delta`:
  `power(delta) = mean over d in D0 of [delta + d + quantile_0.025(D0) > 0]`,
  i.e. the probability that the lower bound of the central 95% percentile interval is above
  zero when the true pooled incremental improvement is `delta`;
- expected power at MESI = `power(0.00020)`;
- empirical MDE = the smallest `delta` on the grid `k * 1e-7`, `k = 0, 1, ..., 100000`, with
  `power(delta) >= 0.80`; if none, the MDE is reported as not reached;
- classification: `ANALOG_POWER_GATE_PASSES_PENDING_RESEARCH_DIRECTOR_REVIEW` if
  `power(MESI) >= 0.80`, otherwise `POWER_BLOCKED_NOT_EXECUTED`; the gate records
  `POWER_GATE_FAILED_CLOSED` if the proxy cannot be reconstructed exactly;
- forbidden inputs: any price-only or price-plus-flow prediction, any EXP-PRED-V2-006 fit,
  any observed incremental effect, post-cutoff or sealed data.

Seeds are fixed and distinct: foundation family `20260923`, power gate `2026092307`,
EXP-PRED-V2-006 inference `2026092306`. None may change after a result.

Even a passing gate does not authorize EXP-PRED-V2-006; Research Director review is mandatory.

## Boundaries

No horizon change, extra lags, alternative imbalance definitions, nonlinear models,
hand-built regimes, threshold sweeps, extra features, trading PnL, costs, magnitude, sealed
data, Champion or real money.
