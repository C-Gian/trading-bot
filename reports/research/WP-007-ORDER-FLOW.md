# WP-007 — Aggressive buy-flow transition

DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE. Champion NONE. No sealed
query was executed. All six folds are previously exposed development history.

## Feature integrity and semantics

The accepted canonical BTCUSDT 1m identity remained unchanged. All 3,870,559 rows
passed finite/nonnegative taker-field checks; `taker_base <= volume` and
`taker_quote <= quote_volume` held under the frozen tolerance without clamping.
The deterministic timestamp-only raw Binance sample compared 21,632 rows across every
available calendar quarter and both known off-grid intervals with zero mismatches.

`BTCUSDT-SPOT-ORDERFLOW-DEV-v1` contains 64,135 eligible 1h buckets and 16,008
eligible 4h buckets. Production aggregation and the independent oracle reconcile at
content hash `d16a5e18d19a9fe30a58ce24999d001d11bf3168d59703b8afd09552632464e5`.
Buckets use the ratio of summed taker-buy base volume to summed total base volume;
incomplete and quarantined buckets are ineligible and missing minutes remain unfilled.

The feature is Binance's exchange-reported taker-buy base asset volume share: a proxy
for aggressive buy-side participation on that venue. It is not complete market-wide
order flow, investor intent, cross-exchange signed demand, or causal evidence.

## Frozen family and chronology

SEARCH_MEMORY_V2 admitted FLOW_CORE as `NEW_FAMILY` under `FAM-ORDER-FLOW` and
FLOW_PRICE_RESPONSE as `DESCENDANT_MECHANISM_CHANGE` before results. The classifier
was not weakened, no condition was added to force novelty, and prior budgets were not
reset. The exact 0.5 accounting balance point, non-overlapping 4h context, 2% stop,
4% target, 1,440-minute horizon, and four profiles per variant were fixed with zero
parameter search.

FLOW_CORE emits LONG only when the previous completed 1h share is <=0.5, current
completed 1h share is >0.5, and the most recent completed UTC 4h bucket closing at or
before the current signal hour opens is >0.5. FLOW_PRICE_RESPONSE adds only
`current_completed_1h_close > current_completed_1h_open`.

Two tooling defects were found before market evaluation. The first wrote no
preregistration; the second occurred after the original preregistrations were committed
but before any market array or trial was loaded. Both are recorded as zero-result
corrections. The original preregistrations are preserved and effective v2 declarations
were committed before the result run; scientific scope and executable behavior did not
change.

## Results — DEVELOPMENT_EVALUATION_V1 unchanged

| | FLOW_CORE | FLOW_PRICE_RESPONSE |
|---|---:|---:|
| Terminal classification | **REJECT_COST_DOMINATED** | **REJECT_COST_DOMINATED** |
| Default net expectancy R | -0.0667167056 | -0.0505303537 |
| Zero-cost net expectancy R | +0.0533577522 | +0.0695709705 |
| Double-cost net expectancy R | -0.1867911419 | -0.1706316500 |
| DELAY_1H net expectancy R | -0.0619009982 | -0.0504141518 |
| Resolved trades | 1828 | 1565 |
| Invalid / unresolved | 1 / 11 | 0 / 7 |
| Nonnegative folds | 1/6 | 2/6 |
| Minimum fold trades | 241 | 204 |
| Trade ESS | 1630.92 | 1331.60 |
| Positive-fold profit concentration | 100.00% | 63.34% |

CORE folds: 2019:395 (-0.0730669766 R), 2020:246 (-0.0408817800 R), 2021:320 (-0.1185235089 R), 2022:321 (-0.1201543643 R), 2023:241 (+0.0001895828 R), 2024:305 (-0.0216012451 R).

PRICE_RESPONSE folds: 2019:330 (-0.0782813188 R), 2020:204 (+0.0109533855 R), 2021:254 (-0.0958586631 R), 2022:284 (-0.1040867905 R), 2023:220 (+0.0175494960 R), 2024:273 (-0.0199040260 R).

Both rules have positive zero-cost expectancy, but default friction consumes the
signal and doubled costs deepen the loss. CORE is positive in only one fold, by just
+0.0001895828 R, so its positive-fold concentration is 100%. Evidence is much more
frequent than ALIGNED, but not more evenly profitable. PRICE_RESPONSE removes 263
trades and improves default expectancy by +0.0161863519 R, yet remains
cost-dominated. DELAY_1H improves CORE by only +0.0048157074 R and leaves it negative;
the event is not rescued by a one-hour lag.

## Descriptive preserved-reference comparison

These are not paired comparisons; each reference retains its own eligibility and
occupancy semantics.

| Reference | Default expectancy R | CORE delta R |
|---|---:|---:|
| Random control mean | -0.0967774607 | +0.0300607551 |
| SMA trend | -0.1081210229 | +0.0414043173 |
| Breakout | -0.0535976983 | -0.0131190073 |
| ALIGNED | +0.1373934676 | -0.2041101732 |
| Pullback recovery core | +0.0003823075 | -0.0670990131 |
| No-trade | zero trades | not comparable |

The new mechanism is structurally distinct in information source and entry rule, but
its development economics do not survive realistic friction. The preselected CORE
sets the family conclusion: **REJECT_COST_DOMINATED**. The less-negative confirmation
variant does not replace it.

## Accounting and disposition

One economic hypothesis, two configurations, eight profile evaluations, zero numeric
variants, one adaptive decision, and one result-dependent fork were consumed.
Cumulatively: 5 hypotheses, 13 configurations, 69 profile/seed trials, 0 numeric
variants, 4 adaptive decisions, and 4 result-dependent forks.

FAM-ORDER-FLOW is parked as cost-dominated. FAM-BREAKOUT remains exhausted;
FAM-PULLBACK-RECOVERY and ALIGNED remain parked. No sealed query, paper trade,
Champion, forward evidence, or real-money authorization follows.
