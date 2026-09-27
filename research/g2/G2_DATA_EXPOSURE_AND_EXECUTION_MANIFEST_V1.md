# G2 Data Exposure and Execution Manifest V1

Status: FROZEN AT G2-00 GATE A  
Date: 2026-09-27  
Authority: ADR-0052; Astra Development System Directive V2

## 1. Purpose

This manifest freezes:
- the G2 V1 research instrument;
- data fields and causal meanings;
- current historical exposure;
- protected-data boundaries;
- execution approximations;
- phase-bounded I/O requirements.

It does not authorize an economic market run.

## 2. Research instrument

Instrument:
- BTCUSDT USD-M linear perpetual contract.

Research purpose:
- symmetric LONG/SHORT paper accounting;
- no real margin/leverage authorization;
- virtual gross notional capped by the separate risk contract.

Primary historical price source:
- Binance official public USD-M 1m kline archive already pinned in repository manifest
  data/manifests/BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1.json.

Existing official-archive coverage used by G2:
- 2020-01 through 2024-12;
- 1m;
- checksum-verified monthly objects;
- request ceiling 2024-12-31T23:59:59.999Z.

Primary funding source:
- data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json;
- settled funding through 2024-12-31 16:00 UTC;
- raw request pages and derived file hash-pinned.

Spot data exists in the repository but is not a G2-V0 forecast input.

## 3. CRYPTO-CONTRACT-01 outcome

Classification:
PASS_WITH_DECLARED_HISTORICAL_EXECUTION_APPROXIMATION.

Primary current venue documentation reviewed on 2026-09-27:
- Binance USD-M Futures REST API, Exchange Information;
- Binance USD-M Futures REST API, Kline/Candlestick Data;
- Binance USD-M Futures REST API, Mark Price;
- Binance USD-M Futures REST API, Funding Rate History;
- Binance USD-M Futures REST API, Funding Rate Info;
- Binance USD-M Futures REST API, Recent Trades;
- Binance USD-M Futures REST API, Symbol Order Book Ticker.

Documentation root:
https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data

Verified semantics relevant to G2:
- /fapi/v1/exchangeInfo publishes current symbol/contract type/status, quote/base/margin assets and
  price/quantity filters;
- precision fields are not substitutes for tickSize/stepSize; filters are authoritative;
- /fapi/v1/klines returns open/high/low/close, base volume, close time, quote volume, trade count,
  taker-buy base volume and taker-buy quote volume;
- /fapi/v1/trades identifies whether the buyer was maker;
- /fapi/v1/premiumIndex exposes current mark price, index price, latest funding rate and next funding
  time;
- /fapi/v1/fundingRate is settled funding history with fundingTime and fundingRate;
- /fapi/v1/fundingInfo describes funding interval and adjusted cap/floor changes;
- /fapi/v1/ticker/bookTicker exposes current best bid/ask price and quantity.

These facts define field meaning. They do not imply directional alpha.

## 4. Core historical fields

CORE historical:
- open_time;
- open;
- high;
- low;
- close;
- base_volume;
- close_time;
- quote_volume;
- trade_count;
- taker_buy_base_volume;
- taker_buy_quote_volume;
- settled funding_time;
- settled funding_rate.

Derived deterministic bars:
- 15m;
- 1h;
- 4h;
- Daily UTC;
- Weekly UTC.

All derived bars come from the same 1m USD-M source and completed-bar rules.

## 5. Core future-paper/live fields

In addition to the historical core:
- server/receipt timestamp;
- best bid;
- best ask;
- bid quantity;
- ask quantity;
- current contract-filter snapshot;
- applicable actual fee schedule/version;
- mark price where required for funding/risk accounting;
- index price where required for monitoring.

These future fields improve execution measurement. Their absence from old history must not be filled
by invented L2/queue information.

## 6. Data not required for G2-V0

Not required and not to be acquired merely to expand the feature set:
- L2/L3 order book;
- queue position;
- open interest;
- liquidation feeds;
- long/short ratios;
- options/implied data;
- cross-venue universe;
- on-chain;
- news/NLP;
- social sentiment.

Existing old project files for some of these families remain search memory. Their existence does not
authorize V0 use.

## 7. Field availability semantics

Every normalized observation must support:
- event_time;
- available_at;
- received_at when actually observable;
- source identifier;
- source version/manifest hash;
- unit;
- data-quality state.

Historical archive convention:
- for a complete 1m kline, the row becomes available only at/after its close boundary;
- no decision may use a bar whose close is after the decision instant.

Settled funding convention:
- funding_rate from historical funding history becomes usable for accounting at funding_time;
- the final settled rate is not backfilled into decisions before funding_time;
- historical predicted-funding state is not present in the pinned G2 data and is therefore absent.

Current premiumIndex fields may be used prospectively only when actually timestamped/recorded.

## 8. Exposure ledger

### 2020

Classification:
EXPOSED_DEVELOPMENT_INITIALIZATION.

Use:
- source warm-up;
- first model training;
- causal/prequential residual archive construction after minimum training support.

It is not confirmation evidence.

### 2021-2024

Classification:
EXPOSED_DEVELOPMENT_SANDBOX.

Use:
- G2-02 bounded development only after separate authorization;
- diagnostics, autopsy and up to the frozen revision budget.

All previous project exposure/search memory remains acknowledged.

The fact that G1 did not compute 2023-2024 configuration economics in Phase A does not make those
years pristine confirmation data.

### 2025 onward

Classification:
PROTECTED_CANDIDATE_HISTORY / NOT AUTHORIZED FOR G2 DESIGN.

Current canonical state before G2 acquisition:
- protected dataset not acquired for G2 evaluation;
- authorized protected queries: 0;
- consumed protected queries: 0.

No G2-00 or G2-01 task may read 2025+ BTC market outcomes to choose features, thresholds, costs,
examples or architecture.

Before G2-03, a dedicated audit must define the exact protected interval and verify actual exposure.
If that audit finds material prior design exposure, the period is relabeled honestly; dates are not
shifted opportunistically until a favorable holdout appears.

### Future after candidate freeze and explicit activation

Classification:
FUTURE_PAPER only when predictions/actions were actually emitted prospectively under the frozen
system and operational coverage is recorded.

Backfilled reconstructions are BACKFILLED_RESEARCH, never future paper.

## 9. Current repository source lineage

USD-M 1m source manifest:
data/manifests/BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1.json

Important properties:
- official Binance data archive;
- credential-free;
- monthly raw objects;
- checksum verified;
- both Spot and USD-M objects exist;
- G2 reads USD-M objects only unless a later authorized contract says otherwise.

Funding source manifest:
data/manifests/BTCUSDT-USDM-FUNDING-DEV-v1.json

Important qualification:
the old manifest contains historical project-context metadata naming BTCUSDT_SPOT as traded
instrument even though the source itself is USD-M settled funding. G2 does not inherit that metadata
as instrument truth. G2 instrument identity is frozen by this manifest and the forecast/execution
contract.

## 10. Phase-bounded I/O rule

The G1 source layer could open full monthly/funding objects and filter observations later. That is
registered engineering debt and is not acceptable for a future protected phase.

G2 source contracts require:
1. resolve authorized interval before opening observation files;
2. open only monthly/archive objects intersecting the authorized interval;
3. reject any object outside the phase boundary;
4. filter row groups/records to authorized bounds before returning them;
5. log requested interval, opened-object interval and returned interval;
6. metadata-only manifest identity reads are allowed without opening observations;
7. tests fail if an unauthorized observation object is touched.

For G2-02 the authorized market-observation ceiling is 2024-12-31T23:59:59.999Z.

No loader path may discover or enumerate 2025+ observation files as a convenience during G2-02.

## 11. Current contract filters

Exact BTCUSDT tick size, step size, minimum quantity/notional and order restrictions are not
hard-coded in this scientific document because exchangeInfo is the venue's current source of truth
and these rules can change.

Runtime requirement:
- capture a full exchangeInfo snapshot;
- select BTCUSDT PERPETUAL/TRADING;
- persist the relevant filters and snapshot hash;
- apply PRICE_FILTER and quantity/notional filters from that pinned snapshot;
- never derive tick/step from pricePrecision/quantityPrecision.

Synthetic fixtures use explicit fake filters.

Before any G2 economic replay, the run manifest must contain the pinned filter snapshot actually
used. Changing the pinned snapshot is provenance, not a hidden model adjustment.

## 12. Fee and historical spread boundary

The repository does not contain:
- a user-specific historical USD-M commission schedule over the whole sandbox;
- full historical best bid/ask for the whole sandbox.

Current USD-M account commission is account/tier dependent and should be obtained from the
applicable account/venue source when future paper is authorized.

Therefore G2 historical development uses the explicit aggregate friction convention frozen in
G2_FORECAST_POLICY_EXECUTION_CONTRACTS_V1.md:
- base 12bp per executed side;
- 1.5x stress 18bp per side;
- 2x stress 24bp per side.

These are research scenarios, not statements of current Binance fees.

No post-result reduction of the scenario is permitted to rescue performance.

## 13. Latency and fill realism

Historical V1 execution:
- market-only;
- base latency 1m;
- stress adds 5m;
- no passive queue;
- no limit-order touch fill;
- stop gap fills use worse observable open when crossed;
- missing exact entry/expiry bar invalidates the shadow/trade event;
- friction is adverse on every executed side.

Future paper:
- actual best bid/ask timestamp can measure decision-to-executable-price shortfall;
- actual rejects/cancels/gaps are stored;
- the system must not backfill downtime as prospective coverage.

## 14. Funding accounting boundary

Funding is included only for intervals during which a paper position is actually open.

Historical settled rate:
- allowed only at its settlement time;
- not a forecast input.

Historical mark price:
- absent from current pinned funding artifact;
- last-price 1m proxy at settlement is used only as a declared accounting approximation.

If future work acquires a point-in-time mark-price series, it becomes a new versioned data contract.

## 15. Missingness/staleness

Critical fields:
- price OHLC;
- quote/base volume;
- taker-buy volume for the full V0 model;
- required funding settlements;
- contract filters when sizing.

Critical missingness:
- creates FORECAST_UNAVAILABLE or execution abstention;
- never becomes numeric zero;
- never uses future forward-fill.

Daily/Weekly display context may be absent without changing V0 forecast.

Cycle state may be UNAVAILABLE without changing V0 forecast because it is shadow only.

## 16. G2-01 engineering-data authorization

G2-01 may:
- read metadata/manifests;
- use synthetic fixtures freely;
- use small explicitly declared windows from <=2024 exposed data for parser/aggregation/replay
  parity and causality checks;
- compare output hashes and prefix invariance.

G2-01 may not:
- compute/compare cumulative strategy economics;
- select a model/version from market performance;
- inspect protected 2025+ outcomes.

## 17. CRYPTO-CONTRACT-01 scientific conclusion

The existing repository data is sufficient to implement the first causal G2 vertical slice without
new alpha-data acquisition.

Known limitation:
historical execution realism is scenario-based because historical bid/ask and user-specific fees are
not pinned.

That limitation is acceptable for exposed development if explicitly stress-tested. It must be
measured prospectively with actual quotes/fees before future evidence is called live/paper
confirmation.
