# WP-009 GDELT_NEWS_CONTEXT_V1_1 pause

**WP-009 IS NOT COMPLETE AND IS NOT VALIDATED.** This record exists so the work can be
resumed later without ambiguity. It does not finalize, archive, or pass WP-009.

Base HEAD for this segment: `5d0f2855afee6ba4231fae19ac8c9bdfe2b0248c`.

## Why V1 hourly acquisition was replaced

`GDELT_NEWS_CONTEXT_V1` required hourly timeline resolution. Official GDELT DOC 2.0
semantics return hourly timelines only for request spans of 72 hours through one week,
so covering 2017-08-17 through 2024-12-31 for five channels and two modes needed 3,850
credential-free requests. The endpoint persistently answered HTTP 429 during that
schedule, and the design became operationally impractical.

`GDELT_NEWS_CONTEXT_V1_1` was recorded prospectively, before any V1_1 value existed, in
`research/exogenous/GDELT-NEWS-CONTEXT-AMENDMENT-V1_1.json`. It aggregates by UTC
calendar day over calendar-year request windows: 80 requests for the full development
interval, 10 for the pilot. The five frozen semantic channels, their exact vocabulary,
both modes and `TIMELINESMOOTH=0` are unchanged; no keyword was added or removed. No
BTC price, return, outcome or strategy result was consulted for this infrastructure
decision.

## What is preserved

- All 175 V1 hourly raw response/meta pairs and their hashes, unchanged.
- `backend/app/research/gdelt.py`, the V1 acquisition module, unchanged.
- The frozen five-channel query catalog, unchanged.
- All ALFRED catalogs, amendments, manifest and integrity artifacts, unchanged.
- `docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md` and the point-in-time governance,
  unchanged.
- All earlier WP-009 commits and reports. Nothing was deleted or rewritten, including
  the failed and partial hourly acquisition evidence.

## Pilot status: PARTIAL

The deterministic pilot interval is 2017-08-17 through 2017-12-31 for all five channels
and both modes: 10 expected requests. **3 of 10 were acquired and are preserved**, each
re-verified against its frozen request identity and SHA-256 response and file hashes.
The remaining 7 are outstanding.

GDELT answered with `date_resolution = day` — validated, not assumed — and supplied the
returned global-monitoring normalization, then throttled again. 12 HTTP 429 responses
were observed; the bounded retry stop triggered, the run halted, and every successful
cache entry was preserved. No retry loop is unbounded.

Each returned series carried 135 daily points across the 137 pilot calendar days. The
two absent days remain explicit gaps and are never inferred as zero.

Because the pilot is incomplete, no V1_1 manifest, integrity artifact or derived table
was produced. Deliberately not done: the remaining pilot requests, the 2018-2024
windows, `EXOGENOUS_CONTEXT_V1`, WP-009 final validation, WP-009 finalization, and any
trading experiment. No strategy, sealed, paper, Champion or real-money state changed.

## Resuming

1. `python scripts/acquire_wp009_gdelt_daily.py` — resumable from cache. The three
   preserved responses are re-verified and never refetched; only the outstanding seven
   are attempted. Exact preserved and outstanding request identities and hashes are in
   `research/exogenous/GDELT-NEWS-CONTEXT-V1_1-PAUSE-V1.json`.
2. Once all ten exist, the same command writes
   `data/manifests/GDELT-NEWS-CONTEXT-DAILY-PILOT-DEV-v1_1.json` and
   `reports/validation/WP-009-GDELT-DAILY-PILOT-INTEGRITY.json`.
3. Only then acquire the 2018-2024 windows via
   `app.research.gdelt_daily.request_specs()`, and only after that consider the combined
   exogenous context.

Implementation: `backend/app/research/gdelt_daily.py`. Tests:
`backend/tests/test_gdelt_daily.py`.
