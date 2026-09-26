# Checkpoint — EXECUTE-SYSTEM-G1-PHASE-A-V1

Status: `SYSTEM_G1_PHASE_A_RESULT_PENDING_RESEARCH_DIRECTOR_ADJUDICATION`
Mechanical disposition: **`SYSTEM_G1_DEVELOPMENT_REJECTED_SELECTION_STAGE`**
Authority: ADR-0048 (Phase A only); `research/protocols/SYSTEM-G1-DEVELOPMENT-V1.md`.
Evidence class: exposed historical development/selection evidence (not confirmation).

## Execution

- Guard phase-scoped first (requested phase must equal `authorized_phase`); no-data validation
  passed before any market read (commits `0e06637`, `b453a13`).
- One run: `uv run python scripts/run_g1_development.py --phase A`, 2026-09-25T21:38:33Z →
  2026-09-26T04:46:49Z (428 min wall; dominated by the frozen forecaster's per-issue weighted
  quantiles over the expanding training set). Exit 0.
- Engine window 2020-01-01 → 2023-01-01 (2020 warm-up/training only); entries only
  2021-01-01 ≤ decision < 2023-01-01; the engine stopped at 2023-01-01T00:00Z, so no 2023 kline was
  parsed. The single settled-funding artifact spans through 2024 and was loaded whole, but only
  settlements before 2023-01-01 could be applied. No 2023-2024 configuration economics computed.
- Artifact (write-once): `research/experiments/SYSTEM-G1-DEVELOPMENT-V1/PHASE-A-SELECTION.json`,
  self-hash `artifact_sha256 = 375c3a9720ea93467af60b0af44a4bf2a58d42ed314c3001669e93ad35f03655`
  (verified by `batch.artifact_digest`), file canonical sha256
  `efa615028bba7fcf45d52f9f5a7ccad6eeb39d58bb13d55246f762913941b568`. It records the protocol, code,
  source and configuration identities, all seven rows and every eligibility gate.
- State disarmed immediately afterwards (`historical_execution_authorized=false`,
  `authorized_phase=null`); the guard now refuses A and B.

## Seven configurations (2021-2022)

| Config | Scorable (2021/2022) | Coverage | 2021 net P&L / return | 2022 net P&L / return | Cumulative return | Max DD | Run stop | Eligibility |
|---|---|---|---|---|---|---|---|---|
| S0 | 47 (47/0) | 100% | −450.75 / −4.51% | 0 / 0% | −4.51% | 5.10% | YES | FAIL: scorable_2022_ge_15, net_pnl_2021_positive, net_pnl_2022_positive, run_drawdown_stop_never_triggered |
| S_FULL | 3 (1/2) | 100% | −29.94 / −0.30% | +97.64 / +0.98% | +0.68% | 0.30% | no | FAIL: scorable_trades_ge_40, scorable_2021_ge_15, scorable_2022_ge_15, net_pnl_2021_positive |
| S_MINUS_CYCLE | 52 (52/0) | 100% | −504.52 / −5.05% | 0 / 0% | −5.05% | 5.05% | YES | FAIL: scorable_2022_ge_15, net_pnl_2021_positive, net_pnl_2022_positive, run_drawdown_stop_never_triggered |
| S_MINUS_PARTICIPATION | 17 (8/9) | 100% | −178.48 / −1.78% | −24.90 / −0.25% | −2.03% | 2.60% | no | FAIL: scorable_trades_ge_40, scorable_2021_ge_15, scorable_2022_ge_15, net_pnl_2021_positive, net_pnl_2022_positive |
| S_MINUS_DAILY_HTF | 4 (2/2) | 100% | +22.57 / +0.23% | +98.15 / +0.98% | +1.21% | 0.30% | no | FAIL: scorable_trades_ge_40, scorable_2021_ge_15, scorable_2022_ge_15 |
| S_P1_ONLY | 3 (1/2) | 100% | −29.94 / −0.30% | +97.64 / +0.98% | +0.68% | 0.30% | no | FAIL: scorable_trades_ge_40, scorable_2021_ge_15, scorable_2022_ge_15, net_pnl_2021_positive |
| S_P2_ONLY | 0 (0/0) | n/a | 0 / 0% | 0 / 0% | 0% | 0% | no | FAIL: scorable_trades_ge_40, scorable_2021_ge_15, scorable_2022_ge_15, scorable_coverage_ge_95pct, net_pnl_2021_positive, net_pnl_2022_positive |

Descriptive (from the artifact, not gates): S0 mean net R −0.39, profit factor 0.55, 32 LONG / 15
SHORT; S_MINUS_CYCLE −0.40R, PF 0.50; S_MINUS_PARTICIPATION −0.48R, PF 0.45. S0 and S_MINUS_CYCLE
hit the 5% run-drawdown entry stop during 2021 and therefore took no 2022 entries. S_FULL and
S_P1_ONLY are identical: no S-full P2 trade occurred. The S-full-corroborated systems traded 3-4 times
in two years.

## Selection

- Selected configuration: **NONE** — no configuration satisfies every frozen eligibility gate
  (≥40 scorable, ≥15 per year, coverage ≥95%, positive net P&L in 2021 and 2022, run stop never
  triggered).
- Frozen rule outcome: `SYSTEM_G1_DEVELOPMENT_REJECTED_SELECTION_STAGE`.
- Phase B possible: **NO** (`phase_b_possible=false`; `run_phase_b` refuses without a selection, and
  the guard refuses Phase B regardless).

Forecast coverage / conviction counts: the Phase-A artifact persists only the frozen selection table;
forecast rows were not persisted, and no re-run was performed to obtain them.

Validated strategy NONE; production NO_TRADE; Champion NONE; sealed queries 0; real money false.
