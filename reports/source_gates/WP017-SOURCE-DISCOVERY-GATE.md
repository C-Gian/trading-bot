# WP-017 source discovery gate

## Conclusion

`RECOMMENDED_SOURCE = CFTC_CME_BITCOIN_COT`

This is a source-integrity gate, not WP-017 preregistration or execution. It performed
zero backtests, model fits, strategy tests, sealed queries, or joins to BTC outcomes.
WP-016 remains blocked. CFTC CME Bitcoin COT is the only reviewed design that combines
a defensible point-in-time rule, official compact history, stable identity and practical
local acquisition. Recommendation means “eligible for Research Director hypothesis
design,” not “predictive” or “profitable.”

| Contract | CFTC CME Bitcoin COT | GDELT 2 bulk | Common Crawl News |
|---|---|---|---|
| POINT_IN_TIME | PASS | PASS | PASS |
| HISTORICAL_COVERAGE | PARTIAL | PASS | PASS |
| REPRODUCIBILITY | PASS | PASS | PASS |
| SEMANTIC_STABILITY | PASS | PASS | PASS |
| LOCAL_FEASIBILITY | PASS | PARTIAL | FAIL |
| ORTHOGONAL_INFORMATION | HIGH | HIGH | HIGH |
| REVISION_RISK | MEDIUM | MEDIUM | LOW |
| DATA_VOLUME | 3.77 MB compressed | about 1–2 TiB GKG if acquired naively | about 40.3 TiB compressed |

## Evaluation rule

Point-in-time PASS requires an observation or processing timestamp that proves the
underlying information had already been public, plus a deterministic conservative lag
and fail-closed handling of ambiguous records. A publisher-supplied article date alone
does not qualify. Reproducibility requires source-addressed raw artifacts that can be
preserved and hashed. No candidate was evaluated against subsequent market behavior.

## Source A — CFTC CME Bitcoin COT

### Official identity and fields

The CFTC describes COT as Tuesday open-interest data that is ordinarily released Friday
at 3:30 p.m. Eastern; the report date is therefore not its availability date. The same
official page says errors are corrected in subsequent reports and that historical data
are not revised after publication. [CFTC COT overview and FAQ](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)

The official TFF archive supplies annual compressed text/Excel files. It covers the
financial-futures format from September 2009 and exposes year-addressed files including
2017–2024. [CFTC historical compressed files](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm)

The scoped 2024-12-31 report identifies `BITCOIN - CHICAGO MERCANTILE EXCHANGE`, CFTC
market code `133741`, and contract units of five bitcoins. [Official 2024-12-31 TFF report](https://www.cftc.gov/sites/default/files/files/dea/cotarchives/2024/futures/financial_lf123124.htm)
The TFF schema provides Dealer/Intermediary, Asset Manager/Institutional, Leveraged
Funds, Other Reportables and Nonreportable long/short/spread positions, changes,
percentages and trader counts. [Official TFF variable definitions](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalViewable/cotvariablestfm)

### Coverage and pilot

A non-market pilot retrieved the eight official `fut_fin_txt_YYYY.zip` files for
2017–2024 in memory and hashed their exact bytes. Total compressed size was 3,771,554
bytes. Filtering only the stable market code/name yielded 352 weekly rows: none in 2017,
39 from 2018-04-10 onward, 52 in each of 2019–2023, and 53 in 2024, ending exactly
2024-12-31. The JSON artifact records every archive SHA-256. No file was joined to BTC
prices and no strategy quantity was calculated.

Coverage is PARTIAL because CME Bitcoin observations begin 2018-04-10, after the
development domain begins. Any later study must use a preregistered matched universe;
it may not fill the missing prefix.

### Point-in-time and revisions

Earliest safe availability is frozen for a future data foundation as:

> 00:00 UTC on the calendar day after the actual CFTC publication date.

Ordinary releases use the official Friday schedule. Holidays, shutdowns, outages and
corrections use the CFTC’s dated exception records. The official archive records, among
other cases, shutdown backlogs and the 2023 reporting delay/recovery schedule.
[CFTC historical special announcements](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalSpecialAnnouncements/index.htm)
Any observation whose actual publication date cannot be reconstructed from official
evidence is ineligible. Tuesday positions are never made available on Tuesday.

Revision risk is MEDIUM rather than LOW: source corrections, delayed releases and
reporting classification changes exist. They are tractable because CFTC records the
exceptions and says historical published values are not silently updated. Raw annual
bytes, source URL, retrieval metadata and local SHA-256 must all be preserved.

### Verdict

POINT_IN_TIME PASS; HISTORICAL_COVERAGE PARTIAL; REPRODUCIBILITY PASS;
SEMANTIC_STABILITY PASS; LOCAL_FEASIBILITY PASS; ORTHOGONAL_INFORMATION HIGH.

COT measures regulated institutional futures positioning, unlike existing Binance spot
F1–F8 and unlike the already-tested perpetual funding context. It is recommended for
Research Director hypothesis design, without any claim about expected sign or utility.

## Source B — GDELT 2 contemporaneous bulk archive

### Archive design and timestamps

GDELT 2 exposes Events, Mentions and GKG timestamped bulk file families and documents a
15-minute cadence. [Official GDELT data catalog](https://gdeltproject.org/data.html)
The 2.0 launch record dates coverage from 2015-02-19 and documents the continuously
updated master and last-update lists. [GDELT 2.0 launch documentation](https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/)

The Event/Mentions codebook defines `DATEADDED` and `MentionTimeDate` as UTC processing
or update instants. [GDELT Event 2.0 codebook](https://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf)
The GKG codebook states that `GKGRECORDID` starts with the UTC batch timestamp in which
the record was created, distinct from the document publication date.
[GDELT GKG 2.1 codebook](https://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf)

Consequently a defensible prospective rule is processing batch timestamp plus 24 hours,
using first-observation semantics. Publisher document dates are forbidden as the
availability timestamp. Exact timestamped ZIPs must be preserved with the size/MD5
enumerated by the [official master file](https://data.gdeltproject.org/gdeltv2/masterfilelist.txt)
and a locally computed SHA-256. Invalid or absent processing timestamps fail closed.

### Pilot, revisions and feasibility

A non-market pilot read representative timestamped files only. A
`20170817000000.gkg.csv.zip` sample was 8,387 bytes, two rows and SHA-256
`f15e1dd77e118d53650175059bafe0501fd44a2b05ec027da341ed27bff3671a`.
A `20241231234500.gkg.csv.zip` sample was 4,570,971 bytes, 1,152 rows and SHA-256
`e36049158ef491379eae9fb6685017b5170658c82520c65f70ab6b4795bfd44a`.
The master list itself was about 128 MB at retrieval.

Point-in-time status passes because records carry contemporaneous GDELT processing
instants, including when older articles are discovered later. Revision risk remains
MEDIUM: corrections, follow-on mentions and duplicated documents can create new records,
so a future foundation must retain the first observed record rather than retrospectively
collapse to the latest representation.

Naive GKG acquisition for 2017–2024 is approximately 1–2 TiB compressed. Events and
Mentions are smaller, but a deterministic streamed Bitcoin subset, frozen query rules
and deduplication must be proven before allocation. This is not the rate-limited Timeline
API used by paused WP-009, whose historical work remains unchanged.

### Verdict

POINT_IN_TIME PASS; HISTORICAL_COVERAGE PASS; REPRODUCIBILITY PASS;
SEMANTIC_STABILITY PASS; LOCAL_FEASIBILITY PARTIAL; ORTHOGONAL_INFORMATION HIGH.

Hold for a bounded streaming/data-foundation pilot. Do not resume the WP-009 Timeline
API acquisition and do not preregister a strategy yet.

## Source C — Common Crawl News

### Archive design and timestamps

Common Crawl announced CC-NEWS in 2016 as daily WARC files under date-addressed paths,
published shortly after articles are written or crawled.
[Official CC-NEWS announcement](https://commoncrawl.org/blog/news-dataset-available)
Common Crawl documents that WARC records preserve raw HTTP responses, `WARC-Date`
capture time and payload/block digests. [Official data access guide](https://commoncrawl.org/get-started)

This supports an earliest-safe rule of 00:00 UTC on the calendar day after the later of
the WARC capture and archived-object Last-Modified timestamp. Article metadata is not
the clock. A future manifest must pin WARC path, record ID and content digest; malformed
records fail closed.

### Coverage and feasibility

The pilot enumerated every official monthly `warc.paths.gz` file from 2017-08 through
2024-12: 89 months and 41,292 WARC objects. The first and last scoped manifests are
directly date-addressed: [2017-08 paths](https://data.commoncrawl.org/crawl-data/CC-NEWS/2017/08/warc.paths.gz)
and [2024-12 paths](https://data.commoncrawl.org/crawl-data/CC-NEWS/2024/12/warc.paths.gz).
At roughly 1 GiB compressed per object, the scoped corpus is approximately 40.3 TiB.

Raw capture semantics and immutable content digests make revision risk LOW. But this
gate did not establish an official selective CC-NEWS URL index equivalent to the CDX
indices documented for main crawls. Full local scanning is not feasible, and a
future-safe publisher or keyword universe cannot be chosen using future outcomes.

### Verdict

POINT_IN_TIME PASS; HISTORICAL_COVERAGE PASS; REPRODUCIBILITY PASS;
SEMANTIC_STABILITY PASS; LOCAL_FEASIBILITY FAIL; ORTHOGONAL_INFORMATION HIGH.

Reject for the local V1 path unless an official selective CC-NEWS index is established.

## Next work package

`RESEARCH_DIRECTOR_REVIEW_AND_WP017_CFTC_COT_HYPOTHESIS_DESIGN`

The Research Director should first accept or reject this source recommendation, then
define the actual WP-017 hypothesis and matched-universe design. No WP-017 experiment ID,
feature, model configuration or search allocation has been reserved here.
