# CFTC leveraged positioning context V1

The source is the official CFTC annual compressed Traders in Financial Futures archive
for 2018–2024. The selected market is exactly
`BITCOIN - CHICAGO MERCANTILE EXCHANGE`, official contract market code `133741`.
Third-party mirrors and current/live APIs are outside the contract.

For every report the data foundation records `report_date`, actual
`publication_date`, `availability_timestamp`, and `publication_date_basis`. The normal
basis is `ORDINARY_CFTC_RELEASE_RULE`; a report whose official archived object date does
not match the normal Friday rule is `CFTC_OFFICIAL_EXCEPTION`. Missing or invalid
official publication evidence makes the row unavailable.

Availability is 00:00:00 UTC on the calendar day after actual publication. Eligibility
uses availability, never the Tuesday position date. Values are held unchanged until a
newer report becomes available; exact-boundary lookup uses `availability_timestamp <=
signal_timestamp`. There is no interpolation, freshness threshold, clipping, scaling,
rolling transform, or report-age feature.

The sole context feature is:

`CFTC_LEVERAGED_FUNDS_NET_OI_SHARE_V1 = (Lev_Money_Positions_Long_All - Lev_Money_Positions_Short_All) / Open_Interest_All`

All three fields come from the same official report. Missing/non-numeric fields,
nonpositive open interest, duplicate market/report rows, an unexpected market identity,
or post-cutoff availability in the canonical artifact fail closed. Raw archives and
publication evidence are preserved and content-hashed. This context is informational;
the traded instrument remains BTCUSDT spot.
