# G2 Development Cycle 1 V1 — fixed batch results

> **Exposed development evidence only.** Not validation, not a discovery test, not a candidate or Champion. Production action remains `NO_TRADE`; real money is not authorized.

Status: `EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_G2_02_REVIEW`  
Authorization: `G2-02-DEV-RUN-AUTHORIZATION-001` (2026-09-29T15:40:28.394241+00:00)  
Interval: 2020 initialization/training; 2021-01-01..2024-12-31 UTC scored; 2025+ never requested.

## Executed systems

| Run | Systems | Run id | Record-stream fingerprint |
|---|---|---|---|
| ABL-G2-01 | ABL-G2-01 | G2DEV-b2692e27b6b3798f696362d7 | `05ae8379a1ec45a0…` |
| ABL-G2-02 | ABL-G2-02 | G2DEV-fe5024739e86dc101fb45740 | `5b68abfd17fe1736…` |
| G2-V0 | G2-V0 | G2DEV-a54a7701240dfc1c7edad0d5 | `34e97b9fa85c1b47…` |
| NULL-FORECAST | NULL_FORECAST | G2DEV-e27e7fe43bf060c852421cf1 | `976b46e055583a70…` |
| TREND-REFERENCE | TREND_ONLY_FORECAST, TREND_REFERENCE_POLICY | G2DEV-d19cb54c2e90e8fb35d02a0b | `06180b2606c1f0e1…` |

`CASH_REFERENCE` is zero exposure (no simulation). Ablations are diagnostic only and cannot be promoted.

## Headline (development, uncertainty = 80% weekly-block interval)

- G2-V0 total net return 0.00%, max drawdown 0.00%, 0 trades, mean realized NET_R —; 5% drawdown lock: not triggered.
- CRPS G2-V0 − NULL_FORECAST: point 0.00002381 (p10 0.00001837, p90 0.00002944); negative favours G2-V0.
- CRPS G2-V0 − TREND_ONLY_FORECAST: point 0.00000302 (p10 0.00000161, p90 0.00000444); negative favours G2-V0.
- CRPS G2-V0 − ABL-G2-01: point 0.00000160 (p10 2.840e-07, p90 0.00000293); negative favours G2-V0.
- CRPS G2-V0 − ABL-G2-02: point 6.014e-07 (p10 -5.373e-07, p90 0.00000176); negative favours G2-V0.
- Mean 15m return G2-V0 − TREND_REFERENCE_POLICY: point 0.00000000 (p10 0.00000000, p90 0.00000000); positive favours G2-V0.
- Mean 15m return G2-V0 − CASH_REFERENCE: point 0.00000000 (p10 0.00000000, p90 0.00000000); positive favours G2-V0.
- Mean 15m return G2-V0 − ABL-G2-01: point 0.00000000 (p10 0.00000000, p90 0.00000000); positive favours G2-V0.
- Mean 15m return G2-V0 − ABL-G2-02: point 0.00000000 (p10 0.00000000, p90 0.00000000); positive favours G2-V0.

## Forecast scorecard (2021–2024, matured targets)

| System | CRPS (primary) | Pinball q10 | Pinball q50 | Pinball q90 | Brier r4h>0 | q10–q90 coverage | MAE median | Direction hit (descr.) | Scored forecasts | Availability |
|---|---|---|---|---|---|---|---|---|---|---|
| G2-V0 | 0.006438 | 0.002310 | 0.004269 | 0.002259 | 0.25158 | 79.92% | 0.008537 | 49.10% | 140,225 | 99.99% |
| NULL_FORECAST | 0.006415 | 0.002308 | 0.004248 | 0.002254 | 0.25017 | 79.93% | 0.008495 | 50.71% | 140,225 | 99.99% |
| TREND_ONLY_FORECAST | 0.006435 | 0.002309 | 0.004267 | 0.002259 | 0.25133 | 79.92% | 0.008533 | 49.54% | 140,225 | 99.99% |
| ABL-G2-01 | 0.006437 | 0.002308 | 0.004268 | 0.002260 | 0.25141 | 79.91% | 0.008535 | 49.49% | 140,225 | 99.99% |
| ABL-G2-02 | 0.006438 | 0.002310 | 0.004269 | 0.002259 | 0.25155 | 79.92% | 0.008537 | 49.17% | 140,225 | 99.99% |

## Policy scorecard (common 15m timeline, 10,000 USDT virtual equity at 2021-01-01)

| System | Mean 15m return vs cash (primary) | Total net return | Max drawdown | Trades | Mean NET_R | Occupancy | LONG/SHORT | Turnover / yr | 5% drawdown lock |
|---|---|---|---|---|---|---|---|---|---|
| G2-V0 | 0.00000000 | 0.00% | 0.00% | 0 | — | 0.00% | 0/0 | 0.00 | not triggered |
| TREND_REFERENCE_POLICY | 0.00000000 | 0.00% | 0.00% | 0 | — | 0.00% | 0/0 | 0.00 | not triggered |
| CASH_REFERENCE | 0 | 0.00% | 0.00% | 0 | — | 0.00% | — | — | — |
| ABL-G2-01 | 0.00000000 | 0.00% | 0.00% | 0 | — | 0.00% | 0/0 | 0.00 | not triggered |
| ABL-G2-02 | 0.00000000 | 0.00% | 0.00% | 0 | — | 0.00% | 0/0 | 0.00 | not triggered |

## Execution scorecard

| System | Decision→fill (min) | Entries | Rejected | Friction paid | Funding paid | Funding received | Gap stops | Late exits | Funding invalid |
|---|---|---|---|---|---|---|---|---|---|
| G2-V0 | — | 0 | 0 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |
| TREND_REFERENCE_POLICY | — | 0 | 0 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |
| ABL-G2-01 | — | 0 | 0 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |
| ABL-G2-02 | — | 0 | 0 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |

## Uncertainty (5,000 complete-UTC-week bootstrap replicates, seed 2026092702)

Forecast (lower CRPS/Brier is better; negative Δ favours the first system):

| Comparison | Metric | Point Δ | p10 | p50 | p90 | Support |
|---|---|---|---|---|---|---|
| G2-V0 − NULL_FORECAST | crps | 0.00002381 | 0.00001837 | 0.00002350 | 0.00002944 | 140,225 |
| G2-V0 − NULL_FORECAST | brier | 0.00140596 | 0.00118538 | 0.00140716 | 0.00162511 | 140,225 |
| G2-V0 − TREND_ONLY_FORECAST | crps | 0.00000302 | 0.00000161 | 0.00000298 | 0.00000444 | 140,225 |
| G2-V0 − TREND_ONLY_FORECAST | brier | 0.00024688 | 0.00016146 | 0.00024525 | 0.00033283 | 140,225 |
| G2-V0 − ABL-G2-01 | crps | 0.00000160 | 2.840e-07 | 0.00000158 | 0.00000293 | 140,225 |
| G2-V0 − ABL-G2-01 | brier | 0.00016925 | 0.00009937 | 0.00016918 | 0.00023885 | 140,225 |
| G2-V0 − ABL-G2-02 | crps | 6.014e-07 | -5.373e-07 | 5.817e-07 | 0.00000176 | 140,225 |
| G2-V0 − ABL-G2-02 | brier | 0.00002464 | -0.00003654 | 0.00002488 | 0.00008276 | 140,225 |

Policy (positive Δ favours the first system):

| Comparison | Metric | Point Δ | p10 | p50 | p90 | Support |
|---|---|---|---|---|---|---|
| G2-V0 − TREND_REFERENCE_POLICY | 15m marked-equity simple return | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 140,256 |
| G2-V0 − CASH_REFERENCE | 15m marked-equity simple return | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 140,256 |
| G2-V0 − ABL-G2-01 | 15m marked-equity simple return | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 140,256 |
| G2-V0 − ABL-G2-02 | 15m marked-equity simple return | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 140,256 |

This is an internal stability diagnostic, not independent validation and not a discovery p-value.

## Coverage

- Scored decisions: 140,256
- Forecast unavailable (scored) by reason: {'FORECAST_UNAVAILABLE_MISSING_DATA': 16}
- Zero-volume minutes 2020–2024 (retained, frozen semantics): 332

## Autopsy (G2-V0)

### Category frequencies over all G2-V0 trades (FACT)

| Category | Trades | Share |
|---|---|---|

Denominator: 0 trades.

### Favourable episodes (top NET_R)

### Unfavourable episodes (bottom NET_R)

### Deterministic pseudo-random trade episodes

### Missed standardized opportunities (NO_TRADE with shadow NET_R ≥ +1R)

| Class | Episodes | Mean counterfactual NET_R (diagnostic) |
|---|---|---|
| MODEL_ABSTENTION | 1,478 | 1.264 |

Episodes: 1478; of which the TREND_REFERENCE_POLICY selected the same side at the first decision (COUNTERFACTUAL_REFERENCE_OPPORTUNITY): 0.

Each episode in `AUTOPSY.json` separates FACT → CAUSAL HYPOTHESIS → REQUIRED TEST. Hypotheses are not conclusions; no test was executed and G2-V0 was not modified.
