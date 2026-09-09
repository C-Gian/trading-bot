# WP-005 Research Director review

## Verdict

- Structural verdict: **ACCEPTED**
- Scientific conclusion: **ALIGNED_DIAGNOSTIC_SUPPORTED_BUT_INCONCLUSIVE**
- Underlying WP-004 family classification remains **INCONCLUSIVE**
- Final WP-005 HEAD: `444172a359e2663887624da82254cc2185ff85e1`
- True WP-005 starting HEAD: `3fdeffe5de59ebf3d80dcb70e26fe8dff8a28153`

## Report-base reporting error

The WP-005 executor chat report printed `2b40aa03cfc05ac7f57d269f596f1ebacdc9d356`
as its base reviewed HEAD. That commit is the WP-004 reviewed base, not the WP-005
merge base. Git ancestry was independently verified: the true WP-005 start and merge
base is `3fdeffe5de59ebf3d80dcb70e26fe8dff8a28153`, which is a descendant of
`2b40aa03cfc05ac7f57d269f596f1ebacdc9d356` and an ancestor of
`444172a359e2663887624da82254cc2185ff85e1`.

This is a **non-material reporting error**. No committed scientific artifact,
hash, result, admission or chronology depended on the printed value. The original
WP-005 report is not rewritten. The authoritative identity now lives in
`governance/WORK_PACKAGE_CHRONOLOGY.json`, and `validate_report_bases` fails closed
if any work package from WP-006 onward states a base other than its declared
starting HEAD.

## Real remote continuous integration

Real GitHub Actions after push: **SUCCESS**.

Workflow `check`, branch `main`, event `push`, run
[34355806303](https://github.com/C-Gian/trading-bot/actions/runs/34355806303) for
head `444172a359e2663887624da82254cc2185ff85e1`, completed `success` at
`2026-09-09T13:15:07Z`. The observation is recorded in
`reports/reviews/WP-005-CI-EVIDENCE.json` from an unauthenticated official GitHub
API read. Historical WP-005 result artifacts keep their recorded `PENDING_PUSH`
value; they are not mutated to replace it.

## Verified facts

- Raw `2017-12` and `2018-02` archive SHA-256 hashes match the accepted manifest
  exactly (`3d41da2d...`, `131667f0...`).
- The 21,602 off-grid rows already exist in the accepted official Binance archives;
  they are a source-archive property, not a pipeline defect.
- Raw to canonical timestamp and OHLCV payload mapping is exact: zero timestamp
  mismatches and zero payload mismatches.
- No validation or warm-up interval intersects a quarantined bucket
  (`{"1h": 0, "4h": 0}`).
- The unchanged quarantine reproduces 363 1h and 92 4h buckets with zero repairs
  or fills.
- The exact 12/12 WP-004 profile replay reconciles to identical canonical content
  hashes across 72 fold components, creating zero new experiment results.
- Independent feature and result reconciliation: **PASS**, zero feature mismatches.
- `SEARCH_MEMORY_V2` is active and validated, with nine frozen legacy signatures.
- The matched-control protocol was committed before its results; ancestry proves
  the protocol commit precedes every diagnostic result commit.
- All 32 fixed random-gate seeds are preserved with no selection or replacement.
- Matched parent breakout default expectancy: `-0.0547388706 R`.
- ALIGNED default expectancy: `+0.1373934676 R`.
- Matched-parent delta: `+0.1921323382 R`.
- Matched random-gate q90: `+0.1107856627 R`; ALIGNED exceeds q90 by
  `+0.0266078049 R`.
- Strategy experiments remain 9; Champion `NONE`; sealed evaluations 0;
  paper trades 0; real money `false`.
- The one mechanical post-execution aggregation failure is preserved and finalized
  no result artifact.

## Interpretation

The comparability question raised at WP-004 review is resolved in ALIGNED's favour
diagnostically: its edge is not explained by the parent breakout mechanism alone,
nor by random selection of the same number of parent candidates per fold. That is a
diagnostic result, not a significance test and not independent evidence.

The blocking WP-004 limitations are unchanged: fold sparsity, only 3/6 nonnegative
folds, and positive-fold profit concentration above 50%. ALIGNED therefore stays
`INCONCLUSIVE` and is **not** sealed-evaluation eligible.

## Directions

- FAM-BREAKOUT stays exhausted. Do not reopen it.
- Do not modify ALIGNED, its thresholds, or its records.
- Do not promote a Champion and do not query sealed data.
- Build sealed-evaluation infrastructure before any candidate can ever qualify.
- Allocate exactly one genuinely new algorithmic family for WP-006, subject to a
  governed SEARCH_MEMORY_V2 novelty gate that must be passed before any market
  result is produced.
