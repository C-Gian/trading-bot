# Predictive open interest structure V1

`PREDICTIVE_OPEN_INTEREST_STRUCTURE_V1`

The point-in-time contract for the second Stage-2 information family of
`PREDICTIVE_RESEARCH_GENERATION_V1`. It governs how historical BTCUSDT USD-M perpetual
**open interest** may enter a prediction of the frozen spot 24h terminal target.

Open interest measures the *quantity* of leveraged exposure outstanding. Settled funding,
already tested and rejected under
[`PREDICTIVE_SETTLED_FUNDING_STRUCTURE_V1`](PREDICTIVE_SETTLED_FUNDING_STRUCTURE_V1.md),
tested a price/carry channel. The two families are orthogonal by construction and are never
combined.

## 1. Source

| Item | Value |
| --- | --- |
| Source class | official Binance public data archive only |
| Host | `https://data.binance.vision` |
| Prefix | `data/futures/um/daily/metrics/BTCUSDT` |
| Manifest | `data/manifests/BTCUSDT-USDM-OPEN-INTEREST-DEV-v1.json` |
| Canonical artifact | `data/derived/BTCUSDT-USDM-open-interest-5m-v1.parquet` |
| Credentials | none; the archive is credential-free public data |
| Cadence | 5 minutes, 288 records per complete day |
| Development ceiling | `2024-12-31T23:59:59.999Z` |

Every daily object is downloaded together with the archive's own `.CHECKSUM` file and is
verified against it before parsing. A mismatch aborts acquisition; it never enters the
canonical artifact. The daily object's CSV header must equal the archive's exact column
order, so an upstream schema change fails the parse instead of silently shifting a column.

**Not admissible as a substitute**, under any circumstances: third-party vendors, scrapes,
reconstructed vendor mirrors, the current REST `openInterestHist` snapshot window, or any
undocumented backfill. If the official archive does not publish a period, that period simply
has no source.

## 2. Admitted fields

| Field | Status |
| --- | --- |
| `create_time` | admitted — the record timestamp |
| `sum_open_interest` | admitted — aggregate perpetual open-interest **quantity** |
| `sum_open_interest_value` | **excluded** — notional mechanically embeds BTC price |
| `count_toptrader_long_short_ratio` | excluded |
| `sum_toptrader_long_short_ratio` | excluded |
| `count_long_short_ratio` | excluded |
| `sum_taker_long_short_vol_ratio` | excluded |

Only the quantity is admitted, so the family stays interpretable as positioning quantity and
cannot smuggle in a price feature. Funding, mark price, index price, premium, basis and
liquidation fields are outside this contract entirely.

## 3. Point-in-time semantics

`create_time` is the measurement instant of the open-interest snapshot: the archive publishes
one record per five-minute boundary, each stamped with the boundary it measures.

At an hourly decision instant `T` the **OI state** is the record with the largest
`create_time` satisfying

```
create_time < T
```

A record stamped exactly `T` is **not** available — settlement of a measurement at `T` is not
knowable strictly before `T`.

The selected record must additionally satisfy

```
T - create_time <= 10 minutes
```

Otherwise the state is unavailable. There is no interpolation and no forward fill beyond this
as-of rule.

**Residual assumption, stated rather than hidden.** The archive documents the measurement
timestamp; it does not separately document a publication lag. Because the cadence is five
minutes and the rule is strictly `< T`, the newest usable record is normally stamped `T - 5m`,
and the staleness bound caps the worst case at `T - 10m`. A look-ahead would therefore require
the archive's publication lag to exceed five minutes, which the near-real-time nature of the
series makes implausible but which this contract cannot prove from the archive alone. The
assumption is recorded in the source audit and in every experiment admitted under this
contract.

## 4. Feature window and validity

`PREDICTIVE_OPEN_INTEREST_FEATURES_V1` requires a valid OI state at **every** hour in
`T-24h … T` — twenty-five hourly states. If any required state is unavailable or
non-positive, the whole feature vector is unavailable and the candidate abstains. The reason
is typed and counted:

| Reason | Meaning |
| --- | --- |
| `NO_PRIOR_OPEN_INTEREST_RECORD` | no record strictly before that hour exists |
| `OPEN_INTEREST_STATE_TOO_STALE` | the newest strictly-prior record is older than ten minutes |
| `NON_POSITIVE_OPEN_INTEREST` | the selected quantity is not strictly positive |
| `NON_FINITE_OPEN_INTEREST_FEATURE` | a computed value is not finite |

The rules are ordered and mutually exclusive: the first that fires owns the instant.

## 5. Frozen feature set

Let `O_t > 0` be the as-of state at hour `t`, and let `L_t = log(O_t)`. Exactly six features,
in this order, over the states `T-24h … T`:

| # | Name | Definition |
| --- | --- | --- |
| 1 | `OI_LOG_CHANGE_1H` | `L_T - L_{T-1h}` |
| 2 | `OI_LOG_CHANGE_4H` | `L_T - L_{T-4h}` |
| 3 | `OI_LOG_CHANGE_24H` | `L_T - L_{T-24h}` |
| 4 | `OI_LOG_LEVEL_Z24` | z-score of `L_T` against the 25 states, population standard deviation |
| 5 | `OI_LOG_DIFF_VOL24` | population standard deviation of the 24 one-hour differences of `L` |
| 6 | `OI_LOG_TREND24` | OLS slope of `L` on the integer hour index `0..24` |

For `OI_LOG_LEVEL_Z24`, an exactly zero population standard deviation emits `0.0`. For
`OI_LOG_DIFF_VOL24`, zero is a valid value.

No clipping, winsorization, sign inversion, threshold, interaction term, calendar variable or
price-derived feature may be added. No Stage-1 internal feature and no settled-funding feature
may be combined with these.

## 6. What this contract does not do

- It does not change the frozen prediction target, horizon, labels, folds, scorer, reliability
  bins or bootstrap block length. Those remain
  [`PREDICTIVE_EVALUATION_CONTRACT_V1`](../canonical/PREDICTIVE_EVALUATION_CONTRACT_V1.md)
  Amendment A1 and `PREDICTIVE-BASELINES-V1`.
- It does not admit basis, long/short ratios, CFTC, macro, news, sentiment or on-chain data.
- It does not repair the Stage-1 canonical hourly gap debt, which remains deferred.
- It authorizes no sealed query, no Champion and no real money.
