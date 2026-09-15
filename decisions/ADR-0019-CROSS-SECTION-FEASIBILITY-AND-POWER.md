# ADR-0019 — the frozen cross-sectional design is placebo-invalidated and power-blocked

Status: ACCEPTED NEGATIVE FEASIBILITY RESULT. Date: 2026-09-16. Checkpoint:
`CROSS-SECTION-FEASIBILITY-AND-POWER-DESIGN-V1`.

## Context

`RESEARCH_ARCHITECTURE_SYNTHESIS_V2` allocated the primary research direction to
`CROSS_SECTIONAL_FEASIBILITY_AND_POWER_DESIGN`, on the reasoning that BTC-only ALIGNED
persistence is severely power-limited while a properly frozen cross-sectional study can
test one common economic mechanism using more information.

This checkpoint froze that study — `ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1` — and then
measured whether it could resolve its own preregistered MESI without ever inspecting the
true cross-sectional effect.

## What was built

The universe policy, eligibility rules, outcome, estimand, threshold, inference, placebo
rule and power target were committed in `cb13309` **before** any cross-sectional ALIGNED
signal was generated, so the freeze ordering is provable from git history.

Official Binance spot monthly 1h kline archives supplied the substrate: 3,710 archive
symbols, 735 USDT-quoted, 52 removed by the mechanical leveraged-token suffix rule, 683
candidates, 486 with in-window evidence, 17,925 preserved monthly objects, 12,886,210
on-grid hourly rows. Direct 1h data reproduced the frozen ALIGNED semantics on BTCUSDT
exactly against the canonical 1m substrate (49,034 of 49,034 identical decisions, 195 of
195 identical raw signals), so `DATA_SOURCE_STATUS = PASS`.

Causal eligibility admitted 387 assets across 390 instrument epochs, 2,556,366 decision
rows and 3,380 raw ALIGNED events in 259 asset clusters and 184 UTC week clusters, so
`UNIVERSE_FEASIBILITY_STATUS`, `DATA_FEASIBILITY_STATUS`, `SURVIVORSHIP_STATUS`,
`CLUSTER_SUPPORT_STATUS` and `DEPENDENCE_INFERENCE_STATUS` all pass.

## Result

`CROSS_SECTION_POWER_GATE_STATUS = REDESIGN_REQUIRED` on two independent grounds.

1. **The placebo invalidates the frozen inference.** Across 338 non-zero circular-shift
   replicates the two-way asset/week clustered test rejected 12 times at the governed
   `alpha = 0.05 / 13`, against 1.3 expected: empirical size 3.55% versus a nominal
   0.385%, a 9.2x inflation with exact binomial `p = 1.26e-8`. The analytic cluster
   standard error (12.68 bps) also understates the empirical placebo dispersion
   (16.73 bps) by 32%. `PLACEBO_CALIBRATION_STATUS = REDESIGN_REQUIRED`.

2. **The design cannot resolve its own MESI.** At the frozen `MESI = 24.0 bps/event` the
   prospective power is `0.2117` against a target of `0.80`, with an MDE of
   `44.87 bps/event` — roughly 1.9x the economically necessary lower bound.

Neither failure is evidence about cryptocurrency markets. The true pooled beta, its t
statistic, its p value and every per-asset real effect remain uncomputed, and the
estimator refuses shift zero by construction.

## Decision and consequences

Stop and return to the Research Director. Do not lower MESI or the power target, select
high-signal assets, remove categories, alter ALIGNED, inspect the real beta, test a second
universe threshold, add another liquidity cutoff, or move to another horizon.

Accounting is untouched: 26 completed experiments, 12 known observed material economic
hypotheses, 0 sealed queries, Champion `NONE`, real money false. The hypothesis stays
`DESIGNED_NOT_PREREGISTERED_NOT_EXECUTED` and would become the 13th observed material
hypothesis only if a future Research Director authorizes its zero-alignment execution.

The product universe remains `BTCUSDT_SPOT_V1_UNCHANGED`,
`cross_section_product_authorized` is false, no multi-asset trading, Analyze Market
surface, order path or allocation logic exists, and no cross-sectional market outcome has
been observed.

Two limitations are recorded rather than repaired, because repairing either would be the
post-hoc search this checkpoint forbids. First, the frozen placebo keeps one absolute
position displacement for every asset and drops no asset, so displacement is bounded by
the shortest participating history (336 positions); replicates overlap heavily and are
not independent draws. Second, an identical position shift maps to different calendar
offsets across assets, so cross-asset synchrony is only partially preserved. Both are
quantified in the placebo artifact and both argue for a Research-Director-level redesign
of the inference rather than an executor-level adjustment.
