# POINT_IN_TIME_EXOGENOUS_DATA_V1

Status: accepted prospectively for WP-009 before bulk historical acquisition.

## Scope

This contract governs exogenous information used by Trading Bot. It covers public
GDELT news context and public ALFRED macro vintages through the development cutoff.
It creates information infrastructure only: no BTC return, trade outcome, strategy
score, model fit, or execution decision is part of this version.

## Time fields

- `observation_time`: the period the measured fact describes.
- `event_time`: when the underlying real-world event occurred, when supplied.
- `publication_time`: when the source says the item was published.
- `availability_time`: the earliest conservative UTC instant at which research code
  may use the record.
- `retrieval_time`: when this repository retrieved the source response; this is audit
  metadata and never moves availability backward.
- `vintage_start`: the ALFRED real-time date on which a value first belongs to that
  vintage state.
- `vintage_end`: the last real-time date for that state when supplied or derived from
  the next state; an open-ended value is represented explicitly.

At signal time `t`, a record is usable only when `availability_time <= t`.
Observation time alone never establishes availability.

## Conservative availability

GDELT timeline buckets are usable only after the represented UTC interval is complete.
An hourly bucket `[h,h+1h)` therefore has `availability_time = h+1h`. Publication
timestamps, when present, may delay but never accelerate that boundary.

ALFRED values retain historical vintage states. A date-level `vintage_start = d`
implies `availability_time = 00:00:00 UTC` on calendar day `d+1`. An exact historical
publication timestamp may replace that default only if its independent source and hash
were frozen before use. WP-009 uses the next-day default exclusively.

Current-revised values may not replace older vintage states. An as-of lookup chooses
only a value state whose availability is not later than the lookup time. No future
revision is backfilled, no interpolation occurs between releases, and missing remains
missing.

## Timezone and DST

All stored timestamps are timezone-aware UTC. Source date fields are interpreted as
Gregorian dates, not local midnights. Date-only availability advances by one calendar
day and is then represented at `00:00:00Z`. Hourly grids are generated arithmetically
in UTC, so daylight-saving transitions create neither repeated nor missing grid hours.
No local timezone conversion participates in availability or joins.

## Identity and retention

Every request records a canonical request identity, source family/version, retrieval
time, response/file SHA-256, and parser version. Derived datasets record file and
logical content hashes plus the complete raw-request set. Raw high-volume responses
follow `RESEARCH_ARTIFACT_STORAGE_V1` and remain local under `data/raw/`; compact
manifests and audits are tracked.

The maximum permitted development time is `2024-12-31T23:59:59Z` for source requests
and `2024-12-31T23:00:00Z` for the combined hourly grid. Acquisition and parsing fail
closed on a later request bound, record, vintage, publication, availability, or grid
timestamp. No sealed BTC path is an input to this contract.
