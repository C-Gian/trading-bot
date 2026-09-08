# WP-003 Baselines and Negative Controls

**Evidence stage:** DEVELOPMENT BACKTEST / CONTROLS ? NOT APPROVED STRATEGY PERFORMANCE

Dataset `BTCUSDT-SPOT-1M-DEV-v1` (`02168b73?acb2`); `BACKTEST_ENGINE_V2`, `EXECUTION_MODEL_V2`, `BTCUSDT_SPOT_COST_V1`. All six rules and trials were preregistered before results. No Champion is created.

| Experiment | Classification | Primary result | Trades |
|---|---|---:|---:|
| EXP-BASE-001-BUYHOLD | REFERENCE_ONLY_NOT_PRODUCT_CANDIDATE | 20.905930996 | N/A |
| EXP-BASE-003-TREND | FIXED_BASELINE_NOT_CANDIDATE | -0.0908105341 | 2445 |
| EXP-BASE-004-BREAKOUT | FIXED_BASELINE_NOT_CANDIDATE | -0.0482093869 | 1123 |
| EXP-CTRL-002-RANDOM | NEGATIVE_CONTROL | -0.0948689556 | 49255 |
| EXP-CTRL-005-TREND-DELAY-1H | TIMING_NEGATIVE_CONTROL | -0.0940234189 | 2446 |
| EXP-CTRL-006-NO-TRADE | NEGATIVE_CONTROL | N/A | 0 |

Trend and breakout retain DEFAULT, ZERO, and DOUBLE cost profiles in their immutable trial artifacts. Random retains all 32 seed outcomes and their declared distribution. Buy-and-hold is a market-direction reference outside the product holding horizon. No-trade produced zero attempts and zero trades.

The fixed trend, breakout, delayed timing control, and random control had negative net expectancy under default costs. These are valid development results and do not constitute project failure or an approved strategy. Gap-crossing trades remain unresolved without manufactured P&L; invalid attempts remain separate.

Calendar-year breakdowns, cost drag, drawdown, hit rate, win/loss averages, invalid attempts, and unresolved outcomes are preserved in each finalized `trials.json`. No naive significance test, adaptive parameter change, or promotion decision was made.
