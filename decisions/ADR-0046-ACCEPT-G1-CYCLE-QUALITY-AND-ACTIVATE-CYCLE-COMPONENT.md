# ADR-0046 — Accept System G1 cycle synthetic quality gate and admit cycle as an active G1 component

Status: ACCEPTED — Research Director, 2026-09-25

## Evidence

Frozen gate:
`research/protocols/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.md`

Result:
`reports/research/SYSTEM-G1-CYCLE-SYNTHETIC-QUALITY-GATE-V1.json`

Execution commit:
`afbf835ba76c2cac0c2951bec24dc5c0c93c2783`

No BTC market data, BTC return or System G1 historical outcome was used.

The frozen quality rule was not changed after execution:

- `explained_fraction >= 0.90`;
- current + previous two completed scale bars;
- normal warm-up complete;
- no gap/reset in the persistence window.

## Adjudication

Accept:

`CYCLE_SYNTHETIC_QUALITY_GATE_PASS_PENDING_RESEARCH_DIRECTOR_ACTIVATION`

as a valid method-quality PASS.

All six scales passed all mandatory gates.

White-noise USABLE occupancy remained low:

- median: 1.8% to 2.5% across scales;
- p95: 4.7% to 9.0% across scales;
- frozen limits: median <=5%, p95 <=15%.

Clean-cycle and trend+cycle ensembles had median/p10 USABLE occupancy 100% on every scale.

Median dominant-period relative error was approximately 3.9% to 4.6%, below the frozen 10% limit.

Causal/integrity gates all passed.

## Interpretation

This result validates the **measurement method for System G1 use** under its frozen synthetic gate.

It does not establish:

- profitable BTC cycle trading;
- predictive BTC cycle skill;
- a reliable market turning-point forecast;
- a probability interpretation for cycle quality;
- economic value of the cycle component.

Those questions remain for the bounded historical System G1 comparison.

The synthetic coherent fixtures are deliberately clean and the high-pass filter exactly removes the
linear-trend fixture. Their 100% retention is therefore not treated as evidence about real-market
occupancy.

## Activation decision

The cycle family is admitted as an active **timing/corroboration component** for System G1.

Frozen quality labels:

- UNAVAILABLE;
- WEAK;
- USABLE.

Frozen timing semantics:

- FAST = 45m + 3h;
- INTERMEDIATE = 1d + 4d;
- SLOW = 1w + 4w.

For LONG support:

1. at least one FAST scale is USABLE;
2. every USABLE FAST scale has current projected slope `RISING`;
3. no USABLE INTERMEDIATE scale has most recent confirmed turn `CONFIRMED_DOWN_TURN`.

SHORT is symmetric.

SLOW disagreement is displayed and recorded but is not an entry veto in G1.

Otherwise the qualifier is `CYCLE_MIXED_OR_WEAK`.

Cycle support cannot create a setup by itself. It may only satisfy the predeclared cycle
corroboration role of P1/P2.

## Primary execution delay

Accept the corrected System G1 primary operational delay:

`1 minute` after readiness.

The later delay robustness view is an additional +5 minutes.

Costs and other risk limits remain unchanged.

## Next stage

Freeze and implement the complete System G1 Development V1 specification **without inspecting G1
historical outcomes**.

The historical G1 batch remains unauthorized until the Research Director reviews that
implementation.

Champion NONE. Validated strategy NONE. Operational production output NO_TRADE. Real money false.
