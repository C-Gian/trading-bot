# Predictive cross-asset breadth context V1

`PREDICTIVE_CROSS_ASSET_BREADTH_CONTEXT_V1`

The point-in-time contract for the first Stage-3 information family of
`PREDICTIVE_RESEARCH_GENERATION_V1`. It governs how the **rest of the crypto market** may
enter a prediction of the frozen BTCUSDT spot 24h terminal target.

Three families have already been tested and rejected on that target: BTC's own internal
price/volume structure, settled perpetual funding (a carry/price channel) and open interest
(a positioning-quantity channel). Cross-sectional breadth is orthogonal to all three: it is
information about *other* assets, observed at the same decision instant.

**BTCUSDT remains the sole prediction and product target.** Every other asset is a context
feature and nothing else. No asset is authorized for trading, no second target is created,
and no per-asset result is ever reported as a product claim.

## 1. Source

| Item | Value |
| --- | --- |
| Source class | official Binance public data archive only |
| Host | `https://data.binance.vision` |
| Prefix | `data/spot/monthly/klines`, interval `1h` |
| Manifest | `data/manifests/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.json` |
| Substrate artifact | `data/derived/BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1.parquet` |
| Credentials | none; the archive is credential-free public data |
| Quote asset | `USDT` only |
| Universe derivation | historical archive evidence, never current exchange info |
| Development ceiling | `2024-12-31T23:59:00Z` |

The substrate is not acquired by this family. It is the already-governed inventory, hashed by
its manifest, and the loader verifies that hash before reading a single row. Nothing here
downloads anything, and **no historical cross-sectional research result is imported**: prior
work on this substrate studied a different question under a different protocol and is not
predictive evidence for this target.

**Not admissible as a substitute**, under any circumstances: third-party vendors, scrapes,
reconstructed mirrors, current exchange listings, index constituents or any undocumented
backfill.

## 2. Admitted fields and admitted symbols

| Field | Status |
| --- | --- |
| `symbol` | admitted — identity only |
| `open_time` | admitted — the bar's opening instant on the hourly grid |
| `close` | admitted — the only price read |
| `open`, `high`, `low` | excluded |
| `volume`, `quote_volume` | excluded — no liquidity screen and no volume weighting exists |

A symbol is admitted when it is USDT-quoted, is **not** `BTCUSDT`, and is not excluded by the
manifest's frozen leveraged-token rule (a `UP`, `DOWN`, `BULL` or `BEAR` suffix immediately
preceding the quote asset). That rule is literal and non-discretionary; it is applied to the
symbol string alone so no post-hoc judgement about an individual asset can enter the universe.

`BTCUSDT` is present in the substrate and is removed here. The prediction target may not be
one of its own context features.

## 3. Point-in-time semantics

A spot hourly bar stamped `t` covers `[t, t+1h)` and closes at `t + 1h`. The frozen decision
instant `T` indexes the bar that has just closed, so `close[T]` is knowable at `T` — exactly
the convention the BTC target already uses on the same archive.

At `T`, an asset is **point-in-time eligible** when all four required endpoint bars

```
T ,  T-1h ,  T-24h ,  T-168h
```

have actually been observed for that asset. Nothing else decides membership.

What is forbidden, explicitly:

- **no future-survival filter** — an asset's eventual delisting, eventual sample length or
  eventual liquidity may not affect whether it participates at `T`;
- **no whole-sample participation threshold** — no requirement of a fixed total row count over
  the complete sample, and in particular the retired 504-row/epoch participation idea is not
  revived in any form;
- **no interpolation, forward fill, nearest-bar substitution or reconstruction** — a missing
  endpoint bar makes that asset unavailable at that instant and nothing more;
- **no market-capitalisation, future-volume or survivorship weighting** — every cross-sectional
  statistic is equal-weighted over the eligible set.

Membership is therefore recomputed at every decision instant and may grow or shrink causally:
an asset that lists tomorrow is absent today, and an asset that is delisted tomorrow is a full
member today.

**Residual assumption, stated rather than hidden.** The substrate is a monthly archive
reconstruction of an hourly grid. A bar the archive never published is simply absent rather
than late, and absence removes that asset from that instant instead of admitting a stale or
reconstructed value. The failure mode of this source is abstention, never imputation.

## 4. Feature window and validity

`PREDICTIVE_CROSS_ASSET_BREADTH_FEATURES_V1` requires at least **30** point-in-time eligible
non-BTC assets at `T`. Below that the whole feature vector is unavailable and the candidate
abstains. The reason is typed and counted:

| Reason | Meaning |
| --- | --- |
| `DECISION_INSTANT_OUTSIDE_SOURCE_SPAN` | the `T-168h … T` window is not inside the observed source span |
| `INSUFFICIENT_POINT_IN_TIME_UNIVERSE` | fewer than thirty eligible non-BTC assets at `T` |
| `NON_FINITE_CROSS_ASSET_FEATURE` | a computed statistic is not finite |

The rules are ordered and mutually exclusive: the first that fires owns the instant.

The universe size is reported as source accounting. It is **not** a model feature.

## 5. Frozen feature set

For every point-in-time eligible asset, using complete hourly endpoint bars only:

```
r_1h            = log(close[T] / close[T-1h])
r_24h_trailing  = log(close[T] / close[T-24h])
r_168h_trailing = log(close[T] / close[T-168h])
```

The same asset set possesses all four endpoint bars and is used for all eight statistics, in
this order:

| # | Name | Definition |
| --- | --- | --- |
| 1 | `BREADTH_UP_SHARE_1H` | fraction with `r_1h > 0` |
| 2 | `BREADTH_UP_SHARE_24H` | fraction with `r_24h_trailing > 0` |
| 3 | `BREADTH_UP_SHARE_168H` | fraction with `r_168h_trailing > 0` |
| 4 | `CROSS_MEDIAN_RETURN_1H` | median `r_1h` |
| 5 | `CROSS_MEDIAN_RETURN_24H` | median `r_24h_trailing` |
| 6 | `CROSS_MEDIAN_RETURN_168H` | median `r_168h_trailing` |
| 7 | `CROSS_MAD_RETURN_24H` | median absolute deviation of `r_24h_trailing` from its cross-sectional median |
| 8 | `CROSS_MAD_RETURN_168H` | median absolute deviation of `r_168h_trailing` from its cross-sectional median |

A return of exactly zero is not an up move, so it does not enter an up share.

No BTC price or return, funding, open-interest, order-flow, macro, calendar, news, sentiment
or on-chain feature is included. No clipping, winsorization, rank transform, sign inversion,
threshold, interaction term or feature selection may be added, and no Stage-1, settled-funding
or open-interest feature may be combined with these.

## 6. What this contract does not do

- It does not change the frozen prediction target, horizon, labels, folds, scorer, reliability
  bins or bootstrap block length. Those remain
  [`PREDICTIVE_EVALUATION_CONTRACT_V1`](../canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md)
  Amendment A1 and `PREDICTIVE-BASELINES-V1`.
- It does not declare a magnitude. The families admitted under it declare direction and
  calibrated probability only; magnitude returns once a source family earns directional
  admission.
- It does not admit basis, CFTC, macro, calendar, news, sentiment or on-chain data.
- It does not repair the Stage-1 canonical hourly gap debt, which remains deferred.
- It does not authorize any asset other than `BTCUSDT` as a prediction or trading target.
- It authorizes no sealed query, no Champion and no real money.
