# WP-002 gap characterization

Status: PASS

- Dataset: `BTCUSDT-SPOT-1M-DEV-v1`
- Total missing minutes: 8560
- Distinct intervals: 34
- Minimum / median / maximum duration: 3 / 134 / 2010 minutes
- Duration buckets (1, 2-5, 6-60, 61-240, >240): 0, 1, 6, 16, 11
- First gap: 2017-09-06T16:00:00Z to 2017-09-06T22:59:00Z
- Last gap: 2023-03-24T12:40:00Z to 2023-03-24T13:59:00Z
- Gap spans: 157 UTC 1h windows and 66 UTC 4h windows
- Accepted derived data flags 31 partial 1h and 50 partial 4h rows; fully absent windows are not represented as bars.
- Artifact SHA-256: `eaaed86d83897bc47479bbe71fea8775a72c248473a0e205bf4afee9cb551007`

Missing rows remain unfilled. Their cause is not inferred. The simulator rejects missing entry paths and returns unresolved data-gap outcomes when an open position crosses an unobserved interval.
