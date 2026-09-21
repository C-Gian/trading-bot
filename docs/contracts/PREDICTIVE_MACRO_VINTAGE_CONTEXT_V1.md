# Predictive macro-vintage context V1

Status: frozen before any `PREDICTIVE-STAGE3-MACRO-VINTAGE-V1` outer-fold prediction.

This contract admits the existing `ALFRED_MACRO_CONTEXT_V1` artifact only for the bounded
predictive experiment in the active work package. It references and does not alter
[`POINT_IN_TIME_EXOGENOUS_DATA_V1`](POINT_IN_TIME_EXOGENOUS_DATA_V1.md). The BTCUSDT target,
24h terminal horizon, folds, scorer and baselines remain those of the canonical predictive
evaluation contract Amendment A1.

## Source identity and availability

- Manifest: `data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json`.
- Canonical artifact: `data/derived/ALFRED-macro-context-v1.parquet`, file SHA-256
  `448f1ea80252ce5fbc7f1982c41540dc71852c3a4e2fbf1a1357fd1ed9c877dd`.
- Catalog: `research/exogenous/ALFRED_SERIES_CATALOG_V1.json`, SHA-256
  `cfc08c40c669770a144210026b81326379e50e7d61e770d3d4b40baf5e94b8b1`.
- Exact series, in order: `DFF`, `DGS10`, `T10Y2Y`, `VIXCLS`, `NFCI`, `WALCL`,
  `CPIAUCSL`, `UNRATE`.
- A vintage state becomes usable at `00:00:00Z` on the next calendar day after
  `vintage_start`. A record is usable at decision timestamp `T` only when
  `availability_time <= T`.
- Current-revised FRED substitution, post-2024 vintages, interpolation, forward filling,
  nearest-future lookup and missing-value imputation are forbidden.

At every `T`, the complete state is reconstructed from only vintage records already
available at `T`. All anchors and changes for that vector are computed from that same
snapshot. A later revision can affect only timestamps at or after its conservative
availability boundary.

## Frozen feature vector

`PREDICTIVE_MACRO_VINTAGE_FEATURES_V1` contains exactly, in order:

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

For daily/business-daily series an anchor uses the latest observation on or before the
anchor and is invalid when older than 7 calendar days. Weekly and monthly limits are 14
and 45 days respectively. Daily and weekly change anchors are the UTC decision date minus
the declared number of calendar days. CPI and unemployment first select the latest valid
monthly observation as known at `T`, then require the observation on exactly the same
calendar day 12 or 3 calendar months earlier. VIX, WALCL and CPI log operations require
strictly positive levels.

If any anchor is missing, stale, non-positive where a logarithm is required, or produces a
non-finite value, the complete vector is unavailable. The reason is typed and counted; the
row is never imputed. An unavailable evaluation row is a counted abstention and an
unavailable training row is excluded and counted.

No BTC price/volume, cross-asset, funding, open-interest, basis, CFTC, calendar/cycle,
news, sentiment or on-chain feature may enter. No feature selection, clipping,
winsorization, rank transform, threshold search or post-result redesign is authorized.

## Source-only admission gate

The audit may inspect canonical BTC bar timestamps and completeness solely to recover the
already-frozen eligible decision grid. It may not load BTC closes, calculate returns or
directions, fit a model or inspect a prediction.

Each calendar fold 2019–2024 is source-admissible only when source-feature coverage is at
least 0.90 and at least 365 calendar days of feature-valid history precede its start. Model
execution is authorized only with at least five admitted folds and pooled source-feature
coverage of at least 0.95. Failure classifies
`BLOCKED_MACRO_SOURCE_COVERAGE_V1` and consumes no predictive configuration.

## Boundaries

This is a pure prediction experiment. It declares direction and calibrated probability,
not magnitude or economics. It authorizes no sealed query, post-cutoff BTC access,
Champion, observer, live order, credential or real-money action.
