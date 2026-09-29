# G2-02 Research Director Review V1

Status: **REVIEWED — BASELINE NOT PROMOTABLE; UTILITY DIAGNOSTIC AUTHORIZED**

Reviewed evidence:
- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/RESULTS.json`
- `research/experiments/G2-DEVELOPMENT-CYCLE-1-V1/AUTOPSY.json`
- `reports/checkpoints/G2-02-BASELINE-AND-DIAGNOSTICS-V1.md`
- `reports/checkpoints/G2-02-EXECUTOR-NOTE-ZERO-ACTIONS-V1.md`

Evidence class: exposed development only.

## 1. Integrity

The fixed G2-02 batch is accepted as technically valid development evidence.

Accepted:
- frozen G2-V0 executed without adaptive changes;
- four fixed references and two preregistered diagnostic ablations executed;
- deterministic G2-V0 rerun identity passed;
- no protected 2025+ observation was read;
- no revision slot was consumed;
- no candidate, Champion, paper activation or real-money authorization occurred.

## 2. Forecast finding

G2-V0 does not improve the primary forecast score versus the causal NULL_FORECAST on exposed
2021-2024 development.

Primary CRPS:
- G2-V0: 0.00643843;
- NULL_FORECAST: 0.00641461;
- delta G2-V0 - NULL: +0.00002381;
- weekly-block p10 / p90: +0.00001837 / +0.00002944.

Lower CRPS is better, so the complete V0 forecast is worse than NULL throughout the reported
internal stability interval.

Brier is also worse:
- G2-V0: 0.25157669;
- NULL_FORECAST: 0.25017073;
- delta: +0.00140596.

The TREND_ONLY forecast and both fixed ablations also fail to beat NULL on CRPS.

Therefore:

`G2_V0_FORECAST = NO_EXPOSED_INCREMENTAL_FORECAST_VALUE_VS_NULL`

This is a development finding, not a protected/future conclusion.

No ablation is promoted. ABL-G2-01 is less poor than G2-V0, but it still loses to NULL and is
diagnostic-only by contract.

## 3. Policy finding

Policy economics are **uninformative**, not negative.

Every economic system produced zero actions:
- G2-V0: 0 trades;
- TREND_REFERENCE_POLICY: 0 trades;
- ABL-G2-01: 0 trades;
- ABL-G2-02: 0 trades.

Hence all portfolio-return comparisons are exactly zero and cannot support either an economic edge
claim or an economic rejection of the policy's selected trades.

The causal reason is explicit:
- 140,240/140,240 forecast-available G2-V0 decisions ended
  `UTILITY_MARGIN_NOT_POSITIVE`;
- LONG predicted utility: median about -0.141R, maximum about +0.038R;
- SHORT predicted utility: median about -0.159R, maximum about +0.028R;
- median prequential residual q10 is about -0.979R LONG and -0.920R SHORT;
- highest resulting prudential margins remain negative: about -0.900R LONG and -0.872R SHORT.

The frozen rule `predicted utility + residual q10 > 0` therefore requires predicted utility on a
scale the fitted heads never approached.

This is evidence that the frozen actionability gate is too conservative to expose the utility
heads' economic discrimination in G2-V0. It is **not yet evidence** that simply lowering or removing
the gate would be profitable.

The TREND_REFERENCE_POLICY also never acts because its q10/q90 forecast interval always straddles
zero.

## 4. Shadow-payoff context

The unconditional standardized shadow labels are unfavorable on average:
- LONG mean NET_R about -0.171R; positive fraction about 35.5%;
- SHORT mean NET_R about -0.173R; positive fraction about 34.5%.

That makes abstention rational in aggregate.

The 1,478 autopsy episodes with shadow NET_R >= +1R are ex-post selected by their realized payoff.
Their mean counterfactual payoff is therefore **not evidence that those opportunities were
predictable ex ante**.

The unresolved scientific question is narrower:

> Do the already-fitted utility heads rank future path utility well enough that high predicted
> utility decisions have materially better realized shadow NET_R than the unconditional population?

That must be answered before spending a revision slot on the policy margin.

## 5. Next allocation

Authorize one diagnostic-only checkpoint:

`G2-02A-UTILITY-READOUT-DIAGNOSTIC-V1`

It uses only the existing G2-02 run cache/results and matured exposed labels.

It must:
- fit no new model;
- run no new economic simulation;
- choose no action threshold;
- execute no trades;
- consume no revision slot;
- access no 2025+ data.

The diagnostic tests ranking/calibration of the existing utility heads using fixed deciles,
year stability and UTC-week block resampling.

## 6. Decision after G2-02A

The Research Director will decide the first substantive G2 revision only after G2-02A.

Possible interpretations are deliberately bounded:
- robust utility ranking -> a minimal actionability/calibration revision may be justified;
- no utility ranking -> merely relaxing the prudential margin is not justified;
- mixed ranking -> investigate the smallest supported role-specific change without threshold search.

No R1/R2/R3/RCYCLE is authorized yet.

## 7. Current disposition

- G2-V0 forecast: no exposed incremental value versus NULL;
- G2-V0 policy economics: uninformative because zero actions;
- G2-V0: not promotable to protected evaluation;
- diagnostic ablations: not promotable;
- revision slots consumed: 0;
- cycle slot consumed: 0;
- protected evaluation: forbidden;
- future paper: forbidden;
- validated strategy: NONE;
- Champion: NONE;
- operational production action: NO_TRADE;
- real money: forbidden.
