# ADR-0012 — CFTC leveraged-funds positioning as a point-in-time development context

Status: accepted for one preregistered WP-017 development experiment pending Owner execution.

## Decision

The WP-017 source gate selected official CFTC Traders in Financial Futures data for
`BITCOIN - CHICAGO MERCANTILE EXCHANGE`, contract market code `133741`. Only official
annual compressed TFF archives for 2018-2024 are used. Third-party mirrors and
reconstruction of historical values from a current API are outside the contract, because
neither can prove what was knowable at a past signal time.

Exactly one new feature is admitted:

`CFTC_LEVERAGED_FUNDS_NET_OI_SHARE_V1 =
(Lev_Money_Positions_Long_All - Lev_Money_Positions_Short_All) / Open_Interest_All`

All three fields are taken from the same official report. Nonpositive open interest or a
missing/non-numeric field makes the context unavailable. No clipping, z-score, rolling
normalization, weekly change, momentum, alternative window, alternative trader group or
interaction is admitted, and Binance funding stays excluded because it was already
rejected.

## Report date is not availability

The governing risk in Commitments of Traders data is that a report describes Tuesday
positions but is published later. Treating the report date as the availability date would
leak several days of hindsight into every signal.

Each canonical record therefore carries `report_date`, `publication_date`,
`availability_timestamp` and `publication_date_basis`. The publication date is resolved
from the dated label embedded in that report's own official archived object, not from an
HTTP header and not from an assumed calendar. A publication date matching the ordinary
schedule is recorded as `ORDINARY_CFTC_RELEASE_RULE`; anything else, including holiday,
shutdown, outage and correction timing, is recorded as `CFTC_OFFICIAL_EXCEPTION`.

The frozen availability rule is 00:00:00 UTC on the calendar day after the actual
publication date. If a publication date cannot be resolved from official evidence, the row
is ineligible and fails closed rather than defaulting to an assumed release.

Of 352 raw rows, 47 carry official exception timing, including the 2018-2019 shutdown
delays where the 2018-12-24 report was not published until 2019-02-01.

## Cutoff boundary

Eligibility uses `availability_timestamp`, never `report_date`. The report dated
2024-12-31 was published 2025-01-06, so it became available 2025-01-07, after the
immutable 2024-12-31T23:59:00Z development cutoff. It is preserved in the raw archive and
excluded from the canonical development context. 351 of 352 rows are eligible and zero
rows have an unresolved publication date. A dedicated deterministic test guards this
boundary.

## As-of semantics

For a governed 1h signal at time t, the context is the latest record with
`availability_timestamp <= t`, held unchanged until another eligible publication exists.
There is no interpolation, no report-age feature and no freshness cutoff, so an absent or
stale report never silently becomes a signal of its own.

## Matched control

The prediction universe is computed once, without reference to a configuration. The
primary (`INTERNAL_PLUS_CFTC_LEVERAGED_NET_HGBR`, F1-F8 plus the one new feature) and its
matched control (`INTERNAL_HGBR_MATCHED_CFTC`, F1-F8 only) are therefore structurally
guaranteed to use identical eligible timestamps, so any difference is attributable to the
feature rather than to a different trading universe.

## Runtime

WP-017 binds `RESEARCH_RUNTIME_V2_BATCH` explicitly rather than inheriting a frozen V1
runtime. It is the first candidate to do so. DEFAULT, ZERO and DOUBLE reuse one prediction
set and DELAY_1H uses governed deterministic delay alignment. Frozen WP-008 and
WP-011--WP-016 implementations and identities are unmodified.

## Consequences

The search burden is registered prospectively: one hypothesis, one new feature, one
primary, one matched control, one fixed model, four profiles and fixed folds, with ten
reserved model fits and zero executed. Success criteria are frozen in the protocol and in
both preregistrations before any result exists and may not be changed afterwards.

Reconciliation is honestly declared PARTIAL: it re-parses the preserved official archives,
the publication calendar, the as-of mapping, the matched universe, the model refits, the
predictions and the DEFAULT execution independently of the WP-017 lab and runner, but it
still shares the governed feature source, label and execution primitives.
