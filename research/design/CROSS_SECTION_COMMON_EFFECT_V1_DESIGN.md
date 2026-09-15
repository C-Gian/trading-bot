# CROSS_SECTION_COMMON_EFFECT_V1 — design and power preparation

Status: FROZEN DESIGN, NOT PREREGISTERED, NOT EXECUTED.

This document freezes one future material economic/informational hypothesis. It does not
authorize execution, does not observe any cross-sectional ALIGNED effect, does not change
`ALIGNED_PARTICIPATION_CONTINUATION_V1`, and does not change the BTCUSDT spot V1 product.

## 1 — Scientific question

`ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1`

> Across a frozen point-in-time Binance Spot USDT universe, do the unchanged ALIGNED
> gates identify asset-hours with a positive common 24-hour forward effect beyond
> contemporaneous market/time and asset effects?

This is **one** hypothesis, not one per asset. If a future Research Director authorizes
its zero-alignment execution it becomes the 13th observed material economic hypothesis.
During this preparation the observed family remains 12.

## 2 — Product boundary

Product remains `BTCUSDT_SPOT_V1`. The cross-section is
`SCIENTIFIC_GENERALIZATION_ONLY`. No multi-asset trading, no multi-asset Analyze Market,
no orders, paper positions or allocation logic for other assets.
`cross_section_product_authorized = false`; `real_money_authorized = false`.

## 3 — Development window and source

Development information is restricted to `2019-01-01T00:00:00Z` through
`2024-12-31T23:59:00Z`. Listing the official archive today only enumerates which
historical objects exist; every admitted object carries a month partition inside the
window, so no post-cutoff market information can determine eligibility, performance or
signal outcomes.

Primary source: the official Binance public **spot monthly 1h kline archive**
(`data/spot/monthly/klines/<SYMBOL>/1h/`). 1h is chosen because the ALIGNED decision
engine consumes completed hourly bars and derived 4h context. Current `exchangeInfo` is
never used as historical listing truth. No credentials are used.

Raw objects are preserved verbatim with their URL, month, SHA-256, first/last timestamp,
row count, quote asset and availability status in
`data/manifests/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.json`.

### 3.1 Source equivalence requirement

Before direct 1h bars may be relied on, `BTCUSDT` direct-1h must reproduce the frozen
ALIGNED semantics against the canonical project 1m substrate: identical in-window hour
key set, identical ALIGNED gate outputs on every commonly decidable hour, and identical
raw signal counts. The result is recorded in
`reports/cross_section/CROSS-SECTION-BTC-1H-EQUIVALENCE-V1.json`. Failure sets
`DATA_SOURCE_STATUS = REDESIGN_REQUIRED` and stops the checkpoint.

## 4 — Point-in-time universe policy (frozen before any signal count)

Universe = every Binance spot symbol with `USDT` quote for which official monthly 1h
archive evidence exists inside the development window. The universe is derived from
archive evidence, never from today's surviving symbol list, and survival to 2024 is never
required.

The single exclusion rule is mechanical and frozen: a symbol is excluded when one of the
suffixes `UP`, `DOWN`, `BULL`, `BEAR` appears immediately before `USDT`. The rule is
applied to the symbol string alone so that no discretionary winner/loser list can enter
the universe. Its literal application also removes a small number of symbols whose base
asset merely ends in those letters; those symbols are enumerated in the survivorship
audit as a known, frozen, non-discretionary cost of refusing discretion.

Stablecoin-like and fiat-like pairs are **not** manually removed in V1. A semantic
universe refinement would be a new design decision.

No asset is selected using future return, ALIGNED performance or future signal count.

## 5 — Causal eligibility (frozen)

At decision hour `t` an asset is eligible only from information completed before `t`:

- minimum completed archive history before eligibility: **30 complete UTC days**;
- liquidity lookback: **30 completed UTC days**;
- minimum trailing median **daily quote volume: 10,000,000 USDT**.

Rationale: a planning order notional of about 5,000 USDT is at most about 0.05% of median
daily quote turnover. This is a capacity and data-quality eligibility rule. It is not a
performance optimization and authorizes no capital.

A day contributes to the liquidity median only when all 24 of its hours are present, so
partial days can never inflate the trailing median. Canonical gaps are never interpolated.
An asset that later delists stays historically eligible until its causal eligibility
ceases; future longevity is never an eligibility condition.

## 6 — Frozen ALIGNED transfer

`ALIGNED_PARTICIPATION_CONTINUATION_V1` is used unmodified, per asset, with exactly:

- prior-high breakout lookback over the 24 completed hours before the latest completed hour;
- 43 completed 4h context bars giving 42 increments, with `up >= 2 * down`;
- prior 24h mean volume reference with a 2x participation threshold.

No parameter is scaled by volatility, asset, market cap, liquidity, price or year, and no
asset-specific tuning occurs. That invariance is the point of the replication.

The study generates **raw signal events**. One-position-at-a-time occupancy suppression is
deliberately not imposed.

## 7 — Future primary outcome (frozen, not evaluated here)

24-hour forward log-price return in basis points.

- start: the next completed tradable hourly open at or after the decision boundary;
- terminal: the latest legitimately observed tradable close at or before exactly +24h;
- a missing terminal price is never interpolated;
- if trading permanently terminates inside the interval the last legitimate tradable price
  is used rather than dropping the event because it later delisted.

No stop, no target, no R denominator, no one-position constraint. This is an
information/generalization study.

## 8 — Pooled primary estimand (exactly one)

    Y(i,t) = alpha_i + gamma_t + beta * ALIGNED_SIGNAL(i,t) + e(i,t)

with `Y` the frozen 24h forward return in price bps, `alpha_i` an asset fixed effect and
`gamma_t` a decision-time fixed effect. `beta` measures common relative forward
performance associated with ALIGNED after removing persistent asset-level differences and
contemporaneous market-wide decision-time effects. The future primary claim is `beta > 0`,
in bps per ALIGNED signal event.

`beta` is **not** computed at the true unshifted alignment in this checkpoint. No per-asset
beta may ever be a primary or a rescue condition; per-asset results, if ever reported, are
descriptive diagnostics that may never select winners.

## 9 — Economic threshold

`CROSS_SECTION_MESI_BPS = 24.0`, reusing the already-governed informational lower bound
`500 bps/year / (125 ALIGNED trades / 6 years) = 24 bps/event`.

A +24 bps common informational effect is a **necessary lower bound** for relevance to the
BTC product at approximately historical ALIGNED cadence. It is not sufficient to claim a
+5% product return, profitable multi-asset execution, or BTC validation. MESI is not
lowered after seeing power.

## 10 — Dependence and inference

24h forward outcomes overlap and crypto assets share market shocks, so IID inference is
forbidden. The future pooled `beta` uses deterministic **two-way clustered** inference:

- cluster dimension 1: asset / instrument epoch;
- cluster dimension 2: UTC calendar week of the decision time.

Asset clustering permits arbitrary serial dependence within an asset; week clustering
captures contemporaneous cross-asset dependence and the overlap of nearby 24h outcomes.
The covariance uses the standard inclusion/exclusion intersection correction
`V = V_asset + V_week - V_intersection`, with the finite-sample correction and the exact
estimator implementation recorded in the power-gate artifact. Reference degrees of freedom
use the conservative smaller cluster dimension minus one.

Inferential-support prerequisites, not performance filters:

- at least **30** distinct asset clusters contributing ALIGNED events;
- at least **100** UTC week clusters containing at least one ALIGNED event.

Failure sets `CLUSTER_SUPPORT_STATUS = REDESIGN_REQUIRED`. Assets are never added manually
to make them pass.

## 11 — Prospective multiplicity

Known observed material family before execution: 12. On execution: 13. Design and power
use `alpha_effective = 0.05 / 13`, one-sided positive. `UNQUANTIFIED_PRE_REPO_EXPOSURE`
remains `true`; no numeric count is invented for unknown historical search.

## 12 — Matched placebo calibration

The primary inferential design is the pooled two-way-FE / two-way-cluster model. A
deterministic **non-zero** timing placebo checks that this inference is not
anti-conservative. Shift zero is never used.

Each asset keeps its frozen raw ALIGNED binary sequence and event clustering; the sequence
is circularly shifted inside that asset's causally eligible history, using the same shift
magnitude across assets wherever structurally possible, and excluding any shift closer than
168 eligible hourly positions to zero. Only the placebo pooled statistic is computed.

Recorded: placebo count, event-count retention, within-asset cluster preservation,
cross-asset synchrony distortion, and empirical upper-tail calibration. The placebo is a
calibration diagnostic. It may invalidate the inferential method; it may never rescue
insufficient power. If the shift mechanism materially destroys cross-asset synchrony, that
limitation is reported and the gate fails closed rather than pretending exactness. No
search is performed for a placebo construction that yields a favourable power result.

## 13 — Power without real-effect exposure

The preparation may use the 24h panel to estimate noise and dependence only. Permitted:
fixed-effects null residual estimation without the ALIGNED regressor, residual dispersion,
two-way cluster covariance ingredients, non-zero placebo effects, and synthetic injected
effects. Forbidden: zero-alignment beta, t, p, and any per-asset real effect.

Prospective quantities: `power_target = 0.80`, `power_at_MESI`,
`minimum_detectable_effect_bps`, under the frozen cluster-aware design, validated where
practical by deterministic synthetic injection of known beta (0, 12, 24, 48, 96 bps) into
the null/residual process. Synthetic effects are calibration only and are never observed
market effects.

## 14 — Power gate

`CROSS_SECTION_POWER_GATE_STATUS = READY_FOR_PREREGISTRATION` requires all of:
`DATA_SOURCE_STATUS`, `UNIVERSE_FEASIBILITY_STATUS`, `DATA_FEASIBILITY_STATUS`,
`SURVIVORSHIP_STATUS`, `CLUSTER_SUPPORT_STATUS`, `PLACEBO_CALIBRATION_STATUS` and
`DEPENDENCE_INFERENCE_STATUS` equal to `PASS`, plus `power_at_MESI >= 0.80` and numerical
resolution sufficient for `alpha_effective`. Otherwise the status is
`REDESIGN_REQUIRED`.

On `REDESIGN_REQUIRED` the executor may not lower MESI or target power, select
high-signal assets, remove categories, alter ALIGNED, inspect the real beta, test a second
universe threshold, add another liquidity cutoff, or move to another horizon. It returns to
the Research Director.
