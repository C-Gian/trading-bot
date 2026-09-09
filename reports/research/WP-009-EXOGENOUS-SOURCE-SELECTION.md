# WP-009 exogenous source selection

**INFORMATION FOUNDATION — NOT EDGE EVIDENCE**

The source universe is exactly GDELT DOC 2.0 and ALFRED. Selection follows the
Research Director's information-semantic specification and point-in-time quality;
BTC prices, returns, trade outcomes, and strategy performance were not consulted.

GDELT supplies credential-free global news-volume and tone timelines. It can represent
crypto, public policy, central-bank, geopolitical, and social information environments
using a transparent query taxonomy. Its monitored source universe changes through
time, so counts are retained with returned normalization and availability flags rather
than treated as a stationary population. Article bodies are never scraped.

ALFRED supplies historical real-time macro vintages rather than a present-day revised
FRED snapshot. The credential-free graph download is acceptable only when each frozen
vintage request is retained and normalized under next-day UTC availability. If that
mechanism cannot be acquired deterministically, ALFRED is reported blocked rather than
replaced with current-revised data.

No paid API, account, key, source substitution, outcome-guided exclusion, rolling
transformation, standardization, or trading score is authorized in WP-009.
