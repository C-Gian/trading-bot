# G2-01 Gate B Re-review V1

Status: **PASS — G2-02 EXPOSED DEVELOPMENT AUTHORIZED**  
Reviewed commit: `aa18aeea575639b9b6d368246fd53bf50c329e18`  
Evidence class: engineering/causal validation only.

## Decision

Gate B passes.

The bounded corrections requested in
`reports/reviews/G2-01-GATE-B-RESEARCH-DIRECTOR-REVIEW-V1.md` are accepted:

- risk events now expose post-event realized and marked equity;
- funding-driven drawdown lock is contemporaneous;
- `RiskSnapshot.position_open` means an actual open trade only;
- the earlier ledger timestamps were qualified append-only rather than rewritten;
- the 2020-2024 non-economic data-integrity preflight passed;
- the BTCUSDT USD-M exchangeInfo filter snapshot is pinned and hash-verified.

The full local repository check on the clean final executor tree passed in data mode. The GitHub CI
run created by the later push is useful redundancy, not the evidence source used for this decision.

## Data preflight adjudication

Accepted:
- 60/60 exposed monthly objects;
- 2,630,880 valid expected minutes;
- no missing, duplicate, out-of-order or off-grid 1m rows;
- no incomplete 15m/1h/4h bars caused by gaps;
- funding grid complete: 5,481/5,481 expected settlements;
- 8h historical funding-grid assumption supported for 2020-2024;
- no protected 2025+ observation read.

The 332 zero-volume minutes remain an explicit data-quality observation.

No rule is changed before G2-V0 baseline:
- zero-volume observations remain handled by the frozen fail-closed feature semantics;
- 16 post-warmup decision instants are unavailable because taker imbalance is undefined;
- this is reported as coverage, not repaired post hoc.

## Cycle

`CYCLE-CAUSALITY-01 = AVAILABLE_FOR_RESERVED_REVISION` remains accepted.

Cycle remains SHADOW_ONLY in G2-V0. No cycle timing term may enter the baseline or diagnostic
ablations. The single G2-RCYCLE slot remains unused and available only through a pre-run change card.

## Search budget

Before G2-02 execution:
- baseline G2-V0: authorized, not yet executed;
- G2-R1/R2/R3: unused;
- G2-RCYCLE: unused;
- diagnostic ablations allowed: exactly two frozen ablations;
- protected evaluation: forbidden;
- future paper: forbidden.

## Gate decision

`GATE_B = PASS`

G2-02 may execute only the frozen exposed-development package in
`tasks/G2_02_BASELINE_AND_DIAGNOSTICS_V1.md`.

Validated strategy remains NONE.
Champion remains NONE.
Operational production action remains NO_TRADE.
Real money remains forbidden.
