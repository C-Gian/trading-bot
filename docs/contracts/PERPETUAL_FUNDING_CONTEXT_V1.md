# PERPETUAL_FUNDING_CONTEXT_V1

Status: frozen prospectively for WP-015 before any model result.

BTCUSDT USD-M perpetual funding is public informational context only. BTCUSDT SPOT is
the sole traded instrument and LONG / NO_TRADE is unchanged. No futures order, paper
trade, credential, balance, or real-capital path is authorized.

The only context field is `LATEST_SETTLED_FUNDING_RATE`. At hourly spot signal time
`t`, select the record with greatest `fundingTime` strictly earlier than `t`. A record
timestamped exactly at `t` is unavailable. There is no interpolation, transformation,
clipping, standardization, rolling average, cumulative value, momentum, threshold, or
use of predicted funding, mark price, premium, basis, open interest, or position ratios.
If no strictly prior settlement exists, the signal row is ineligible.

The source is the credential-free official Binance USD-M Futures endpoint
`GET https://fapi.binance.com/fapi/v1/fundingRate`, fixed to symbol `BTCUSDT`, ascending
pagination, limit 1000, and an inclusive request ceiling of
`2024-12-31T23:59:59.999Z`. Every next start is the prior page's final `fundingTime + 1`
millisecond. Raw chunks and request metadata are retained locally and hash-pinned by the
tracked manifest. Canonical records contain only funding timestamp and funding rate.
Duplicates, backward timestamps, records after the ceiling, or settlement gaps exceeding
the expected eight-hour cadence plus a 60-second source-timestamp jitter tolerance fail
closed and are never filled. Shorter published intervals are retained as observed.
