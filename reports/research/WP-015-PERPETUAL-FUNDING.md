# WP-015 perpetual funding sentiment / positioning context

WP-015 tested one new raw informational variable, the latest settled BTCUSDT USD-M
perpetual funding rate strictly earlier than each hourly signal, against a matched
internal-only HGBR control on the exact same 2020-2024 eligible universe. BTCUSDT spot
LONG remained the only traded instrument.

Primary DEFAULT expectancy was -0.0814500414 R/trade over
716 trades, with
0/5 nonnegative folds and minimum fold
count 68. ZERO was
+0.0385955883, DOUBLE was
-0.2014956557, and DELAY_1H was
-0.1044031521 R/trade.

Matched control DEFAULT was -0.1236220929; primary minus control was
+0.0421720515 R/trade.
This relative improvement did not yield positive DEFAULT expectancy or any nonnegative
fold. Classification: **REJECT_COST_DOMINATED**. Reconciliation passed
with maximum prediction difference 0.0.

Funding-sign diagnostics are descriptive only. No transformation, sign threshold, model
variant, or result-dependent rescue was performed. Champion remains NONE, ALIGNED remains
the paper research candidate, sealed queries and paper trades remain zero, and real money
remains false.
