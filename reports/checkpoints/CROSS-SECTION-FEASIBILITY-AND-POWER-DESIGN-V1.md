# Cross-section feasibility and power design V1

Status: COMPLETED_NEGATIVE_FEASIBILITY_PENDING_RESEARCH_DIRECTOR_REVIEW

Starting HEAD: `2fa562877c2efd4bd022c157b0a6f38212df1380` on local `main`.
Universe-policy freeze commit: `cb13309b0e42a87fb139066efc4a9ef89db0dc14`.

`ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1` is one future material economic/informational
hypothesis, not one per asset. It remains `DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED`. The
true (zero-alignment) pooled ALIGNED effect, its t statistic, its p value and every
per-asset real effect were never computed; the estimator refuses shift zero by
construction.

## Data source

Official Binance public **spot monthly 1h kline** archives, no credentials, with current
`exchangeInfo` never used as historical listing truth. 3,710 archive symbols, 735
USDT-quoted, 52 removed by the mechanical leveraged-token suffix rule, 683 candidates,
486 with in-window monthly evidence, 17,925 preserved objects (0.53 GiB compressed),
12,886,210 on-grid hourly rows. No multi-asset 1m history was downloaded.
`DATA_FEASIBILITY_STATUS = PASS`.

Direct 1h reproduces the frozen ALIGNED semantics on BTCUSDT against the canonical 1m
substrate: identical in-window hour key set (52,549), **49,034 of 49,034 identical
decisions** and **195 of 195 identical raw signals**. `DATA_SOURCE_STATUS = PASS`.

25 of 262,655 compared bar fields (0 open, 0 close, 1 high, 1 low, 23 volume) differ
between Binance's own 1m and 1h serializations of the same market. None changed an
ALIGNED gate; all are preserved verbatim in the equivalence artifact as an upstream
source property, not an aggregation error.

## Universe and signal support

The policy was frozen in `cb13309` **before** any cross-sectional signal existed. 387
eligible assets across 390 instrument epochs, 2,556,366 decision rows, **3,380 raw
ALIGNED events** with no occupancy suppression, in **259 asset clusters** and **184 UTC
week clusters**. Assets whose archive ends before 2024-12 are retained historically and
do contribute events. `UNIVERSE_FEASIBILITY_STATUS`, `SURVIVORSHIP_STATUS` and
`CLUSTER_SUPPORT_STATUS` all `PASS`.

A vectorized ALIGNED evaluator was used for the 2.5M-row scan and is verified identical
to the frozen `FeatureSource` engine on real and synthetic series.

## Inference and power

The two-way asset/decision-time within transform is exact (residual factor means
2.4e-17 and 2.1e-17 relative), and every replicate's Cameron-Gelbach-Miller covariance is
positive semidefinite. `DEPENDENCE_INFERENCE_STATUS = PASS`.

**Both remaining gates fail.**

`PLACEBO_CALIBRATION_STATUS = REDESIGN_REQUIRED`. Across 338 non-zero circular-shift
replicates the frozen test rejects 12 times at `alpha = 0.05 / 13` against 1.3 expected:
empirical size **3.55%** versus nominal **0.385%**, a **9.2x** size inflation, exact
binomial `p = 1.26e-8`. The analytic cluster standard error (12.68 bps) also understates
the empirical placebo dispersion (16.73 bps) by 32%. The placebo did exactly what it was
designed to do: it invalidated the proposed inference rather than rescuing it.

Prospective power at the frozen threshold:

| quantity | value |
| --- | --- |
| MESI | 24.0 bps/event |
| effective alpha | 0.0038461538 (0.05 / 13, one-sided) |
| degrees of freedom | 183 |
| design standard error | 12.680466 bps |
| empirical MDE | 44.872236 bps/event |
| **power at MESI** | **0.2117** |
| target power | 0.80 |

`CROSS_SECTION_POWER_GATE_STATUS = REDESIGN_REQUIRED`.

## Recorded limitations

Two limitations are reported rather than repaired, because repairing either would be the
post-hoc search this checkpoint forbids.

1. The frozen placebo keeps one absolute position displacement for every asset and drops
   no asset, so displacement is bounded by the shortest participating history (336
   positions). The 338 replicates overlap heavily and are not independent draws.
2. An identical position displacement maps to different calendar offsets across assets,
   so contemporaneous cross-asset synchrony is only partially preserved; the
   decision-time fixed effect absorbs the market-wide component the placebo cannot
   reproduce exactly.

Both argue for a Research-Director-level redesign of the inference, not an executor-level
adjustment.

## What was not done

No MESI, power target, universe threshold, liquidity cutoff, horizon or ALIGNED parameter
was changed in response to the result. No second universe threshold was tried. No
high-signal asset selection, category removal or per-asset rescue occurred. No sealed
data was queried and no post-cutoff market data entered development.

## Product and accounting

Product remains `BTCUSDT_SPOT_V1`; the cross-section is
`SCIENTIFIC_GENERALIZATION_ONLY`. `cross_section_product_authorized = false`, no
multi-asset trading, Analyze Market surface, order path, paper position or allocation
logic exists for any other asset.

Completed experiments remain 26, known observed material economic hypotheses remain 12,
sealed queries remain 0, Champion remains `NONE`, genuine completed paper trades remain
0, and real money remains false. The cross-sectional experiment would consume the 13th
observed material hypothesis only on a future authorized zero-alignment execution.

Next action: RESEARCH DIRECTOR REVIEW.
