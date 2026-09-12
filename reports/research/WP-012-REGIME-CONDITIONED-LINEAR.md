# WP-012 regime-conditioned linear experts

**EXPOSED DEVELOPMENT RESEARCH — NOT APPROVED STRATEGY PERFORMANCE.**

`FAM-REGIME-CONDITIONED-LINEAR` is **REJECT_COST_DOMINATED**.

## Recovery and chronology

Recovery began from `8633203f8fc054f13bd47bc1c03020fcd1f3e75e`, two Claude commits after
the reviewed `a4dab6cc00c26fbaa108414c5a8d3977890ff8c7` baseline. The final
SEARCH_MEMORY admission, allocation, protocol, two preregistrations, NFCI as-of audit,
and pre-execution structural finding were committed before the recovered result files
were produced. The result artifacts were intact; the independent reconciliation and
result/state records were unfinished. No chronology repair or market-result rerun was
performed.

## Frozen design

`FINANCIAL_CONDITIONS_REGIME_V1` uses only conservatively available point-in-time ALFRED
NFCI: `NORMAL_OR_LOOSE` at or below exactly 0.0 and `TIGHT` above 0.0. There was one
threshold, no smoothing or hysteresis, no alternate macro variable, and missing NFCI made
an hour ineligible. NFCI selected an expert but never entered the feature matrix.

Both configurations used the frozen eight WP-008 features in their declared order, the
isolated DEFAULT net-R target, a 216-hour purge, fully known training outcomes, float64
OLS with intercept, train-only population scaling, full-rank enforcement, and one fit per
annual fold. `REGIME_TWO_EXPERTS` fitted separate regime experts; the matched control
fitted one global expert on the same eligible universe. DEFAULT, ZERO, DOUBLE, and
DELAY_1H were fixed before execution.

## Results

| Configuration | DEFAULT | ZERO | DOUBLE | DELAY_1H | Trades | Nonnegative folds | Min fold | OOS Pearson |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `REGIME_TWO_EXPERTS` | **-0.1071860713 R** | +0.0128704015 R | -0.2272425389 R | -0.0999433536 R | 989 | 1/6 | 84 | +0.0308428274 |
| `GLOBAL_SINGLE_EXPERT_MATCHED` | -0.1103044148 R | +0.0097486022 R | -0.2303574280 R | -0.1053203947 R | 1,001 | 1/6 | 82 | +0.0305095744 |

The primary cumulative DEFAULT result was -106.0070 R, with trade ESS 830.20 and
active-week Kish count 117.44. Annual expectancy was -0.0572, -0.0426, -0.2083,
-0.2334, +0.0390, and -0.1573 R for 2019 through 2024. Five of six folds were negative;
all six were negative at doubled costs.

The primary exceeded the control by only +0.0031183435 R/trade. This is descriptive,
not paired: the primary could not emit predictions for 336 TIGHT validation hours and
executed 12 fewer resolved trades. The tiny difference is consistent with withholding a
small slice of the universe, not demonstrated regime-conditioned improvement.

## Regime evidence

`NORMAL_OR_LOOSE` contributed all 989 primary trades and scored -0.1071860713 R/trade
(-106.0070 R cumulative) across all six years. It had 48,448 eligible validation hours,
9,286 positive predictions, and OOS Pearson +0.0308428274.

`TIGHT` had 336 eligible validation hours, but zero positive predictions and zero trades
because its expert was infeasible in DEV-2020, the only fold with TIGHT validation data.
The control took 13 TIGHT trades at -0.0991203204 R/trade, but those trades used the
global model and do not validate a TIGHT expert. Robust positive net expectancy was
therefore absent in NORMAL_OR_LOOSE and untestable in TIGHT.

## Explicit conclusions

1. **Does PRIMARY beat the control?** Numerically by +0.0031183435 R/trade, but not in a
   scientifically meaningful or paired sense. Both are `REJECT_COST_DOMINATED` with 1/6
   nonnegative folds.
2. **Does either regime have robust positive net expectancy after costs?** No.
   NORMAL_OR_LOOSE is clearly negative; the TIGHT expert has no validation trades.
3. **Is improvement broad across years?** No. The primary is negative in five years and
   positive only in 2023.
4. **Does doubled-cost robustness improve?** Only trivially versus the control
   (-0.22724 vs -0.23036 R), while every primary fold remains negative. There is no
   cost-robust edge.
5. **Are coefficient differences stable?** Superficially: all eight TIGHT-minus-NORMAL
   difference signs repeat across four comparable records. But the four TIGHT fits are
   the same 336-row model with one unique model hash, so this is repetition, not temporal
   confirmation. The NORMAL expert itself has full sign stability for five of eight
   features; the other three have dominant-sign shares 0.83, 0.67, and 0.50.
6. **Useful conditioning or partitioning noise?** Merely partitioning on this sample.
   NFCI is above zero in one contiguous 2020 fortnight, making a TIGHT expert impossible
   to train before and use during the only TIGHT validation interval.

## Descriptive historical context

Trade sets and eligibility differ, so none of these are paired comparisons. WP-012 is
less negative than WP-008 `LINEAR_FULL` (-0.1142 R) but worse than WP-011
`EWLS_INTERNAL_MACRO` (-0.0988 R), WP-011 `EWLS_INTERNAL_ONLY` (-0.0527 R), and the
breakout baseline (-0.0482 R). `ALIGNED` remains descriptively positive at +0.1374 R but
`INCONCLUSIVE`; no-trade remains 0 trades and 0 realized exposure. WP-012 does not change
the ALIGNED product candidate or promote a Champion.

## Independent reconciliation and governance

The recovery reconciliation rebuilt the ALFRED NFCI timeline from raw verified vintage
records, all 59,025 internal-feature-eligible rows, all 16 feasible expert fits and their
scaling, every OOS prediction, the DEFAULT signal sets, and 2,008 DEFAULT attempts. It
called neither the primary lab nor runner. All checks passed; maximum coefficient and
prediction gaps were 5.0e-16 and 1.33e-15, with zero mismatches.

WP-012 adds two completed experiments, one economic hypothesis, two configurations,
eight profile evaluations, 18 reserved/16 feasible expert fits, zero numeric variants,
and zero regime-threshold variants. Cumulative accounting is 19 experiments, 8 economic
hypotheses, 19 configurations, 93 profile trials, 8 adaptive decisions, 8
result-dependent forks, and 174 reserved supervised fits. Sealed queries remain 0,
paper trades 0, Champion NONE, and real money false. WP-009 remains paused and the V1 UI
and paper-research surface are unchanged.

## Next

Research Director review. Park this exposed zero-threshold NFCI-conditioned linear
family without tuning. A future regime-conditioning test would require genuinely
prospective evidence or a separately authorized, preregistered regime source with enough
independent regime transitions; it must not rescue WP-012 by retuning this sample.
