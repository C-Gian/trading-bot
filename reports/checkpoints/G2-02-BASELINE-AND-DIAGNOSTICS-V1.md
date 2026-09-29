# G2-02 Baseline and Diagnostics V1 — executor checkpoint

> **Exposed development evidence only.** Not validation, not a discovery test, not a candidate or Champion. Production action remains `NO_TRADE`; real money is not authorized.

Status: `EXECUTOR_COMPLETE_PENDING_RESEARCH_DIRECTOR_G2_02_REVIEW`

## What was executed

- G2-V0 exactly as frozen at Gate A/B (no parameter, feature, threshold, cost, risk or cycle change); cycle SHADOW_ONLY.
- Fixed references: NULL_FORECAST, TREND_ONLY_FORECAST, TREND_REFERENCE_POLICY, CASH_REFERENCE (definitions from the frozen contract §23; not tuned).
- Diagnostic ablations: ABL-G2-01 (FULL_MINUS_PARTICIPATION_FLOW_RESPONSE), ABL-G2-02 (FULL_ADDITIVE_ONLY); same ridge/calendar/window/penalties.
- Ledger authorization `G2-02-DEV-RUN-AUTHORIZATION-001` appended at 2026-09-29T15:40:28.394241+00:00 before the first economic simulation.
- No adaptive revision, change card, stress scenario, R1/R2/R3/RCYCLE, 2025+ access, candidate/Champion, paper trading or real money.

## Integrity

- G2-V0 simulated twice: fingerprint identical = yes, cache identical = yes.
- Development core ≡ frozen `G2Core` for G2-V0 on the synthetic engineering path (record-stream fingerprint equality test).
- Issued predictive quantiles re-derived bit-identically from the reconstructed residual sets before CRPS scoring: G2-V0=yes, NULL_FORECAST=yes, TREND_ONLY_FORECAST=yes, ABL-G2-01=yes, ABL-G2-02=yes.
- Accounting/rule audits: G2-V0: trades reconcile=yes, equity reconciles=yes, one position=yes, no pre-2021 entry=yes, no 2025+ observation=yes; ABL-G2-01: trades reconcile=yes, equity reconciles=yes, one position=yes, no pre-2021 entry=yes, no 2025+ observation=yes; ABL-G2-02: trades reconcile=yes, equity reconciles=yes, one position=yes, no pre-2021 entry=yes, no 2025+ observation=yes; TREND_REFERENCE_POLICY: trades reconcile=yes, equity reconciles=yes, one position=yes, no pre-2021 entry=yes, no 2025+ observation=yes; NULL_FORECAST: trades reconcile=yes, equity reconciles=yes, one position=yes, no pre-2021 entry=yes, no 2025+ observation=yes

## Results summary

- G2-V0 total net return 0.00%, max drawdown 0.00%, 0 trades, mean realized NET_R —; 5% drawdown lock: not triggered.
- CRPS G2-V0 − NULL_FORECAST: point 0.00002381 (p10 0.00001837, p90 0.00002944); negative favours G2-V0.
- CRPS G2-V0 − TREND_ONLY_FORECAST: point 0.00000302 (p10 0.00000161, p90 0.00000444); negative favours G2-V0.
- CRPS G2-V0 − ABL-G2-01: point 0.00000160 (p10 2.840e-07, p90 0.00000293); negative favours G2-V0.
- CRPS G2-V0 − ABL-G2-02: point 6.014e-07 (p10 -5.373e-07, p90 0.00000176); negative favours G2-V0.
- Mean 15m return G2-V0 − TREND_REFERENCE_POLICY: point 0.00000000 (p10 0.00000000, p90 0.00000000); positive favours G2-V0.
- Mean 15m return G2-V0 − CASH_REFERENCE: point 0.00000000 (p10 0.00000000, p90 0.00000000); positive favours G2-V0.
- Mean 15m return G2-V0 − ABL-G2-01: point 0.00000000 (p10 0.00000000, p90 0.00000000); positive favours G2-V0.
- Mean 15m return G2-V0 − ABL-G2-02: point 0.00000000 (p10 0.00000000, p90 0.00000000); positive favours G2-V0.

## Forecast

| System | CRPS (primary) | Pinball q10 | Pinball q50 | Pinball q90 | Brier r4h>0 | q10–q90 coverage | MAE median | Direction hit (descr.) | Scored forecasts | Availability |
|---|---|---|---|---|---|---|---|---|---|---|
| G2-V0 | 0.006438 | 0.002310 | 0.004269 | 0.002259 | 0.25158 | 79.92% | 0.008537 | 49.10% | 140,225 | 99.99% |
| NULL_FORECAST | 0.006415 | 0.002308 | 0.004248 | 0.002254 | 0.25017 | 79.93% | 0.008495 | 50.71% | 140,225 | 99.99% |
| TREND_ONLY_FORECAST | 0.006435 | 0.002309 | 0.004267 | 0.002259 | 0.25133 | 79.92% | 0.008533 | 49.54% | 140,225 | 99.99% |
| ABL-G2-01 | 0.006437 | 0.002308 | 0.004268 | 0.002260 | 0.25141 | 79.91% | 0.008535 | 49.49% | 140,225 | 99.99% |
| ABL-G2-02 | 0.006438 | 0.002310 | 0.004269 | 0.002259 | 0.25155 | 79.92% | 0.008537 | 49.17% | 140,225 | 99.99% |

## Policy

| System | Mean 15m return vs cash (primary) | Total net return | Max drawdown | Trades | Mean NET_R | Occupancy | LONG/SHORT | Turnover / yr | 5% drawdown lock |
|---|---|---|---|---|---|---|---|---|---|
| G2-V0 | 0.00000000 | 0.00% | 0.00% | 0 | — | 0.00% | 0/0 | 0.00 | not triggered |
| TREND_REFERENCE_POLICY | 0.00000000 | 0.00% | 0.00% | 0 | — | 0.00% | 0/0 | 0.00 | not triggered |
| CASH_REFERENCE | 0 | 0.00% | 0.00% | 0 | — | 0.00% | — | — | — |
| ABL-G2-01 | 0.00000000 | 0.00% | 0.00% | 0 | — | 0.00% | 0/0 | 0.00 | not triggered |
| ABL-G2-02 | 0.00000000 | 0.00% | 0.00% | 0 | — | 0.00% | 0/0 | 0.00 | not triggered |

## Execution

| System | Decision→fill (min) | Entries | Rejected | Friction paid | Funding paid | Funding received | Gap stops | Late exits | Funding invalid |
|---|---|---|---|---|---|---|---|---|---|
| G2-V0 | — | 0 | 0 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |
| TREND_REFERENCE_POLICY | — | 0 | 0 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |
| ABL-G2-01 | — | 0 | 0 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |
| ABL-G2-02 | — | 0 | 0 | 0.00 | 0.00 | 0.00 | 0 | 0 | 0 |

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

## Artifacts

- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/RESULTS.json` (canonical result)
- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/AUTOPSY.json`
- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/TRADES-*.csv`
- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/AUTHORIZATION.json`, `BATCH_MANIFEST.json`
- `reports/validation/G2-02-DEVELOPMENT-BATCH-VALIDATION-V1.{json,md,log}`

Interpretation and the next development allocation are Research Director decisions.
