# CURRENT TASK — WP-009
# Point-in-Time Exogenous Context Foundation: News, Politics, Geopolitics, Society, and Macro

## STATUS
ACTIVE

## EXECUTOR
Primary: Codex.
Fallback/overflow: Claude Code if Codex usage is unavailable.
This task is executor-neutral. Scientific truth lives in repository artifacts.
ChatGPT / GPT-5.6 Sol remains Research Director and final scientific authority.
Astra Ultra is NOT allocated to WP-009.

## PURPOSE

WP-008 correctly tested the first fixed multivariate supervised challenger and it failed:
`FAM-SUPERVISED-LINEAR = REJECT_COST_DOMINATED`.

Primary LINEAR_FULL:
- DEFAULT `-0.1142218454 R`
- ZERO `+0.0058246386 R`
- DOUBLE `-0.2342683271 R`
- DELAY_1H `-0.1098336131 R`
- 1,003 trades
- 1/6 nonnegative folds
- min fold trades 82
- mean validation prediction/label correlation about +0.02186

This does NOT falsify the Owner's broader multi-signal thesis.
It falsifies only a fixed linear combination of eight internal market/order-flow features.

The intended long-term system is broader:
- price/pattern/trend
- volatility/liquidity/order flow
- macro/monetary conditions
- politics/regulation
- global news/geopolitics
- social conditions/sentiment
- eventually signal importance that can vary over time

Before testing a dynamic multi-source model, build point-in-time historical exogenous information
without revision leakage or future-news leakage.

WP-009 is a DATA/INFORMATION FOUNDATION checkpoint.

It executes ZERO new trading strategy experiments.
It must NOT inspect post-2024 BTC data.
It must NOT use BTC returns/outcomes to choose exogenous sources, queries, features, or thresholds.

---

## REQUIRED START

Repository: `C-Gian/trading-bot`
Branch: `main`
Required starting HEAD:
`ffeb73d6c0799ccfc09d0ee3b85c25d8e52364c2`

Reviewed predecessor:
`762b3b77f686305b1c73f19956d0b9b16b7a9b1c`

Do not create a branch.
Do not rewrite history.
Do not push.

---

## STAGE A — RECORD WP-008 RESEARCH DIRECTOR REVIEW

Create:
`reports/reviews/WP-008-RESEARCH-DIRECTOR-REVIEW.md`

Verdict:
`ACCEPTED`

Record:
- exact required base `762b3b77...`
- final HEAD `ffeb73d6...`
- 13 commits ahead / 0 behind
- real GitHub Actions run `34392236263` = SUCCESS
- preregistration commit `2d8bc11b2bbc76db387652804f7ad8c492e3d493`
- result commit `88e9c6e941be54b2fe65b802e15312eadc01c7ec`
- result commit has preregistration commit as direct parent
- SUPERVISED_FEATURES_V1 leakage audit PASS
- closest training-label outcome at least 193h before validation
- independent reconciliation PASS
- RESEARCH_ARTIFACT_STORAGE_V1 PASS
- no hyperparameter/threshold/feature search
- FAM-SUPERVISED-LINEAR = REJECT_COST_DOMINATED
- LINEAR_NO_FLOW does not replace primary
- Champion NONE
- sealed=0
- paper=0
- real money=false

Update authoritative current remote-CI truth with WP-008 SUCCESS.
Do not rewrite historical executor reports.

---

## STARTING SCIENTIFIC STATE

Expected:
- experiments_completed = 15
- material_economic_hypotheses = 6
- configuration_variants = 15
- profile_trials = 77
- supervised_model_fits = 12
- numeric_parameter_variants = 0
- adaptive_decisions = 5
- result_dependent_forks = 5
- sealed_queries = 0
- sealed_evaluations = 0
- paper_trades = 0
- Champion = NONE
- forward evidence = NONE
- real money = false

WP-009 must not increase strategy experiment/configuration/profile/model-fit counters.

Because this direction is motivated by prior results, record one additional non-trial adaptive
research direction:
- adaptive_decisions +1
- result_dependent_forks +1

Do not pretend this infrastructure direction is independent of prior results.

---

## FORBIDDEN WORK

Do NOT:
- execute a new trading backtest
- calculate BTC strategy expectancy
- correlate candidate exogenous features with BTC returns
- rank exogenous features by BTC outcome
- inspect BTCUSDT after `2024-12-31T23:59:00Z`
- acquire/query sealed BTC data
- unlock sealed queries
- modify ALIGNED
- reopen parked/rejected families
- tune any strategy
- fit a dynamic model
- choose a signal threshold
- use revised-today macro values as historical truth
- use future news at prior timestamps
- use article text/headlines to hand-pick historical events after seeing BTC moves
- scrape paywalled article bodies
- introduce paid APIs, credentials, cloud billing, or new external accounts
- ask Owner for API keys
- expand strategy asset universe
- SHORT
- leverage/perpetuals
- paper trading
- enable Analyze Market
- product LONG/NO_TRADE advice
- Champion promotion
- real-money/exchange execution
- create branch
- push

---

## STAGE B — POINT-IN-TIME EXOGENOUS DATA CONTRACT V1

Create:
`docs/contracts/POINT_IN_TIME_EXOGENOUS_DATA_V1.md`

Define separately:
- observation_time
- event_time
- publication_time
- availability_time
- retrieval_time
- vintage_start
- vintage_end
- source/version/retrieval hashes

Core rule:
At signal time t, exogenous information is usable only if:
`availability_time <= t`

Historical observation time alone is never sufficient.

For revised macro data:
- current values are not automatically valid historically
- use historical vintage/real-time metadata
- no post-hoc revised data replaces what was knowable then

If source metadata is date-level only:
default availability:
`00:00:00 UTC on the NEXT calendar day`
unless an exact historical publication timestamp is independently sourced and frozen before use.

Document timezone/DST rules.

---

## STAGE C — SOURCE CATALOG V1

Create:
`research/exogenous/SOURCE_CATALOG_V1.json`
and:
`reports/research/WP-009-EXOGENOUS-SOURCE-SELECTION.md`

Selection is based on information semantics and point-in-time quality, not BTC outcomes.

Authorize exactly two source families.

### 1. GDELT DOC 2.0

Purpose:
global news attention/tone proxies for crypto, policy, monetary-policy, geopolitical and social
information environments.

Requirements:
- public credential-free HTTPS only
- official GDELT DOC 2.0 API
- exact STARTDATETIME/ENDDATETIME
- no smoothing
- machine-readable JSON/CSV
- raw response hash + request identity
- development data only through `2024-12-31T23:59:59Z`
- never request 2025+
- document changing monitoring universe
- use returned normalization when available
- no article body scraping

### 2. ALFRED

Purpose:
macro/financial context with historical vintage information.

Requirements:
- St. Louis Fed ALFRED historical vintage/real-time data
- credential-free public download interface only
- no Owner key/account request
- no current-revised-only FRED substitution
- retain only vintage/real-time history through `2024-12-31`
- raw request/file hashes

If credential-free machine-readable ALFRED acquisition cannot be made deterministic:
- do not silently substitute a weaker source
- complete adapter/tests with public examples/synthetic fixtures
- classify acquisition `BLOCKED_CREDENTIAL_FREE_AUTOMATION_UNAVAILABLE`
- continue GDELT foundation
- WP-009 may return PARTIAL, but do not weaken point-in-time rules

---

## STAGE D — FREEZE GDELT QUERY TAXONOMY BEFORE VALUES

Create:
`research/exogenous/GDELT_QUERY_CATALOG_V1.json`

Commit before historical news acquisition.
Do not inspect BTC outcomes or GDELT time-series values before freezing.

Exactly five semantic channels:

### Q1 CRYPTO_CORE
Transparent OR query for:
- bitcoin
- cryptocurrency

### Q2 CRYPTO_POLICY
Crypto core concept AND one fixed policy vocabulary:
- regulation
- regulator
- regulatory
- law
- ban

### Q3 CENTRAL_BANK_POLICY
Fixed institutions:
- Federal Reserve
- European Central Bank
- Bank of England
- Bank of Japan

### Q4 GEOPOLITICAL_STRESS
Fixed vocabulary:
- war
- conflict
- sanctions
- invasion
- missile

### Q5 SOCIAL_STRESS
Fixed vocabulary:
- protest
- riot
- unrest
- strike

Validate query syntax against official GDELT semantics before historical values are fetched.

Document taxonomy limitations.
No vocabulary expansion after values are observed.

---

## STAGE E — GDELT HOURLY ACQUISITION V1

Create version:
`GDELT_NEWS_CONTEXT_V1`

Coverage:
`2017-08-17T00:00:00Z` through `2024-12-31T23:59:59Z`

For every frozen query acquire:
1. TimelineVolRaw
2. TimelineTone

Requirements:
- `TIMELINESMOOTH=0`
- exact UTC STARTDATETIME/ENDDATETIME
- chunks short enough to force hourly, never daily, timeline resolution
- validate actual response resolution
- deduplicate chunk boundaries
- never fetch 2025+

Canonical hourly columns per channel:
- matched_articles
- monitored_articles_norm when supplied
- coverage_share = matched_articles / norm if norm>0
- average_tone
- data_available
- source_request_id

Do not create rolling means, z-scores or trading transforms in WP-009.

Missing hour is not automatically zero unless source semantics prove monitored coverage existed and
the query had zero matches.

Use RESEARCH_ARTIFACT_STORAGE_V1 for high-volume raw responses.

Create:
`data/manifests/GDELT-NEWS-CONTEXT-DEV-v1.json`
`reports/validation/WP-009-GDELT-INTEGRITY.json`

Validate:
- no 2025 rows
- no duplicate hour/channel
- strictly increasing hours
- no smoothing
- hourly resolution
- explicit gaps
- request/response hashes
- deterministic raw->derived rebuild

---

## STAGE F — FREEZE ALFRED SERIES CATALOG

Before values:
create:
`research/exogenous/ALFRED_SERIES_CATALOG_V1.json`

Use exactly these eight series if historical real-time data is available:

1. DFF — Effective Federal Funds Rate
2. DGS10 — 10-Year Treasury Constant Maturity Rate
3. T10Y2Y — 10-Year minus 2-Year Treasury spread
4. VIXCLS — CBOE Volatility Index
5. NFCI — Chicago Fed National Financial Conditions Index
6. WALCL — Federal Reserve total assets
7. CPIAUCSL — CPI all urban consumers
8. UNRATE — unemployment rate

Do not add/remove series based on values or BTC outcomes.

Record units, frequency, seasonal adjustment, source/release, revision semantics and raw identity.

---

## STAGE G — ALFRED POINT-IN-TIME NORMALIZATION

Create version:
`ALFRED_MACRO_CONTEXT_V1`

For every value/revision retain:
- observation date
- value
- vintage/real-time start
- vintage/real-time end when supplied
- conservative availability_time

Default:
`availability_time = 00:00 UTC on the day AFTER vintage_start`

unless exact historical timestamp support is independently verified and frozen.

No future revision may leak backward.
No interpolation between releases.
Missing stays missing.

At signal time t:
`asof_value(series,t)` uses only information whose conservative availability_time <= t.

Create:
`data/manifests/ALFRED-MACRO-CONTEXT-DEV-v1.json`
`reports/validation/WP-009-ALFRED-INTEGRITY.json`

Tests must prove:
- later revision cannot leak backward
- next-day availability
- current known value cannot appear before historical vintage start

---

## STAGE H — EXOGENOUS CONTEXT V1

Create:
`EXOGENOUS_CONTEXT_V1`

Generate an hourly UTC grid from:
`2017-08-17T00:00:00Z`
to:
`2024-12-31T23:00:00Z`

The grid is timestamp-generated only.

Do NOT load BTC price/return/outcome columns to build WP-009 context.

Attach only exogenous data satisfying:
`availability_time <= t`

News:
completed GDELT hours only.

Macro:
latest conservatively available ALFRED value.

Retain:
- source availability flags
- age since macro observation
- age since last vintage/revision
- source/query IDs
- raw levels/news measures

Do NOT full-history standardize.
Do NOT calculate BTC correlations.
Do NOT create trading score.

Create:
`data/manifests/EXOGENOUS-CONTEXT-DEV-v1.json`

High-volume dataset may remain local under existing data policy; tracked manifest required.

---

## STAGE I — INDEPENDENT POINT-IN-TIME ORACLE

Implement an independent as-of audit path not calling production join.

Use a frozen hash-based timestamp sample across every calendar quarter.

Reconstruct from raw source/vintage records exactly what information was available at each sampled t.

Stress:
- macro revision dates
- month/year boundaries
- GDELT chunk boundaries
- missing hours
- 2020 high-news periods
- DST transitions
- cutoff boundary

No BTC outcomes.

Create:
`reports/validation/WP-009-EXOGENOUS-ASOF-RECONCILIATION.json`

Exact mismatch fails.

---

## STAGE J — SOURCE DRIFT / COVERAGE REPORT

Create:
`reports/research/WP-009-EXOGENOUS-COVERAGE.md`

Without BTC correlation report:

GDELT per channel:
- start/end
- missing hours
- matched-hour fraction
- norm availability
- source availability by year
- obvious source/API outages
- retrieval completeness

ALFRED per series:
- first usable availability
- last usable <= cutoff
- observations
- revisions/vintage states
- missingness on hourly grid

Document GDELT monitoring-universe drift as a limitation.

Do not select/exclude sources based on noisy values.

---

## STAGE K — FUTURE ADAPTIVE MULTI-SIGNAL ARCHITECTURE DESIGN ONLY

Create:
`research/design/ADAPTIVE_MULTISIGNAL_ARCHITECTURE_OPTIONS_V1.md`

NO MARKET RESULTS.

Translate the Owner requirement:
signal importance may change through time and regime.

Analyze exactly three future candidate architectures.

### Candidate A — exponentially weighted dynamic linear model
Discuss:
- interpretability
- decay/regularization degrees of freedom
- leakage protection
- coefficient stability
- half-life tuning risk

### Candidate B — regime-conditioned mixture of linear experts
Discuss:
- regime-definition risk
- min samples per regime
- transitions
- avoiding outcome-defined regimes

### Candidate C — online Bayesian/state-space dynamic regression
Discuss:
- uncertainty estimates
- process-noise hyperparameters
- complexity
- hidden-tuning risk

For each include:
- required data
- free hyperparameters
- deterministic controls
- failure modes
- integration of internal + exogenous features
- how time-varying importance is audited

Do NOT select based on BTC result.
Do NOT execute any architecture.

Research Director chooses after WP-009 review.

---

## STAGE L — DYNAMIC SIGNAL IMPORTANCE GOVERNANCE

Create:
`docs/contracts/DYNAMIC_SIGNAL_IMPORTANCE_GOVERNANCE_V1.md`

Future adaptive models must expose signal influence.

Where model class permits, retain/reconstruct at prediction time:
- active feature values
- model coefficients/weights
- standardized contribution per feature
- grouped contribution:
  - MARKET_PRICE
  - VOLATILITY_LIQUIDITY
  - ORDER_FLOW
  - MACRO_FINANCIAL
  - CRYPTO_NEWS_POLICY
  - GEOPOLITICAL
  - SOCIAL
- prediction before execution filter
- model version
- training cutoff

Historical influence analysis must never use future-fitted weights.

For nonlinear interactions, future protocol must freeze deterministic attribution method before results.

No post-hoc attribution shopping.

---

## STAGE M — SEARCH / ADAPTIVE MEMORY

WP-009 creates no strategy family and no experiment.

Record one result-dependent direction:
`EXOGENOUS_AND_DYNAMIC_MULTISIGNAL_FOUNDATION`

No new:
- economic hypothesis
- configuration
- profile
- model fit
- numeric variant

Update failure memory:
- fixed internal-feature linear combination was cost-dominated
- this does NOT falsify dynamic weighting or exogenous information
- linear-family rescue remains blocked

Add exogenous assets to research map as infrastructure, not edge evidence.

---

## STAGE N — SEALED STATE

No sealed data acquisition/query.

Remain:
- SEALED_EVALUATION_V1_1
- BTC authorized queries = 0
- consumed = 0
- dataset = RESERVED_NOT_ACQUIRED

Do not acquire post-2024 exogenous development rows either.

---

## STAGE O — UI/API

Research Lab may show:
- exogenous foundation status
- GDELT version/coverage
- ALFRED version/coverage or blocked status
- as-of reconciliation
- adaptive multi-signal design status
- sealed locked 0/0
- Champion NONE

Do not display news as live trading advice.
Do not enable Analyze Market.

---

## STAGE P — STATE

If both sources complete, preserve:
- experiments_completed = 15
- material_economic_hypotheses = 6
- configuration_variants = 15
- profile_trials = 77
- supervised_model_fits = 12
- numeric_parameter_variants = 0

Update:
- adaptive_decisions = 6
- result_dependent_forks = 6
- latest reviewed checkpoint = WP-008
- latest executor checkpoint = WP-009
- WP-008 remote CI SUCCESS
- exogenous data contract/version/status/hashes
- GDELT status
- ALFRED status
- combined context status
- as-of reconciliation
- next recommended work:
  `RESEARCH_DIRECTOR_SELECT_ADAPTIVE_MULTISIGNAL_ARCHITECTURE_AFTER_WP009_REVIEW`

Preserve:
- sealed=0
- paper=0
- Champion NONE
- forward evidence NONE
- real money=false

If ALFRED is blocked, report state truthfully.

---

## STAGE Q — VALIDATION

Strengthen `python scripts/check.py`.

Validate:

WP-008:
- exact base/head
- real CI SUCCESS
- prereg before result
- old evidence unchanged

Exogenous governance:
- contract exists
- source catalogs frozen before values
- no BTC outcome-based source selection
- no strategy experiment
- no BTC correlation output

GDELT:
- exactly five channels
- query catalog predates historical acquisition
- no query tuning
- no smoothing
- hourly resolution
- <= cutoff
- hashes
- boundary dedupe
- no article body scraping
- deterministic rebuild

ALFRED:
- exactly eight series
- credential-free
- vintage/real-time data
- no current revised substitution
- conservative availability
- no revision leakage
- <= cutoff

Combined:
- timestamp-only grid
- BTC prices/outcomes unused
- as-of only
- no full-history normalization
- independent oracle PASS
- no post-cutoff

Adaptive design:
- exactly three options
- zero market tests
- dynamic importance governance exists

Counters:
- experiments 15
- hypotheses 6
- configurations 15
- profiles 77
- model fits 12
- adaptive counts truthful
- numeric variants 0

Safety:
- sealed 0
- paper 0
- Champion NONE
- real money false
- no credentials introduced

Software:
- backend tests
- frontend tests/build
- lint
- format
- typing
- clean-checkout no-data validation
- clean tree

Remote CI executor report:
`PENDING_PUSH`

---

## DEFAULT BRANCH HOUSEKEEPING

Remote default branch may still be the historical WP-001 branch.
Do not block WP-009.
If safe already-authenticated administration exists without new credentials, set default to main.
Otherwise report PENDING.
Do not delete historical branches.

---

## COMMIT CHRONOLOGY

Recommended:

1. `docs: record WP-008 Research Director acceptance`
2. `docs: define point-in-time exogenous data governance`
3. `research: freeze external source and query catalogs`
4. `feat: build and audit GDELT news context`
5. `feat: build and audit ALFRED macro context`
6. `feat: build point-in-time exogenous context and oracle`
7. `docs: design adaptive multi-signal architecture options`
8. `feat: expose exogenous research status`
9. `chore: complete WP-009 state validation and checkpoint`

No market-result commit exists in WP-009.

---

## CHECKPOINT

Create:
- `reports/checkpoints/WP-009.md`
- `reports/research/WP-009-EXOGENOUS-FOUNDATION.md`
- `tasks/archive/WP-009.md`

Mark CURRENT_TASK completed only on structural success.

---

## REQUIRED EXECUTOR RESPONSE

Return only:

```text
WP-009: PASS | PARTIAL | FAIL

Branch:
HEAD:
Base reviewed HEAD:
Remote CI:
- PENDING_PUSH

WP-008 review:
- verdict:
- real CI evidence:
- prereg/result chronology:
- linear family disposition:

Point-in-time governance:
- version:
- date-only availability rule:
- post-cutoff protection:

GDELT:
- version:
- query catalog frozen before acquisition:
- channels:
- coverage:
- hourly rows:
- missing hours:
- smoothing:
- raw/request hashes:
- integrity:
- limitations:

ALFRED:
- version:
- acquisition status:
- series:
- credential-free:
- coverage:
- vintage/revision handling:
- next-day conservative availability:
- integrity:
- limitations:

Combined exogenous context:
- version:
- BTC prices/outcomes used to build: NO
- rows:
- coverage:
- manifest/hash:
- independent as-of oracle:

Adaptive multi-signal design:
- candidate A:
- candidate B:
- candidate C:
- market tests executed: 0
- dynamic signal importance governance:

Scientific accounting:
- strategy experiments=15
- material economic hypotheses=6
- configurations=15
- profile/seed trials=77
- supervised model fits=12
- numeric parameter variants=0
- adaptive decisions=<truth>
- result-dependent forks=<truth>
- sealed_evaluations=0
- sealed_queries=0
- paper_trades=0
- champion=NONE
- forward_evidence=NONE
- real_money=false

Validation:
- <one concise line>

Forbidden-work check:
- BTC outcome-based source selection: absent
- strategy backtest: absent
- feature/keyword tuning: absent
- post-cutoff BTC access: absent
- post-2024 exogenous development data: absent
- sealed BTC access: absent
- paid API/credentials: absent
- non-BTC strategy expansion: absent
- SHORT/leverage: absent
- paper trading: absent
- real-money functionality: absent
- new branch: absent

External housekeeping:
- default branch main: DONE | PENDING

Material deviations:
- none
  OR
- <only material deviations>

Next recommendation:
- Research Director chooses one adaptive multi-signal architecture for a separate preregistered WP; no automatic sealed query.
```

Do not paste raw logs unless PARTIAL/FAIL and essential.
