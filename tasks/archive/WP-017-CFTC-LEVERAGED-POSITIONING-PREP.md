# CURRENT TASK — WP-017-CFTC-LEVERAGED-POSITIONING-PREP

Status: COMPLETED_PENDING_OWNER_EXECUTION_AND_RESEARCH_DIRECTOR_REVIEW

Starting HEAD: `920376eef118c238c0e9a1c6d59d0fd0aaf08c28` on local `main`.

This checkpoint prepared exactly one new preregistered development experiment for later
Owner execution through Research Lab and stopped before any WP-017 market result.

The governed CFTC data foundation uses official Traders in Financial Futures annual
archives 2018-2024 for `BITCOIN - CHICAGO MERCANTILE EXCHANGE`, code `133741`. Report date
is never treated as availability: each report resolves an actual publication date from its
own official archived object and becomes available at 00:00:00 UTC the following calendar
day. 352 raw rows yield 351 eligible canonical rows; the 2024-12-31 report was published
2025-01-06 and is excluded as post-cutoff; zero publication dates are unresolved.

`FAM-CFTC-REGULATED-FUTURES-POSITIONING` was admitted as a new family. EXP-ML-028 adds the
single feature `CFTC_LEVERAGED_FUNDS_NET_OI_SHARE_V1` to the frozen F1-F8 set; EXP-ML-029
is the matched F1-F8 control on an identical eligible universe. WP-017 binds
`RESEARCH_RUNTIME_V2_BATCH` explicitly. Success criteria, folds, profiles, threshold,
purge and the full search restriction were frozen before any result existed.

Preregistration was committed before the Research Lab candidate was exposed, and
`scripts/check.py` verifies that ordering mechanically.

No backtest, model fit, trading result, sealed query or paper trade was created during
this preparation checkpoint. At its close, `experiments_completed` remained 25, WP-016
remained `BLOCKED_BEFORE_EXECUTION`, Champion remained NONE, and real money remained
false. See `reports/checkpoints/WP-017-CFTC-LEVERAGED-POSITIONING-PREP.md` and
`decisions/ADR-0012-WP017-CFTC-LEVERAGED-POSITIONING.md`.

The later Owner execution and formal Research Director review are recorded separately;
this archived snapshot preserves the preparation-stage truth.
