# WP-002 Research Director review

Verdict: `ACCEPTED_WITH_FIXES`

Reviewed HEAD: `47dd69d73768a9e3a3c92fe08eb1e7e3e8c239f5`.

WP-002 preserved the dataset and boundary, restored state-backed APIs, improved record validation and UI tests, characterized gaps, and prospectively documented execution assumptions without introducing forbidden scope.

Mandatory WP-003 remediation: R1 clean-checkout packaging/CI; R2 explicit same-boundary event ordering and V2 model versions; R3 target-at-open precedence; R4 contiguous lookbacks; R5 parsed UTC cutoff checks; R6 engine cutoff and signal-clock defense; R7 positive-duration splitter validation; R8 runner-owned declared trial accounting and content identity; R9 main-only sequential workflow.

Market experiments remain unauthorized until the deterministic WP-003 pre-experiment gate passes.
