# CURRENT TASK — WP-001 Foundation + Development Data

## Status

COMPLETED

## Work package

`WP-001 — Repository bootstrap, scientific operating system, local web skeleton, and BTCUSDT development-data foundation`

This is intentionally a large autonomous work package. Complete all stages in one run
unless a genuine non-recoverable blocker is encountered.

Do not stop after each stage to ask for review.

## Context

The repository is brand new.

The remote repository is:

`C-Gian/trading-bot`

The Owner has already cloned it locally and placed the initial canonical Markdown
files in the working tree. The remote may still be empty.

Do not assume the initial files are already committed.

## Goal

Build the smallest credible laboratory and local application foundation that can later
support strategy research without creating fake evidence or contaminating reserved
historical evaluation data.

This work package combines Roadmap Phase 0 and Phase 1 because neither requires
strategy search.

At completion we want:

- reproducible repository/governance structure;
- clean research record-keeping conventions;
- deterministic validation;
- FastAPI + React/TypeScript/Vite local application skeleton;
- one-command local development;
- real backend health integration;
- official BTCUSDT spot 1m historical DEVELOPMENT data only;
- immutable raw-source archive locally;
- normalized Parquet;
- deterministic 1h and 4h derived bars;
- integrity/gap reports and cryptographic manifests;
- read-only historical candle API;
- historical-development candlestick visualization clearly labelled as such;
- zero strategies;
- zero backtests;
- zero trading experiments;
- zero paper trades;
- zero sealed queries;
- no real-money functionality.

## Absolutely forbidden

Do not:

- research trading strategies;
- implement research indicators;
- optimize parameters;
- run backtests;
- create a Champion;
- fabricate `NO_TRADE` or `LONG` decisions;
- generate synthetic market history except tiny unit-test fixtures;
- use post-cutoff BTCUSDT data;
- inspect or summarize the reserved historical interval;
- access ETH or other assets;
- implement SHORT/perpetuals;
- add ML/deep learning;
- implement paper-trade signals;
- implement exchange-order execution;
- create real-money controls or credential hooks;
- build V2 server/cloud infrastructure.

## Stage 0 — Preserve the seed baseline

Before restructuring files:

1. inspect the working tree;
2. locate the supplied initial project Markdown documents case-insensitively:
   - `PROJECT_BRIEF.md`
   - `ROADMAP.md`
   - `CURRENT_STATE.md`
   - `WEB_APP_SPEC.md`
   - `SCIENTIFIC_CONSTITUTION.md`
   - `TECH_STACK.md`
   - `AGENTS.md`
   - `CURRENT_TASK.md`
3. do not rewrite the six supplied product/scientific canon documents before they have
   been captured in Git history;
4. if the repository has no commits, create an initial commit on `main` containing the
   supplied seed files exactly as found;
5. if a valid seed commit already exists, do not create a redundant one;
6. create exactly one work branch:

   `work/wp-001-foundation-data`

7. perform all implementation work on that branch;
8. do not push.

If case/naming normalization is needed, do it only after the baseline commit.

## Stage 1 — Normalize repository information architecture

Create the following authoritative structure:

```text
AGENTS.md
README.md

docs/
  canonical/
    PROJECT_BRIEF.md
    ROADMAP.md
    WEB_APP_SPEC.md
    TECH_STACK.md
    INITIAL_STATE.md
  architecture/
    PHASE0_ARCHITECTURE.md
  contracts/
    EXPERIMENT_LIFECYCLE.md
    EVIDENCE_STAGES.md
    MARKET_DATA_CONTRACT.md
    RECORD_KEEPING.md

governance/
  SCIENTIFIC_CONSTITUTION.md

state/
  current_state.json
  README.md

decisions/
  INDEX.md
  ADR-0001-HISTORICAL-DEVELOPMENT-BOUNDARY.md

tasks/
  CURRENT_TASK.md
  archive/

reports/
  checkpoints/

contracts/
  project_state.schema.json
  experiment_preregistration.schema.json
  experiment_result.schema.json
  dataset_manifest.schema.json

research/
  experiments/
  fixtures/

data/
  raw/
  canonical/
  derived/
  manifests/
  reports/

backend/
frontend/
scripts/
.github/workflows/
```

Rules:

- Preserve the original `CURRENT_STATE.md` as `docs/canonical/INITIAL_STATE.md`.
- `state/current_state.json` becomes the ONLY authoritative editable current-state
  document.
- Do not maintain a second prose "current state" by hand.
- Raw/canonical/derived market data are local artifacts and must not be committed to
  Git.
- Dataset manifests and concise integrity reports should be committed.
- Large logs/cache/build artifacts must be gitignored.
- Empty placeholder directories may use `.gitkeep` only where useful.

## Stage 2 — Install the scientific operating system

### Scientific Constitution

Move/copy the supplied Constitution verbatim to:

`governance/SCIENTIFIC_CONSTITUTION.md`

Do not improve, paraphrase, weaken, or silently edit it.

### Record-keeping model

Create `docs/contracts/RECORD_KEEPING.md`.

It must define:

- one machine-readable current state;
- ADRs for material decisions;
- one concise immutable checkpoint report per completed work package;
- one directory per material experiment;
- preregistration before experiment execution;
- terminal results never rewritten after observation;
- failures/negative results retained;
- indexes summarize and link records rather than duplicate them;
- canonical docs are not journals;
- verbose execution logs are not canonical project history;
- Git history is part of the audit trail.

### Experiment lifecycle

Define prospectively:

`DRAFT -> PREREGISTERED -> RUNNING -> COMPLETED | FAILED | CANCELLED`

No actual trading experiment is created in WP-001.

Test fixtures must be unmistakably synthetic and live only under test/fixture paths.

### JSON contracts

Use one documented modern JSON Schema draft.

Create deterministic schemas and validators for:

- project state;
- experiment preregistration;
- experiment result;
- dataset manifest.

Preregistration must require at minimum:

- experiment ID/version;
- UTC creation time;
- hypothesis;
- rationale;
- research question/scope;
- dataset reference/intended dataset contract;
- primary metric;
- secondary metrics;
- evaluation design;
- leakage controls;
- cost/execution reference where applicable;
- parameter/search space;
- explicit trial/search budget;
- stopping rule;
- deterministic seeds where applicable;
- code/config reference;
- status.

Experiment result must link to a preregistration.

Dataset manifest must identify content cryptographically and include source, time
coverage, schema/version, row counts, files/hashes, and derivation metadata.

## Stage 3 — Make the historical evaluation boundary BEFORE data download

This is a material scientific decision and must be recorded before downloading market
data.

Create:

`decisions/ADR-0001-HISTORICAL-DEVELOPMENT-BOUNDARY.md`

Decision:

- Initial research asset: Binance BTCUSDT spot only.
- Development data may include available history only up to and including:
  `2024-12-31T23:59:00Z` at canonical 1m resolution.
- Detailed BTCUSDT bars after that timestamp are RESERVED and must not be fetched,
  inspected, charted, summarized, or used by research/strategy agents.
- The reserved interval is intended for later controlled historical evaluation and is
  not yet declared "sealed evidence" until the evaluator/isolation mechanism exists.
- Future prospective paper data remains stronger evidence than the reserved historical
  interval.
- The development cutoff cannot be moved later merely because research results are
  disappointing.
- Any future change to the boundary requires a new explicit scientific ADR before
  looking at the affected data.

Add the cutoff to machine-readable current state.

Implement a hard guard in development-data acquisition code so that a request for
BTCUSDT data later than the development cutoff fails closed.

Unit-test the guard.

IMPORTANT:
Do not make any network request for post-cutoff BTCUSDT data, even for "checking"
availability.

## Stage 4 — Backend engineering skeleton

Use Python with FastAPI.

Keep scientific/domain logic independent from HTTP.

Suggested dependency direction:

`api -> application -> domain/research/data`

Do not let domain/research/data modules import FastAPI.

Required endpoint:

`GET /api/v1/system/health`

Return only truthful state such as:

- service identity;
- health;
- software version if available;
- project phase/status;
- paper-only mode;
- real-money authorization;
- development-data availability/coverage if installed.

Add:

`GET /api/v1/research/status`

It should expose truthful research state:
no Champion, no experiments, no evidence.

Add a read-only historical data endpoint after Stage 7 is complete, for example:

`GET /api/v1/market/candles`

Requirements:

- BTCUSDT only;
- 1m/1h/4h supported;
- range/limit bounded;
- returns coverage/source metadata;
- never serves data after the development cutoff;
- clearly identifies the data as historical DEVELOPMENT data, not current market state.

Do NOT implement `/analysis/run` behavior yet.

If a placeholder route exists, it must return a clear not-implemented/phase-gated
response and never fabricate `NO_TRADE`.

## Stage 5 — Frontend engineering skeleton

Use React + TypeScript + Vite.

Create a dark desktop-first shell consistent with `WEB_APP_SPEC.md`.

At minimum provide navigation/surfaces for:

- Dashboard / Decision Now
- Market
- Paper Trades
- Statistics
- Research Lab
- System

Phase-appropriate behavior:

### Dashboard

Show:

- `PAPER ONLY`;
- backend health from real API;
- project status;
- `ANALYZE MARKET` visible but disabled/phase-gated;
- `No approved strategy`;
- `No market analysis available yet`;
- no fake price;
- no fake timestamp;
- no fake signal;
- no fake `NO_TRADE`;
- no fake confidence.

### Market

After development data exists, display a real candlestick chart from the canonical
historical DEVELOPMENT dataset using TradingView Lightweight Charts.

Prominently label it:

`HISTORICAL DEVELOPMENT DATA — NOT CURRENT MARKET`

Show actual dataset coverage.

Do not imply this is live/current BTC market state.

### Paper Trades / Statistics / Research Lab

Truthful empty states only.

No fabricated metrics.

### System

Show real backend health and current project/data status.

Frontend health must come from backend behavior, not a hard-coded string.

## Stage 6 — Developer tooling and deterministic validation

Create cross-platform Python entrypoints so Windows V1 development is practical.

Required commands:

- `python scripts/bootstrap.py`
- `python scripts/dev.py`
- `python scripts/check.py`

### bootstrap.py

Install/verify backend/frontend dependencies from committed manifests/lockfiles.

Do not download market data as an implicit side effect.

### dev.py

Start backend + frontend with one command, local bindings only, clean child-process
shutdown, backend health check, and clear local URL.

### check.py

Single deterministic checkpoint validator. Non-zero on failure.

It must cover:

Repository/governance:
- required structure/files;
- Constitution presence;
- state schema;
- state invariants;
- real money false;
- no fake evidence;
- no post-cutoff data manifests;
- no forbidden credential/order-execution code paths.

Experiment contracts:
- valid prereg fixture passes;
- missing primary metric fails;
- missing trial/search budget fails;
- valid linked result passes;
- orphan result fails;
- malformed dataset manifest fails.

Backend:
- lint/format check;
- type check;
- tests;
- health route;
- state loading;
- post-cutoff guard;
- market API cutoff guard.

Frontend:
- lint;
- typecheck;
- unit/component tests;
- production build;
- health source is API;
- disabled Analyze Market behavior;
- no fake trading values;
- historical-data banner when chart is shown.

Use conventional lightweight tools.

Do not add browser E2E infrastructure unless clearly necessary.

## Stage 7 — Build the BTCUSDT development-data pipeline

### Source policy

Use official Binance Spot public market-data sources only.

Prefer the official bulk public archive for historical 1m BTCUSDT data and use an
official public market-data API only when necessary for a permitted development-period
gap/tail.

Do not use third-party repackaged datasets.

Record exact source identifiers/URLs in manifests.

### Allowed time domain

Canonical resolution: 1 minute.

Development end is HARD-CAPPED at:

`2024-12-31T23:59:00Z`

Discover/use the earliest official BTCUSDT spot 1m data available from the approved
source without guessing a start row.

Do not request anything after the cutoff.

### Raw archive

Store downloaded raw source objects under `data/raw/...`.

Raw files are immutable after successful validation.

Record SHA-256 for every raw source object.

Do not commit raw data to Git.

### Canonical normalized data

Normalize to Parquet under `data/canonical/...`.

At minimum preserve fields needed for exact OHLCV research and source traceability.

Requirements:

- UTC timestamps;
- stable schema;
- chronological ordering;
- unique 1m bar identity;
- no fabricated rows;
- no forward-fill of missing bars;
- deterministic transform;
- OHLC consistency validation;
- non-negative volume;
- duplicate detection;
- gap detection;
- source coverage report.

When exact duplicates or conflicting rows exist, resolve only by a deterministic,
documented source policy. Do not silently pick whichever row is convenient.

### Derived 1h and 4h bars

Derive both solely from canonical 1m bars.

Rules:

- UTC-aligned windows;
- closed-bar semantics;
- deterministic OHLCV aggregation;
- any window missing required canonical minutes is marked incomplete and must not be
  silently treated as a complete research bar;
- no forward fill;
- derived data never extends beyond canonical coverage or cutoff.

Store under `data/derived/...`.

### Deterministic identity

Create committed manifests under `data/manifests/` containing:

- dataset ID/version;
- source;
- symbol;
- venue/market type;
- canonical resolution;
- coverage;
- row counts;
- raw SHA-256 hashes;
- canonical/derived file hashes;
- a deterministic content hash where appropriate;
- schema version;
- gap/integrity summary;
- code commit/config reference.

If Parquet file bytes are not guaranteed stable across library versions, also compute a
canonical content hash based on normalized logical rows and document the algorithm.

### Integrity report

Create a concise committed report under `data/reports/`.

It must summarize:

- first/last allowed bar;
- total rows;
- duplicate count;
- gap count and durations;
- invalid OHLCV count;
- incomplete derived windows;
- hash/manifest IDs;
- PASS/FAIL;
- any known source anomalies.

Do not paste millions of rows or giant gap lists into Markdown. Put detailed machine
artifacts in local data/artifact files and keep the committed report concise.

## Stage 8 — Execute the full development backfill

After pipeline unit/integration tests pass:

1. run the actual approved development-data acquisition;
2. normalize it;
3. derive 1h and 4h;
4. produce manifests/reports;
5. rerun deterministic validation against the real local dataset;
6. prove no local dataset exceeds the cutoff;
7. prove no post-cutoff network request is part of the pipeline/config.

Be resilient to ordinary transient network failures with bounded retry/backoff.

Do not ask the Owner to intervene for transient download errors.

If the official source is genuinely unavailable after reasonable bounded retries,
finish all non-network work, preserve diagnostics, mark the data stage FAIL/PARTIAL,
and report the blocker concisely.

## Stage 9 — Historical chart integration

Only after Stage 8 data validation passes:

- wire the read-only candle API to canonical/derived local data;
- wire the Market page chart to that API;
- test 1m/1h/4h selection;
- display coverage and data classification;
- keep `ANALYZE MARKET` unavailable;
- never display the latest chart candle as "current BTC price".

The chart is for historical development-data inspection only.

## Stage 10 — CI

Add a GitHub Actions workflow that runs deterministic code/tests/build without requiring
the large local market dataset or external network.

CI may use synthetic test fixtures only.

Do not require secrets.

The full local data validation remains available through `scripts/check.py` when the
dataset exists.

## Stage 11 — State + research-record update

Only after all work is complete, update repository truth cleanly.

### `state/current_state.json`

If all Phase 0 and Phase 1 gates pass, reflect that the project is ready for the next
backtest-substrate work package.

Research evidence must remain:

- experiments completed: `0`
- sealed evaluations completed: `0`
- paper trades completed: `0`
- Champion: `NONE`
- forward evidence: `NONE`
- real money authorized: `false`

State should also record:

- development cutoff;
- development dataset status;
- manifest ID/hash;
- development coverage;
- latest checkpoint ID;
- next recommended phase.

Do not label the development data itself as trading evidence.

### ADRs

Do not create ADRs for trivial implementation details.

Create an additional ADR only if a material architecture/scientific decision was truly
necessary.

### Checkpoint report

Create:

`reports/checkpoints/WP-001.md`

Keep it concise and structured:

- PASS / PARTIAL / FAIL;
- branch + commit;
- what was built;
- deterministic validation summary;
- development dataset identity/coverage;
- integrity summary;
- scientific state counters;
- forbidden-work checks;
- material deviations;
- next checkpoint recommendation.

### Task archive

Copy the completed work-package definition to:

`tasks/archive/WP-001.md`

Mark that archive copy completed with final commit/reference.

Leave `tasks/CURRENT_TASK.md` intact but change its status to `COMPLETED` only if all
mandatory gates pass; otherwise `PARTIAL` or `FAILED`.

The Research Director will replace it with the next work package after review.

## Acceptance criteria

WP-001 is PASS only if all of the following are true:

1. Seed project documents are preserved in Git history.
2. Work occurred on `work/wp-001-foundation-data`.
3. Scientific Constitution is preserved verbatim.
4. Repository information architecture is clean and documented.
5. One authoritative machine-readable current state exists.
6. ADR-0001 fixes the development cutoff before market-data acquisition.
7. Acquisition code hard-rejects post-cutoff BTCUSDT data.
8. Experiment/data/state contracts are deterministically validated.
9. FastAPI health/research-state endpoints are truthful and tested.
10. React/TypeScript/Vite builds and renders truthful Phase-appropriate states.
11. Analyze Market cannot generate a fake decision.
12. Official BTCUSDT spot 1m DEVELOPMENT data is locally acquired only through the
    cutoff.
13. Raw source hashes are recorded.
14. Canonical normalized Parquet passes integrity validation.
15. Deterministic 1h and 4h derivations exist and incomplete windows are handled
    explicitly.
16. Committed dataset manifest and concise integrity report exist.
17. Read-only historical candle API cannot cross the development cutoff.
18. Market UI shows real historical development candles with an unmistakable
    non-current-data label.
19. CI exists and requires neither dataset download nor secrets.
20. `python scripts/check.py` passes against the completed local installation/data.
21. No strategy/backtest research was performed.
22. No post-cutoff BTCUSDT detailed data was fetched/inspected.
23. No fake evidence or performance metric exists.
24. No real-money functionality or credentials exist.
25. Scientific counters remain zero.
26. Checkpoint report and archive record are cleanly written.
27. All intended changes are committed.
28. Working tree is clean.
29. Nothing was pushed by the executor.

## Commit discipline

Use meaningful commits at natural internal milestones rather than one giant unreviewable
commit or dozens of trivial commits.

Suggested shape only:

1. seed baseline on `main` if required;
2. governance/repository/contracts;
3. backend/frontend/tooling;
4. data pipeline;
5. validated development dataset metadata + UI integration;
6. final state/checkpoint documentation.

Do not commit large market-data files.

## Final validation

Before reporting:

- run `python scripts/check.py`;
- run backend tests/type/lint;
- run frontend lint/type/tests/build;
- verify data cutoff mechanically;
- verify dataset manifest hashes;
- verify git branch;
- verify git status clean;
- record HEAD SHA.

## Required executor response

Return only:

```text
WP-001: PASS | PARTIAL | FAIL

Branch:
HEAD:

Foundation:
- <max 5 bullets>

Development dataset:
- source:
- coverage:
- canonical rows:
- 1h rows:
- 4h rows:
- gaps/anomalies:
- manifest:

Validation:
- <one concise line>

Scientific state:
- experiments=0
- sealed_evaluations=0
- paper_trades=0
- champion=NONE
- forward_evidence=NONE
- real_money=false

Forbidden-work check:
- strategy/backtest research: absent
- post-cutoff BTCUSDT data access: absent
- fake evidence: absent
- real-money functionality: absent

Material deviations:
- none
  OR
- <only material deviations>

Next recommendation:
- <one sentence>
```

Do not paste raw logs unless FAIL/PARTIAL and a short excerpt is essential to identify
the blocker.
