# WP-005 source-integrity audit

Classification: **SOURCE_ARCHIVE_OFF_GRID_CONFIRMED**. Structural status:
**PASS**.

The two required local Binance Spot monthly archives match the SHA-256 values
accepted by `BTCUSDT-SPOT-1M-DEV-v1`:

- 2017-12: `3d41da2da488a69a21e9223221863c3a8ed6ccb9263d30cf1d3a012a48cfffc1`
- 2018-02: `131667f0d4ff73685852d84a406e07f8a3fdf7037798b1bdb0519e7e987e19ad`

Every one of the 21,602 anomalous raw CSV first-column millisecond values maps
exactly to the corresponding canonical UTC-microsecond timestamp. Every mapped
OHLCV and ancillary payload field also matches the source row. The parser column
mapping and millisecond-to-microsecond conversion are correct; no conversion
error introduced either offset.

The accepted source archives contain two strictly ordered, internally 60-second
spaced runs: 20,401 rows at modulo-minute 20,799 ms from
`2017-12-04T06:00:20.799000Z` through `2017-12-18T10:00:20.799000Z`, and 1,201
rows at modulo-minute 14,789 ms from `2018-02-09T09:59:14.789000Z` through
`2018-02-10T05:59:14.789000Z`. Exact transition values, full first-column
hashes, spacing distributions, and payload checks are retained in the
[validation artifact](../validation/WP-005-SOURCE-PROVENANCE.json).

The independent quarantine reconstruction exactly reproduces 363 affected 1h
buckets, 92 affected 4h buckets, and mask SHA-256
`27f629a5e0edde9fada51c9cd373e591e4ba4a8a53c9d1e68327e10b3c4c5bd5`.
It applies zero repairs or fills. Neither quarantined set intersects any 2019–2024
validation signal window or its required 26x1h / 43x4h warm-up buckets. No
post-cutoff bytes were read.

This establishes archive provenance, not the cause inside the live exchange.
The conservative source-grid quarantine remains unchanged.
