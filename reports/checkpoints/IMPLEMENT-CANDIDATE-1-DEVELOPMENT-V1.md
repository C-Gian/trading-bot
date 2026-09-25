# Checkpoint — IMPLEMENT-CANDIDATE-1-DEVELOPMENT-V1

Status: **CANDIDATE_1_IMPLEMENTATION_READY_PENDING_RESEARCH_DIRECTOR_EXECUTION_AUTHORIZATION**.
Starting HEAD `0f0a74f0a144291dd7879f273ab06f16a2f1ad6d`. Implementation-only: no Candidate #1
forward return, trade payoff or economic metric was computed on real prices.

## Implementation

| Path | Role |
|---|---|
| `backend/app/research/candidate_1_development.py` | frozen protocol: population ingestion, matching, execution, metrics, uncertainty, detectability, adjudication |
| `scripts/run_candidate_1_development.py` | `--validate` / `--check` (outcome-blind); `--execute` refuses unless state authorizes |
| `backend/tests/test_candidate_1_development.py` | 27 synthetic / outcome-free tests |
| `reports/validation/CANDIDATE-1-DEVELOPMENT-IMPLEMENTATION-V1.json` | implementation-validation record (replayable) |

Protocol canonical sha256 `c47ffb9b…2313` (pinned; identity PASS); ADR-0039 and the admission
record are pinned too. No development result file exists.

## Outcome-free validation

- Population consumed unchanged from the frozen admission record: 335 valid episodes,
  116 Candidate / 219 control; admission replay PASS; primary positions non-overlapping; no
  Candidate exit minute falls after the cutoff.
- Outcome-blind matching on T-known covariates: 101 pairs, coverage 0.871 (2022 0.927, 2023
  0.775, 2024 0.914); |pooled SMD| 0.083 / 0.009; max |within-year SMD| 0.200; all matching
  gates pass. No forward price was read.
- Reuse: `CostModel` / `BACKTEST_ENGINE_V2` cost semantics (a test proves identical net P&L to
  `simulate`), the frozen admission record, canonical spot 1m artifact as execution source.

## Implementation readings for Director review

These resolve conventions the protocol does not spell out; none alters a frozen scientific
element, and each is visible in code:

1. Execution bars: canonical `data/canonical/BTCUSDT-1m.parquet` (`BTCUSDT-SPOT-1M-DEV-v1`);
   a bar is valid when present with finite positive OHLC and `high >= low`.
2. Within-year standardization and all raw SDs use the sample SD (ddof = 1).
3. Balance SMD: Austin definition on the matched raw covariates
   (`Δmean / sqrt((s_t² + s_c²)/2)`), pooled and within year.
4. Tie-break: Candidates fixed in timestamp order, each to the earliest-timestamp control that
   keeps a (max-cardinality, min-distance) optimum; distance ties within 1e-9 relative.
5. Cluster-robust SE: each component carries its own `G/(G-1)`; two-way
   `V_A + V_B − V_(A∩B)`; non-positive/undefined → invalid; 95% intervals use `t(G−1)`
   (two-way: smallest G).
6. 10% expected shortfall: mean of the worst `ceil(0.1·N)` net returns; drawdown from a zero
   start; break-even all-in cost = mean gross bp; occupied fraction over 2022-01-01..2025-01-01.
7. Top-three removal ranks by net bp (ties by timestamp); only matched pairs of those three are
   removed from the incremental sample.
8. An entry/exit minute after the development cutoff is unavailable → unscorable (none occur).
9. The assignment step uses an in-repository exact Hungarian solver (tested against brute force
   and SciPy) because the repository guard forbids optimizer libraries in `backend/app`.

## State

`market_trial_authorized = false`, `execution_authorized = false`, economic hypothesis untested,
market outcomes not inspected, sealed queries 0, Champion NONE, real money false.

Next: `RESEARCH-DIRECTOR-EXECUTION-REVIEW-CANDIDATE-1-DEVELOPMENT-V1` — market run forbidden
until the Director reviews and a later task authorizes it.
