# G2-02 executor note — zero economic actions (FACT only)

Status: executor observation for the Research Director. This note adds no rule, threshold or
revision. G2-V0 was not changed. The generated checkpoint is
`reports/checkpoints/G2-02-BASELINE-AND-DIAGNOSTICS-V1.md`.

## Facts (G2-V0 run cache, 140,256 scored decisions from 2021 through 2024)

- 140,240 decisions had a forecast and PREQUENTIAL_READY utility evidence on both sides. All
  140,240 ended `NO_TRADE / UTILITY_MARGIN_NOT_POSITIVE`. The other 16 are the preflight's
  zero-volume `FORECAST_UNAVAILABLE_MISSING_DATA` instants.
- Prudential margin = predicted NET_R + q10 of the prequential utility residuals:
  - LONG: highest margin −0.900R, median −1.115R. Predicted-utility median −0.141R, highest
    +0.038R. Median residual q10 −0.979R.
  - SHORT: highest margin −0.872R, median −1.075R. Predicted-utility median −0.159R, highest
    +0.028R. Median residual q10 −0.920R.
- Unconditional standardized shadow NET_R (both sides, after the 12bp/side haircut and funding)
  has a mean of about −0.17R.
- TREND_REFERENCE_POLICY never saw q10 > 0 or q90 < 0 (140,240 × `TREND_REFERENCE_QUANTILES_NOT_DIRECTIONAL`).
- ABL-G2-01 and ABL-G2-02 also produced zero actions.
- Forecast CRPS: G2-V0 − NULL_FORECAST = +2.38e-5 (80% weekly-block interval +1.84e-5 to
  +2.94e-5). Every ablation and TREND_ONLY also scores worse than NULL on CRPS.

## Implication (for the Research Director, not an executor decision)

Under the frozen margin rule, the residual q10 (about −0.95R) exceeds any predicted utility the
heads produced by more than an order of magnitude. No policy comparison can be informative in
this batch. Every policy delta is exactly 0.

Any change to the margin, residual rule, dictionary or horizon is a scientific revision. It
would need a change card and a budget slot.
