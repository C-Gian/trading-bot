# WP-004 evidence audit and generated views

The strategy/evaluation dependency closure frozen in effective version-2 preregistrations
is unchanged after execution. `wp004_validation.py` is a later, separate audit layer:
it reads saved evidence, never calls a strategy runner or loads market prices.

`python scripts/validate_wp004.py` verifies historical ancestry and declarations, the
zero-trial amendment, original WP-003 bytes, append-only ledger/outcomes, exact 3×4
allocation, 72 fold components, all saved trade costs/timing/occupancy, reproducible
metrics, result linkage and the frozen terminal rule. Accounting reconciliation is
not a second fill simulation and cannot establish that a market mechanism is causal.
The pre-commit flag only permits initial result finalization; the final checkpoint
always requires committed, immutable result artifacts.

`python scripts/summarize_wp004.py --check` reconstructs comparisons from existing
trades and checks generated memory views. The write form never overwrites an existing
comparison; only the Markdown views may be regenerated. No strategy trials are added.
`WP-004-LESSONS.json`, validated against `research_lessons.schema.json`, holds immutable
post-result interpretations with original result hashes. It does not amend results,
grant new trials, or supersede the frozen classifier. Human maps are projections,
not a second independently editable current-state source.

`python scripts/check.py` includes the full evidence audit, memory/schema/state checks,
branch/ancestry/Constitution restrictions, scope guards, tests, type/lint checks,
frontend build, and installed dataset/source-grid hash verification. `--no-data`
still verifies approved dataset identity and any present file inventory, but does
not load market files. `python scripts/clean_checkout_check.py` creates an owned
temporary detached checkout, bootstraps it, runs the same no-data validation, and
removes only that verified temporary checkout. It creates no research branch.

After Owner push, remote CI must still be observed at the new HEAD; local checks do
not constitute a remote CI success. Profitability never determines validation PASS.
No finite validator can prove that nobody ran an unlogged external experiment or
detect semantic equivalence of arbitrary programs; explicit admission, versioned
source hashes, cumulative budgets, immutable chronology and review are complementary.
