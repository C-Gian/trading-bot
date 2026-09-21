# Predictive V2 deterministic calendar features V1

Status: **FROZEN BEFORE FIRST OUTER PREDICTION** (2026-09-21).

This contract governs `PREDICTIVE_V2_DETERMINISTIC_CALENDAR_FEATURES_V1`, the feature set
used by the first family of `PREDICTIVE_RESEARCH_GENERATION_V2`. It is a project-reconstructed,
deterministic calendar representation. It is not an implementation of, or claim about,
Ciclica Evoluta or Analisi Evoluta.

## Information boundary

The only input is the timezone-aware UTC decision timestamp `T`. Feature construction reads no
BTC price, volume, return, label, funding, open interest, cross-asset value, macro series, news,
sentiment, on-chain value or future timestamp. Local time, daylight-saving rules and the host
timezone never participate.

Every canonical eligible timestamp must produce a finite vector of width seven. An invalid
vector is an implementation defect and fails closed before fitting or outer prediction; it is
not imputed or silently excluded.

## Ordered feature vector

Exactly these seven features, in this order:

1. `UTC_HOUR_SIN = sin(2*pi*hour/24)`
2. `UTC_HOUR_COS = cos(2*pi*hour/24)`
3. `UTC_WEEKDAY_SIN = sin(2*pi*weekday/7)`, with Monday = 0
4. `UTC_WEEKDAY_COS = cos(2*pi*weekday/7)`
5. `UTC_YEAR_PHASE_SIN = sin(2*pi*(day_of_year-1)/days_in_UTC_year)`
6. `UTC_YEAR_PHASE_COS = cos(2*pi*(day_of_year-1)/days_in_UTC_year)`
7. `UTC_WEEKEND = 1` when weekday is Saturday or Sunday, otherwise `0`

Leap years use 366 as `days_in_UTC_year`; all other years use 365. The hour is the completed
UTC decision-bar hour, the weekday is Python/ISO-style Monday zero, and `day_of_year` is one on
January 1.

## Forbidden additions

This version contains no month dummy, day-of-month, quarter-end, halving, holiday, named
session label or other calendar feature. It has no learned feature transform and no tunable
parameter. Any addition creates a new preregistered family/version and new search burden.

## Required proofs before execution

- output is a pure function of `T`;
- changing any market value while holding `T` fixed cannot change the vector;
- advancing `T` by exactly one hour changes only the calendar state implied by that timestamp;
- UTC hour and weekday boundaries are correct;
- December 31 to January 1 wrap is deterministic;
- February 28/29 leap-year behaviour is correct;
- host local timezone and DST cannot affect the output;
- feature validity is 1.0 on all eligible development timestamps.

The executable freeze is `backend/app/predictive/calendar_features.py` and the pre-result
admission artifact hashes both this contract and that implementation.
