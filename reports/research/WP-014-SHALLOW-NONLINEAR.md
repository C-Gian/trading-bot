# WP-014 shallow nonlinear internal-signal challenger

WP-014 executed one fixed `SHALLOW_INTERNAL_HGBR_V1` configuration and one disclosed
duplicate matched OLS control over the exact frozen F1-F8 universe. No hyperparameter,
feature, threshold, architecture, or model-selection search occurred.

Primary DEFAULT expectancy was -0.0998928666 R/trade over
1269 trades, with
1/6 nonnegative folds and minimum fold
count 129. ZERO was
+0.0201371727, DOUBLE was
-0.2199228978, and DELAY_1H was
-0.0868001004 R/trade. Pooled OOS
prediction/label Pearson correlation was
+0.0324933292.

The matched OLS DEFAULT expectancy was -0.1103044148; HGBR minus
control was +0.0104115482
R/trade. Eligible hours were matched, but executed trade sets were not paired.

Primary classification: **REJECT_COST_DOMINATED**. Independent
reconciliation passed at tolerance 1e-10 with zero
unexplained mismatches. Champion remains NONE, sealed queries remain zero, the ALIGNED
paper candidate is unchanged, and real money remains false.
