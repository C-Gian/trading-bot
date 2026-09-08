# Baselines and Negative Controls V1

This development-only protocol was frozen before results. It runs exactly the six WP-003 experiments on BTCUSDT Spot through 2024-12-31T23:59:00Z. It allows LONG or no-entry, one position at a time, no leverage, no SHORT, no optimization, and no Champion promotion.

At UTC hour boundary `t`, the completed 1h bar closes, the signal decision freezes, and the canonical 1m open at `t` executes. All trade experiments require 169 consecutive complete 1h bars; gaps and partial bars reset eligibility. A LONG uses the latest completed signal-bar close as reference, stop 2% below reference, target 4% above reference, and 1,440-minute maximum hold. An open beyond stop or target is invalid. Gaps yield unresolved trades and quarantine entry until original expiry.

The fixed rules are: endpoint buy-and-hold reference; random entry at probability 1/24 for 32 SHA-256-derived seeds; SMA24 greater than SMA168; current close strictly above the previous 24 highs; the trend condition delayed one hour while pricing the plan from the latest close known at `t`; and no trade. Trend and breakout use DEFAULT, ZERO, and DOUBLE cost profiles. DEFAULT is 10 bps fees and 2 bps adverse friction per side; DOUBLE is 20/4; ZERO is diagnostic only.

Trade primary evidence is net expectancy R over valid resolved trades. Descriptive output includes attempts, valid trades, invalid and unresolved counts/rate, cumulative R, profit factor, drawdown, hit rate, win/loss averages, cost drag, and yearly breakdown. Buy-and-hold uses endpoint return only. Random primary evidence is median seed expectancy. There are no significance tests or promotion thresholds.
