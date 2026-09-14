# PROJECT-RETROSPECTIVE-V1

Status: **BLOCKED**. This is a non-experiment audit. WP-016 was not executed, no WP-016
market result was observed, no sealed or post-cutoff BTC data was accessed, and no
scientific counter changed.

## Executive conclusion

The historical BTC engine, features, labels, costs, folds, accounting, and exposed
WP-003 through WP-015 results survived adversarial review. Their status remains
development evidence; the supervised reconcilers are useful but only partially
independent because they share production feature, label, and execution substrate.
No historical numerical artifact or scientific conclusion was rewritten or downgraded.

Two material forward-looking defects were found:

1. **WP-016 is blocked before execution.** Its daily series is complete, hashed, and
   conservatively delayed, but it was retrieved as a current historical aggregate. The
   Wikimedia endpoint exposes no vintage/publication identity establishing that each
   returned historical value was the value available at D+2. Wikimedia also documents
   changing automated-traffic classification. This is an unclosed revision/definition
   leakage risk, not proof that a particular value changed. The runner now refuses
   WP-016 server-side. Correcting the premise requires a new source design and new
   preregistration; the frozen WP-016 semantics were not edited.
2. **New paper entries are blocked.** The manual analysis is necessarily requested after
   the hourly boundary but the trade record used that already-observed boundary minute
   open as its prospective entry. No genuine paper trade exists, so no evidence was
   contaminated. Creation now fails closed while analysis, historical displays, and the
   synthetic lifecycle oracle remain available. A future causal paper version must
   define an entry that is still unknown when the intent is persisted.

Official source basis: [Wikimedia page-view API reference](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html),
[page-view semantics](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/concepts/page-views.html),
[API changelog](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/changelog.html),
and [pageview data incidents/availability](https://wikitech.wikimedia.org/wiki/Analytics/Data/Pageviews).

## Scientific integrity

- All 25 completed experiment directories have preregistration commits preceding result
  commits. The two WP-016 directories contain preregistrations only. Failed and rejected
  evidence remains present.
- Machine accounting reconciles to 12 hypotheses, 27 configurations, 125 profile trials,
  218 reserved supervised fits, 12 adaptive decisions, 10 result-dependent forks, zero
  numeric variants, and zero sealed queries. WP-016 accounts for two configurations,
  eight profiles, and ten reserved—but zero actual—fits.
- Development cutoff remains `2024-12-31T23:59:00Z`; local BTC files and manifests do
  not exceed it. Champion, sealed evidence, forward evidence, paper count, and real-money
  authorization remain `NONE`/zero/false.
- BAR_CLOSE, SIGNAL_DECISION, and NEXT_1M_OPEN_EXECUTION are aligned at the boundary:
  features use bars closed by `t`; the canonical minute opening at `t` is the entry;
  stop/target are evaluated conservatively from that minute; expiry is `t+1440m`.
  Missing entry/path bars never manufacture PnL and ambiguous bars are STOP_FIRST.
- F1-F8 use the intended completed windows. In particular, prior-24h high excludes the
  current hour; realized volatility uses exactly 24 completed close changes; 4h order
  flow is the latest non-overlapping bar closed before the signal.
- Entry and exit fees/friction are each applied once and normalized by raw entry-to-stop
  risk. ZERO, DEFAULT, and DOUBLE are monotone on identical trade sets; delay is a timing
  profile and may change predictions/trades.

## Evidence portfolio

WP-003 through WP-015 arithmetic and classifications are internally coherent. Negative
families were preserved and parked. Macro/NFCI, regime, interaction, shallow nonlinear,
and funding results remain rejected or cost-dominated. ALIGNED remains the strongest
development clue and correctly remains **INCONCLUSIVE**: it has no sealed/forward evidence
and insufficient breadth for promotion, but no discovered historical implementation
defect justifies demotion.

Reconciliation rating: WP-005 **STRONG**; WP-008 and supervised WP-011 through WP-015
**PARTIAL**. Their model implementations are reconstructed independently, but feature,
label, and execution primitives are shared. “PASS” therefore proves deterministic model
agreement, not a fully independent end-to-end oracle.

## Engineering and product findings

- The runner remains a fixed in-process allowlist with no arbitrary command, path, or
  configuration surface. PID-aware locks now preserve a genuinely live run across a
  second backend instance and recover only dead/legacy owners.
- A NEW_EXPERIMENT candidate is now one-shot after any local attempt. This prevents a
  result-dependent rerun from masquerading as the preregistered first execution.
- WP-016 is visible for auditability but non-runnable in both API and UI. WP-015 remains
  available as reproduction-only.
- Paper JSON writes use unique same-directory staging files; lifecycle read-modify-write
  operations are serialized; persisted safety metadata/records fail closed if forged or
  malformed.
- The full installed-data gate had drifted to nonexistent finalized GDELT/combined
  manifests and omitted funding, attention, and later derived artifacts. It now validates
  the actual five-manifest inventory while preserving the explicit partial GDELT pause.
- The chronological registry, previously ending at an unfinished WP-007 row, now records
  subsequent completed package boundaries. The WP-010 boundary is explicitly marked as
  reconstructed because it lacked a single archived task record.

## Performance and maintainability

The recorded WP-015 reproduction took `1067.810941s`. Static tracing identifies repeated
row-wise sklearn prediction calls, repeated immutable substrate construction, and repeated
profile traversal as the main opportunities. A fixed-seed synthetic benchmark over 10,000
HGBR predictions measured `15.9885752s` row-wise versus `0.0175172s` batched: `912.7358x`
for that operation with maximum absolute difference `0.0`.

No frozen lab was edited: those files are content-bound to preregistrations, and even a
behavior-preserving change would invalidate the recorded code identity. The optimization
should be introduced prospectively as a new version, with exact prediction/trade/artifact
equality and stage timing. Full-workload speedup is not claimed from the microbenchmark.

Future simplification priorities are: version one shared fold/profile orchestration layer;
batch predictions; persist stage timings; key any reusable substrate by code, config,
manifest, and content hashes; and require external vintage guarantees before allocation.

## Readiness verdicts

- Historical results trust: **TRUSTWORTHY AS EXPOSED DEVELOPMENT EVIDENCE**.
- ALIGNED: **UNCHANGED — INCONCLUSIVE PAPER_RESEARCH_CANDIDATE**.
- Paper engine: **BLOCKED_CAUSAL_ENTRY_TIMING_V1** for new entries.
- Research Runner: **READY for WP-015 reproduction; WP-016 disabled**.
- WP-016: **BLOCKED_BEFORE_EXECUTION**.

## Validation

The committed checkpoint passed `scripts/check.py --no-data`: Ruff, format verification,
mypy over 148 source files, 637 backend tests, frontend lint/typecheck, 38 frontend tests,
and the production build. The separate installed-data path passed against the current
five manifests, all governed parquet identities, the preserved partial GDELT cache,
ALFRED point-in-time artifacts, funding raw/as-of data, Wikimedia raw/canonical data,
and the independent BTC/order-flow checks. No experiment adapter ran.

Machine-readable lane findings and evidence paths are in
`reports/audits/PROJECT-RETROSPECTIVE-V1.json`.
