# Parked-state preservation manifest V1

Classification: ARCHIVAL_NAVIGATION_ARTIFACT (not a research summary; it does not override
`state/current_state.json`, ADRs or experiment artifacts).

## Disposition

- Project alpha-research disposition: **`PARKED_NO_CREDIBLE_EDGE_UNDER_CURRENT_CONSTRAINTS`** —
  [ADR-0042](../../decisions/ADR-0042-PARK-ACTIVE-ALPHA-RESEARCH.md) (Astra decision
  `ASTRA_POST_CANDIDATE_1_STRATEGIC_REALLOCATION_OR_PARK_2026-09`).
- Candidate #1: `CANDIDATE_1_CLOSED_DEVELOPMENT_REJECTED` —
  [ADR-0041](../../decisions/ADR-0041-CANDIDATE-1-DEVELOPMENT-REJECTED-STRONG-STOP.md).
- Candidate Card #2: unallocated. Active alpha allocation: zero. Champion NONE. Real money false.
  Sealed queries 0. Confirmation, market trials and prospective collection: not authorized.
- Canonical current status: `state/current_state.json` → `current_project_status` (takes precedence
  over the historical top-level fields it lists).
- Governing documents: `governance/SCIENTIFIC_CONSTITUTION.md` (Version 3.0),
  `docs/canonical/RESEARCH_STAGE_POLICY_V1.md`, `docs/canonical/STRATEGIC_ALLOCATION_MAP_V1.md`.
- **No active alpha task remains.** `tasks/CURRENT_TASK.md` is `PARKED-NO-ACTIVE-RESEARCH-TASK`.

## Canonical HEAD

Pre-closure HEAD `8c680143` (“Authorize final parked-state reconciliation”). The closure commit
is the commit that introduces this file on local `main`; `git log -- reports/handover/PARKED-STATE-PRESERVATION-MANIFEST-V1.md`
identifies it. Git history is the authoritative audit trail.

## Candidate #1 evidence

| Item | Location |
|---|---|
| Candidate card | `research/candidates/CANDIDATE-CARD-1-POSITIONING-CONDITIONED-SELL-OFF-RECOVERY.md` |
| Preserved non-authoritative executor diagnostic | `research/candidates/evidence/CANDIDATE-1-EXECUTOR-SUPPORT-DIAGNOSTIC-V1/` |
| Frozen admission spec / record | `research/protocols/CANDIDATE-1-FROZEN-ADMISSION-V1.md`, `reports/validation/CANDIDATE-1-FROZEN-ADMISSION-V1.json` |
| Development protocol | `research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md` (canonical sha256 `c47ffb9b…2313`) |
| Development result | `research/experiments/CANDIDATE-1-DEVELOPMENT-V1/result.json` (canonical sha256 `4a5d6f39d4c41157a12b79b3f38d9122e3ed0f4d99e38bd6cfce4d7d3dc7e866`) |
| Provenance and replay | `reports/validation/CANDIDATE-1-DEVELOPMENT-V1-PROVENANCE.json` |
| Implementation validation | `reports/validation/CANDIDATE-1-DEVELOPMENT-IMPLEMENTATION-V1.json` |
| Checkpoints | `reports/checkpoints/IMPLEMENT-CANDIDATE-1-DEVELOPMENT-V1.md`, `reports/checkpoints/EXECUTE-CANDIDATE-1-DEVELOPMENT-V1.md` |
| Decisions | ADR-0036 … ADR-0042 (`decisions/INDEX.md`) |
| Search-memory outcome | `research/memory/registry/outcomes/CANDIDATE-1-DEVELOPMENT-V1.jsonl` (layer `PLAYBOOK_DEVELOPMENT_NON_SEALED`) |

Broader research memory: `research/memory/` (families, outcomes, ledgers, `FAILURE_MEMORY.md`),
`research/experiments/`, `research/protocols/`, `reports/checkpoints/`,
`reports/reviews/METHODOLOGICAL-QUALIFICATIONS-V1.md`.

## Data (by manifest; do not copy or re-download)

Development cutoff `2024-12-31T23:59:00Z`; sealed data never acquired.

`data/manifests/`: `BTCUSDT-SPOT-1M-DEV-v1` (canonical `data/canonical/BTCUSDT-1m.parquet`,
sha256 `ae604813…f47e1`), `BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1` (raw
`data/raw/public-taker-flow/`), `BTCUSDT-USDM-OPEN-INTEREST-DEV-v1`
(`data/derived/BTCUSDT-USDM-open-interest-5m-v1.parquet`), `BTCUSDT-USDM-FUNDING-DEV-v1`,
`BTCUSDT-SPOT-ORDERFLOW-DEV-v1`, `BINANCE-SPOT-USDT-1H-CROSSSECTION-DEV-v1`,
`ALFRED-MACRO-CONTEXT-DEV-v1`, `CFTC-CME-BITCOIN-TFF-DEV-v1`, `WIKIMEDIA-BITCOIN-PAGEVIEWS-DEV-v1`.
Data files are local caches (not in Git); manifests pin their hashes and official sources.

## Environment and reproduction

- Python 3.11, `pyproject.toml` + `uv.lock` (`uv sync --frozen`); frontend Node 22,
  `frontend/package.json` + `package-lock.json`; `scripts/bootstrap.py` prepares both (as in
  `.github/workflows/check.yml`).
- No-data validation (no market outcomes): `uv run --frozen python scripts/check.py --no-data`.
- Outcome-free replays: `python scripts/audit_candidate_1_frozen_admission.py --check`;
  `python scripts/run_candidate_1_development.py --check`.
- Data-mode replays (read historical outcomes; run only if an Owner/Astra-authorized review needs
  them): `python scripts/check.py` and `python scripts/replay_candidate_1_development.py`.
- `scripts/run_candidate_1_development.py --execute` refuses to run (authorization removed and the
  single result already exists).

## Reopening rules (ADR-0042)

Parking may be reviewed only with a written dossier establishing a material changed case:
genuinely new accessible information with causal timing and a distinct mechanism; a structural
cost/access change leaving a surviving economic proposition; an identifiable market-structure
change; compelling independent evidence for an implementable mechanism; or an Owner-approved
material product/risk/resource change. A new indicator or AI model, elapsed time, renewed
enthusiasm, a different price regime or untested territory is not a trigger. Every reopening
requires Astra approval; material product/risk/resource changes may also require the Owner; real
capital always requires a separate explicit Owner decision.

## Retrieval/exposure note (ADR-0042)

During Astra's strategic review a mechanical retrieval agent unintentionally returned the Candidate
#1 result file's trade-level array in tool output. Astra's judgment used aggregate summaries only.
This is retrieval/exposure provenance, not a new experiment, subgroup analysis or reopening basis.
