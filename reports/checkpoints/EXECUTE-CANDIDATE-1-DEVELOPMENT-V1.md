# Checkpoint — EXECUTE-CANDIDATE-1-DEVELOPMENT-V1

Status: **CANDIDATE_1_DEVELOPMENT_RESULT_PENDING_RESEARCH_DIRECTOR_ADJUDICATION**.
Mechanical Development disposition: **`DEVELOPMENT_REJECTED`** (not reinterpreted here).

The single authorized execution (ADR-0040) of `research/protocols/CANDIDATE-1-DEVELOPMENT-V1.md`
ran once at HEAD `7677ce257ed8ecd9a2884cdc27f3c125b95851f4` with
`python scripts/run_candidate_1_development.py --execute`. Result:
`research/experiments/CANDIDATE-1-DEVELOPMENT-V1/result.json` (canonical sha256 `4a5d6f39…e866`);
provenance and replay in `reports/validation/CANDIDATE-1-DEVELOPMENT-V1-PROVENANCE.json`.
Development is exposed historical evidence (2022-2024), not confirmation.

## Integrity and support (all pass)

- Identities: protocol, ADR-0039, admission record, implementation — PASS; admission replay PASS;
  no overlapping primary positions.
- Population: 116 Candidate episodes, all scorable (primary, cost and delay); per year 41 / 40 / 35.
- Matching (outcome-blind): 101 pairs (2022 38/41, 2023 31/40, 2024 32/35; coverage 0.871);
  pooled SMD `shock_z` −0.083, log-vol −0.009; max within-year |SMD| 0.200. All 101 pairs scorable.
- Execution bars: canonical spot 1m (sha256 matches `BTCUSDT-SPOT-1M-DEV-v1`); no path minute missing.

## Primary economics (24 bp round trip)

| Quantity | Value | Gate |
|---|---|---|
| `ABS_NET_BP` | −27.03 | >= +25: **FAIL** |
| `INCREMENTAL_NET_BP` | −17.47 | >= +20: **FAIL** |
| Mean gross / fees / friction bp | −3.03 / 20.00 / 4.00 | — |
| Break-even all-in cost (mean gross) | −3.03 bp | — |
| Conservative annual contribution (35 × ABS) | −945.99 bp | >= 500: **FAIL** |
| ES10 Candidate / matched control | −349.49 / −283.80 | within 25 bp: **FAIL** |
| Max drawdown (cumulative −3,135.29 bp) | 3,135.29 bp | <= 1,000: **FAIL** |
| Yearly ABS 2022 / 2023 / 2024 | −37.14 / −29.28 / −12.61 | >0 in 2 of 3: **FAIL** |
| Yearly incremental 2022 / 2023 / 2024 | −21.00 / −31.85 / +0.66 | >0 in 2 of 3: **FAIL** |
| ABS without top-3 winners | −37.71 | >0: **FAIL** |
| Incremental without top-3 pairs | −23.28 | >0: **FAIL** |
| Cost stress (36 bp) ABS | −39.03 | >0: **FAIL** |
| Delay stress (T+46m) ABS / incremental | −25.87 / −13.34 | >0 / >0: **FAIL / FAIL** |

All 12 Development gates fail. Descriptive: win rate 0.405, median net −12.25 bp, median
MAE −67.7 bp, median MFE +65.5 bp, occupied 27,724 min (fraction 0.0176, −6.79 bp per occupied
hour); top 1/3/5 winners 565 / 1,126 / 1,555 bp (0.14 / 0.28 / 0.38 of positive bp); matched
controls mean net −18.45 bp.

## Uncertainty (descriptive)

- ABS: one-way month-cluster SE 14.94 (35 clusters, df 34); 95% CI [−57.40, +3.34]; raw SD 152.89;
  leave-one-year-out 2022 −21.50, 2023 −25.84, 2024 −33.26.
- Incremental: two-way month-cluster SE 22.83 (35 / 31 / 89 clusters, df 30); 95% CI
  [−64.10, +29.17]; raw SD 211.71; leave-one-year-out −15.34 / −11.10 / −25.87.

## Prospective detectability (12-month, 35 arrivals)

| Claim | Planning SD | Required N | Gate |
|---|---|---|---|
| Absolute (+25 bp MESI) | 191.57 | 461 | **FAIL** |
| Incremental (+20 bp MESI) | 298.71 | 1,751 | **FAIL** |

## Accounting

Development executions 1 of 1; execution authorization removed. Market trials executed 1.
Economic hypothesis tested; Candidate #1 market outcomes inspected (2022-2024 only). No new market
data, no post-cutoff or sealed access, sealed queries 0, Champion NONE, real money false.

Next: `RESEARCH-DIRECTOR-ADJUDICATION-CANDIDATE-1-DEVELOPMENT-V1` — no executor work; no
confirmation or reallocation is prepared here.
