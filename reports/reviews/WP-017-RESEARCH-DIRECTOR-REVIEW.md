# WP-017 Research Director review

Status: **REJECT**  
Run: `f475f7a2ef4b4ed693b5f86aa56d4b38`  
Candidate: `WP017_CFTC_LEVERAGED_POSITIONING_V1`

The immutable Owner-executed run and all recorded artifact hashes reconcile. The
frozen primary returned -0.1336606174 R under DEFAULT costs, -0.0136485544 R at
ZERO cost, -0.2536726859 R under DOUBLE costs, and -0.1259686378 R under DELAY_1H.
The matched-control DEFAULT result was -0.1143167546 R, so the primary-minus-control
difference was -0.0193438628 R. There were 1,030 trades, five populated folds, only
two nonnegative folds, OOS correlation 0.0021203273, and reconciliation passed.

The tested CFTC Leveraged Funds feature does not demonstrate useful incremental
predictive information in this frozen specification. DEFAULT expectancy is negative,
ZERO-cost expectancy remains negative, the primary is worse than its matched control,
fold breadth fails, and OOS correlation is approximately zero.

`FAM-CFTC-REGULATED-FUTURES-POSITIONING` is parked. No parameter rescue, alternate
CFTC transformation, sign split, or funding combination is authorized. This review
does not rewrite the preregistration, authorize sealed access, change the product, or
authorize real money.
