# WP-017 CFTC leveraged-positioning preparation checkpoint

WP-017 is preregistered and available for Owner-initiated execution. No historical market
result was computed or observed in this checkpoint, and no WP-017 model was fitted.

## Source

Official CFTC Traders in Financial Futures annual archives for 2018-2024 supply
`BITCOIN - CHICAGO MERCANTILE EXCHANGE`, contract market code `133741`. Each annual ZIP is
preserved with its source URL, retrieval timestamp, compressed byte size and SHA-256. No
third-party mirror and no current-API reconstruction of historical values is used.

Report date is never treated as availability. Each report resolves an actual publication
date from the dated label inside its own official archived report object, classified as
`ORDINARY_CFTC_RELEASE_RULE` or `CFTC_OFFICIAL_EXCEPTION`. Availability is 00:00:00 UTC on
the calendar day after actual publication. An unresolved publication date makes the row
ineligible and fails closed.

352 raw rows canonicalize to 351 point-in-time eligible rows. 47 rows carry official
exception timing, including the 2018-2019 shutdown delays. Zero rows have an unresolved
publication date, zero duplicates and zero invalid required fields.

The report dated 2024-12-31 was published 2025-01-06 and became available 2025-01-07,
after the immutable 2024-12-31T23:59:00Z cutoff. It is preserved in the raw archive and
excluded from the canonical development context. First eligible availability is
2018-04-14T00:00:00Z and last eligible availability is 2024-12-31T00:00:00Z.

Manifest `CFTC-CME-BITCOIN-TFF-DEV-v1`, canonical logical SHA-256
`d2984e9102d1c41e21f5408ebbcfba12525b298697c34793a9d137200702ae0d`.

## Design

SEARCH_MEMORY admitted `FAM-CFTC-REGULATED-FUTURES-POSITIONING` as a new family for
hypothesis `CFTC_LEVERAGED_FUNDS_NET_POSITIONING_ADDS_INFORMATION_V1`. The claim is
predictive, not causal.

The only new feature is `CFTC_LEVERAGED_FUNDS_NET_OI_SHARE_V1`, defined as
`(Lev_Money_Positions_Long_All - Lev_Money_Positions_Short_All) / Open_Interest_All` with
all three fields from the same official report. There is no clipping, normalization,
rolling transform, change or momentum term, alternative trader group or interaction.

`EXP-ML-028-INTERNAL-PLUS-CFTC-LEVERAGED-NET-HGBR` is the primary and uses F1-F8 plus that
single feature. `EXP-ML-029-INTERNAL-HGBR-MATCHED-CFTC` is the matched control and uses
F1-F8 only. Binance funding is excluded; it was already rejected. The prediction universe
is computed once without reference to a configuration, so both use identical eligible
timestamps by construction.

As-of lookup takes the latest record with `availability_timestamp <= signal time` and
holds it unchanged until another eligible publication exists. There is no interpolation,
report-age feature or freshness cutoff.

The frozen shallow HGBR specification, the frozen `ISOLATED_FIXED_PLAN_DEFAULT_NET_R_V1`
target, BAR_CLOSE to NEXT_1M_OPEN execution, STOP_FIRST ambiguity handling and existing
costs are reused unchanged. Folds are the five complete annual expanding validation years
2020-2024 with a 216-hour purge and outcome containment. The signal rule is exactly
`prediction_default_net_r > 0`. Profiles are DEFAULT, ZERO, DOUBLE and DELAY_1H.

WP-017 is the first candidate to bind `RESEARCH_RUNTIME_V2_BATCH` explicitly; it does not
inherit a frozen V1 runtime. DEFAULT, ZERO and DOUBLE reuse one prediction set and
DELAY_1H uses governed deterministic delay alignment. A V2 result without a valid stage
timing record fails closed.

Success criteria are frozen before any result exists, in the protocol and in both
preregistrations: primary DEFAULT mean net R above zero; primary DEFAULT above control
DEFAULT; at least 3 of 5 primary annual DEFAULT folds with mean net R at or above zero;
and primary DOUBLE mean net R at or above zero. ZERO positive with DEFAULT nonpositive is
a cost-dominated rejection; DEFAULT positive with fewer than 3 of 5 nonnegative folds is
not a robust success. DELAY_1H is mandatory robustness evidence, not a hard pass
condition.

## Chronology

Data foundation commit `b8b8005`. Preregistration commit `d53c983`. The Research Lab
candidate `WP017_CFTC_LEVERAGED_POSITIONING_V1` was exposed only afterwards, in a separate
commit, and the ordering is mechanically verified by `scripts/check.py`.

The candidate binds the exact preregistration hashes, reports real deterministic stages,
writes only local gitignored runtime artifacts, runs an independent reconciliation and
generates the compact review bundle. Import and tests never invoke its real adapter.

## Reconciliation strength

`scripts/reconcile_wp017.py` is independent of the WP-017 lab and runner. It re-parses the
preserved official archives and publication calendar, rebuilds the canonical context, and
independently verifies the as-of mapping, the matched timestamp universe, the annual
boundaries and model identities, the fold predictions and the DEFAULT execution and
metrics. It still shares the governed feature source, isolated label and backtest
execution primitives, so its strength is declared `PARTIAL`. No full independence is
claimed.

## Scientific state

25 completed experiments, unchanged. WP-017 actual model fits 0, market results observed
false, ten fits reserved. Zero sealed queries, Champion NONE, zero paper trades, ALIGNED
semantics and real money false, all unchanged. WP-016 remains
`BLOCKED_BEFORE_EXECUTION` and unrunnable. No historical evidence was rewritten.

The prospective search burden is registered: one hypothesis, two configurations, eight
profile trials, ten reserved model fits and zero variants of every alternative.

## Owner next action

Run `WP017_CFTC_LEVERAGED_POSITIONING_V1` once from Research Lab, then send the review
bundle to the Research Director. Executing it produces the first WP-017 market result and
is the point after which the frozen success criteria may not be changed.
