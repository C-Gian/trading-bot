# Predictive macro release-state contract V1

Status: frozen before any `PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1` source result, model fit
or outer-fold prediction.

This contract governs the one prospective source-semantics remediation authorized for the
ALFRED macro information family inside `PREDICTIVE_RESEARCH_GENERATION_V1`. It admits exactly
the same hash-pinned substrate as
[`PREDICTIVE_MACRO_VINTAGE_CONTEXT_V1`](PREDICTIVE_MACRO_VINTAGE_CONTEXT_V1.md) and references
[`POINT_IN_TIME_EXOGENOUS_DATA_V1`](POINT_IN_TIME_EXOGENOUS_DATA_V1.md). It alters neither of
them, and it does not reclassify the source block they governed. The BTCUSDT target, 24h
terminal horizon, labels, folds, scorer, controls and baselines remain those of the canonical
predictive evaluation contract Amendment A1.

## Why a second source semantics exists

`PREDICTIVE-STAGE3-MACRO-VINTAGE-V1` enforced point-in-time availability correctly and is
preserved unchanged. Its per-decision freshness rule, however, applied one concept of
staleness to every frequency: it compared the *observation period date* of the latest
available release with the BTC decision date and rejected a monthly release once that gap
exceeded a fixed number of days. CPI is published weeks after the month it describes, so the
genuinely latest-known release became mechanically "stale" for most of every month even
though no newer release existed anywhere. The source audit counted 55,342
`CPIAUCSL_CURRENT_ANCHOR_UNAVAILABLE_OR_STALE` failures and the family was blocked at
10.72%-13.73% fold coverage, before any BTC return or prediction was read.

This contract therefore separates two ideas the predecessor conflated:

- **state persistence** - the last value actually published and available at `T` is the
  market's current known macro state, and it stays current until a later release becomes
  available;
- **interpolation or backfill** - inventing, forward-dating or importing a value that was not
  available at `T`, which remains forbidden here exactly as before.

State persistence is not imputation. Nothing is invented: the persisted number is a real
release that a market participant standing at `T` had already seen.

## Source identity and availability

- Manifest: `data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json`, manifest id
  `ALFRED-MACRO-CONTEXT-DEV-v1`.
- Canonical artifact: `data/derived/ALFRED-macro-context-v1.parquet`, file SHA-256
  `448f1ea80252ce5fbc7f1982c41540dc71852c3a4e2fbf1a1357fd1ed9c877dd`.
- Catalog: `research/exogenous/ALFRED_SERIES_CATALOG_V1.json`, SHA-256
  `cfc08c40c669770a144210026b81326379e50e7d61e770d3d4b40baf5e94b8b1`.
- Exact series, in frozen order: `DFF`, `DGS10`, `T10Y2Y`, `VIXCLS`, `NFCI`, `WALCL`,
  `CPIAUCSL`, `UNRATE`.
- Availability rule `NEXT_CALENDAR_DAY_00_00_UTC_AFTER_VINTAGE_START`: a vintage state becomes
  usable at `00:00:00Z` on the calendar day after `vintage_start`, and a record enters a
  decision at `T` only when `availability_time <= T`.
- Current-revised FRED substitution, post-2024 vintages, interpolation, forward filling of a
  *missing* observation into a *new* observation date, nearest-future lookup and missing-value
  imputation remain forbidden.

## Release-state semantics at decision time `T`

For each series, reconstruct the complete as-of-`T` snapshot from records whose
`availability_time <= T`, keeping for every observation date only its latest vintage state
available by `T`. Then:

- the **current known level** is the value belonging to the greatest observation date present
  in that snapshot;
- that level persists causally until a newer observation date enters a later snapshot;
- a current level is never rejected because its observation period date is older than some
  fixed number of days relative to `T`;
- no value is interpolated, nearest-future substituted, or taken from a later revision.

A later vintage can therefore change only decisions at or after its own availability boundary.
Every anchor of a single feature vector is read from one and the same as-of-`T` snapshot.

## Source-cadence integrity audit

Persistence must not be allowed to hide a silently frozen or truncated source. Before any BTC
outcome is read, the audit walks the sequence of observation dates actually represented in the
point-in-time substrate and requires no gap larger than:

- 10 calendar days for daily and business-daily series (`DFF`, `DGS10`, `T10Y2Y`, `VIXCLS`);
- 21 calendar days for weekly series (`NFCI`, `WALCL`);
- 70 calendar days for monthly series (`CPIAUCSL`, `UNRATE`).

A violation blocks the checkpoint with
`BLOCKED_MACRO_RELEASE_STATE_SOURCE_INTEGRITY_V1` and no model is fitted.

These limits are source-integrity limits on the release calendar. They are explicitly **not**
per-decision expiry rules on a current value, and they are never applied to the gap between
`T` and the current observation date.

## Frozen feature vector

`PREDICTIVE_MACRO_VINTAGE_FEATURES_V2` contains exactly the same thirteen economic quantities,
in the same order, as `PREDICTIVE_MACRO_VINTAGE_FEATURES_V1`. Only the current-state semantics
above differ.

1. `DFF_LEVEL`
2. `DFF_DELTA_30D`
3. `DGS10_LEVEL`
4. `DGS10_DELTA_30D`
5. `T10Y2Y_LEVEL`
6. `T10Y2Y_DELTA_30D`
7. `LOG_VIX_LEVEL`
8. `VIX_LOG_CHANGE_5D`
9. `NFCI_LEVEL`
10. `NFCI_DELTA_28D`
11. `WALCL_LOG_CHANGE_28D`
12. `CPI_YOY_LOG_CHANGE`
13. `UNRATE_DELTA_3M`

Historical anchors, all resolved inside the same as-of-`T` snapshot:

- `DFF`, `DGS10`, `T10Y2Y` 30-day anchors: the latest observation on or before
  `T_date - 30 days`, and invalid when more than 7 calendar days earlier than that intended
  anchor;
- `VIXCLS` 5-day anchor: the latest observation on or before `T_date - 5 days`, invalid beyond
  7 calendar days;
- `NFCI`, `WALCL` 28-day anchors: the latest observation on or before `T_date - 28 days`,
  invalid beyond 14 calendar days;
- `CPI_YOY_LOG_CHANGE`: take the current known CPI observation date and require the
  observation exactly 12 calendar months earlier to exist in the same snapshot;
- `UNRATE_DELTA_3M`: take the current known unemployment observation date and require the
  observation exactly 3 calendar months earlier to exist in the same snapshot.

The historical tolerance is measured against the intended historical anchor date, never
against the decision time. A later revision of a historical observation is visible only when
its own `availability_time <= T`.

`VIXCLS`, `WALCL` and `CPIAUCSL` log operations require strictly positive levels. If a required
anchor is absent or non-finite, or a log input is non-positive, the whole vector is
unavailable, the reason is typed and counted, and the row is never imputed. An unavailable
evaluation row is a counted abstention; an unavailable training row is excluded and counted.

No BTC price or volume, cross-asset breadth, funding, open-interest, basis, CFTC,
calendar/cycle, news, sentiment or on-chain feature may enter. No feature selection, clipping,
winsorization, rank transform, threshold search or post-result redesign is authorized.

## Pre-result source coverage gate

The audit may read canonical BTC bar timestamps and completeness only to recover the
already-frozen eligible decision grid. It may not load BTC closes, compute returns or
directions, fit a model, or inspect a prediction.

Each calendar fold 2019-2024 is source-admissible only when source-feature coverage under
`PREDICTIVE_MACRO_VINTAGE_FEATURES_V2` is at least 0.90 and at least 365 calendar days of
feature-valid history precede its start. Model execution is authorized only with at least five
admitted folds and pooled source-feature coverage of at least 0.95 over them. Failure
classifies `BLOCKED_MACRO_RELEASE_STATE_SOURCE_COVERAGE_V1`, consumes no predictive
configuration, and parks the macro family as
`PARKED_SOURCE_DESIGN_EXHAUSTED_NO_MARKET_RESULT`.

## Boundaries

This is a pure prediction experiment. It declares direction and calibrated probability, never
magnitude and never economics. It is the second and final source semantics authorized for the
ALFRED macro family in `PREDICTIVE_RESEARCH_GENERATION_V1`; a third is forbidden. It
authorizes no sealed query, no post-cutoff BTC access, no Champion, no prospective observer,
no live order, no credential and no real-money action.
