# ADR-0032 — Owner selects no-cost public-data research path

Status: ACCEPTED (2026-09-21)

The Owner selects Branch B from ADR-0031: no paid or credentialed market/on-chain data at this stage.

## Decision

- Do not purchase, trial, request, or store credentials for Glassnode, CryptoQuant, Coin Metrics Pro, or equivalent paid data.
- Keep the on-chain PIT exchange-flow hypothesis parked as a future enhancement path.
- Proceed with free, official, exchange-native historical data.
- Before opening another 24h V2 model family, run a bounded horizon foundation using public Binance taker-flow information.
- This foundation may compare shorter targets, but it does not change the product target by itself. Any later product-horizon change requires a separate Research Director decision.
- No sealed/post-cutoff data, Champion, real money, or magnitude work.

## Free source selected

Official Binance public archives, BTCUSDT only:

- Spot 1m klines;
- USD-M perpetual BTCUSDT 1m klines;
- development range 2020-01-01 through 2024-12-31;
- archive checksum captured and pinned for every acquired file.

The public kline schema contains quote volume and taker-buy quote volume, sufficient to construct a compact aggressive-buy/sell imbalance proxy without downloading the much larger raw/aggregate-trade archive.

Historical archive revisions are handled by immutable acquisition manifests/checksums. No current API value may silently replace a pinned historical file.

## Scientific purpose

Test whether a fixed, low-complexity taker-flow signal carries directional information at 24h, and if not whether the same signal survives at a nearer 4h or 1h horizon.

This is a horizon/source foundation, not a V2 admission experiment and not a strategy rescue.
