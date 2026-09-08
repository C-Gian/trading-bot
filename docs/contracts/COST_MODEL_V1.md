# Cost model V1

Default profile `BTCUSDT_SPOT_COST_V1` has a 10 bps entry fee, 10 bps exit fee, 2 bps adverse entry execution friction, and 2 bps adverse exit execution friction: 24 bps nominal round trip before path effects. This is a conservative research assumption, not a guaranteed Binance tier.

Fees apply to their respective effective notional. Entry friction increases a long entry and exit friction decreases a long exit. Favorable slippage is unavailable. Trade records expose each component. Future preregistrations must include cost-stress profiles; refinements are prospective and never rewrite observed results.

R uses initial pre-cost price risk: `(entry_raw - stop)`. Gross P&L is `exit_raw - entry_raw`; net P&L subtracts execution friction and both fees. Costs stay in the numerator.

