# Research Search Memory V2

Status: active for all future material strategy research after WP-005.

SEARCH_MEMORY_V2 binds admission and execution to one canonical, strongly typed
`ExecutableStrategySpec`. The spec represents the root/family, entry event,
feature primitives, lookbacks and time scales, transformations, comparisons and
thresholds, regime and confirmation gates, signal/context clocks, direction,
reference price, stop, exit/target, holding horizon, timing perturbation,
position policy, and execution/cost references.

The runner and admission gate must receive the same spec object. A fingerprint is
derived from that spec; callers cannot supply a different fingerprint or behavior
hash. A changed runtime spec invalidates the admission. Missing spec identity is a
hard failure.

Four identities are produced:

- exact behavior hash, excluding dataset/cost/execution environment identity;
- numeric-masked structural hash for parameter-drift recognition;
- complete executable-spec hash, including environment references;
- implementation/config dependency hash.

Changing only data or costs therefore does not create a behavioral family.
Numeric drift stays a parameter variant. An orthogonal gate with the same anchored
entry mechanism stays a descendant/mechanism change. Labels and aliases cannot
reset root-family budgets. Exact executable behavior is a duplicate regardless of
its proposed name.

V2 governs declared executable specs, not arbitrary Python equivalence. The nine
WP-003/WP-004 records retain their original evidence and chronology. Their V2
signatures are deterministic reference translations used only to reject duplicates
and locate family ancestry; they do not claim retrospective executable validation.
