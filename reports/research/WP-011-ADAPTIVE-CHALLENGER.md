# WP-011 adaptive multi-signal challenger

**EXPOSED DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE.**

`FAM-ADAPTIVE-EWLS-MACRO` is **REJECT_COST_DOMINATED**.

## What was tested

WP-008 falsified one thing only: a fixed global linear combination of eight internal
market and order-flow features. It left untested whether *time-varying* weights, *macro*
information, or *recency* weighting would change the answer. WP-011 tests exactly that,
and nothing else.

`EXPONENTIALLY_WEIGHTED_LINEAR_NET_R_V1` fits weighted least squares with intercept. One
model becomes effective at the first UTC hour of each calendar month and is then held
fixed. Every training row weighs `exp(-ln(2) * age_days / 180)` against the effective
instant; scaling uses the weighted mean and population variance under those same weights.
A row enters training only when its signal instant *and* its complete label outcome both
precede `effective - 216h`. The 180-day half-life was frozen before any result and no
alternative was evaluated.

Two configurations, fixed in advance:

- `EWLS_INTERNAL_MACRO` — the eight frozen WP-008 internal features plus eight
  point-in-time ALFRED macro features (16 total). Family primary.
- `EWLS_INTERNAL_ONLY` — the eight internal features alone (8 total). Structural ablation
  that isolates what macro contributed.

## Result

| | DEFAULT | ZERO | DOUBLE | DELAY_1H |
|---|---|---|---|---|
| `EWLS_INTERNAL_MACRO` | **-0.0987513255 R** | +0.0212985363 R | -0.2188011787 R | -0.1081651326 R |
| `EWLS_INTERNAL_ONLY` | -0.0527152557 R | +0.0673267788 R | -0.1727572632 R | -0.0433478423 R |

The primary executed 1,487 trades across the six frozen annual folds, with **0 of 6
nonnegative folds**, a minimum fold of 140 trades, trade ESS 1,353.9 and cumulative
-146.84 R. Every fold is negative: -0.0739, -0.0673, -0.1746, -0.0771, -0.0759, -0.0847.

Gross-of-cost expectancy is barely positive (ZERO +0.0213 R) and turns clearly negative
once realistic costs apply, which is precisely the `REJECT_COST_DOMINATED` signature.
Doubling costs roughly doubles the loss. Delaying the signal by an hour changes little,
so the result is not a fragile timing artifact — there is simply no cost-surviving edge.

Out-of-sample prediction/label Pearson correlation is +0.0275 pooled, and it decays
through time: +0.106 (2019), +0.002 (2020), +0.032 (2021), -0.041 (2022), -0.090 (2023),
-0.050 (2024).

## Did macro help?

**No. It made things materially worse.**

- DEFAULT expectancy fell by **-0.0460 R per trade** when macro was added
  (-0.0988 vs -0.0527).
- Fold stability fell from 2 of 6 nonnegative to **0 of 6**.
- Cost robustness fell: DOUBLE -0.2188 vs -0.1728.
- The pooled correlation barely moved (+0.0275 vs +0.0243), so macro bought no real
  predictive content while roughly doubling the trade count from 814 to 1,487.

The mechanism is visible in the coefficients. The macro block absorbed **69.7% of the
mean absolute standardized coefficient mass** (range 41.2%–89.4%), crowding out market
price (16.4%), volatility/liquidity (8.4%) and order flow (5.5%). That weight was not
predictive: it mostly widened the set of hours the model called positive.

## Did time-varying weighting beat the fixed WP-008 architecture?

Marginally, and not enough to matter. WP-008 `LINEAR_FULL` scored -0.1142 R on 1,003
trades; the adaptive primary scored -0.0988 R on 1,487 trades. Both are
`REJECT_COST_DOMINATED`, and the trade sets are not paired. The adaptive *internal-only*
configuration (-0.0527 R) is the best of the three, which suggests recency weighting
helped a little while macro hurt more — but it is still negative and classified
`INCONCLUSIVE`, so nothing here is an edge.

## Were the macro coefficients interpretable?

Not stably. Sign stability across the 71 monthly fits is poor for most macro terms:
`T10Y2Y_LEVEL` 0.61, `NFCI_LEVEL` 0.61, `WALCL_LOG_CHANGE_28D` 0.55, `DFF_LEVEL` 0.65,
`UNRATE_LEVEL` 0.70. Coefficients that flip sign in a third of months are fitting noise,
not a stable economic relationship. The most sign-stable term is
`TAKER_BUY_SHARE_4H_CENTERED` at 0.93 — but it carries only about 5% of the mass.

## What this does and does not falsify

Falsified: that a prospectively fixed 180-day recency-weighted linear combination of
these eight internal features and these eight point-in-time macro features, refitted
monthly, selects BTCUSDT long opportunities with robust positive net expectancy after
realistic costs.

Not falsified: other half-lives, other update cadences, non-linear models, interaction
terms, different macro series, news or sentiment families, different labels, thresholds,
exits, horizons, assets, and any prospective forward evidence. The Owner's broader
multi-signal thesis is untouched by this single rejection — but the specific claim that
*point-in-time macro context adds predictive value inside a linear adaptive model* now
has direct negative evidence against it.

## Governance

Admission, allocation and both preregistrations were committed before any validation hour
was evaluated. Champion remains NONE, sealed queries 0, paper trades 0, real money false.
No result was used to alter the experiment, and the V1 paper-research product surface is
untouched by this checkpoint.
