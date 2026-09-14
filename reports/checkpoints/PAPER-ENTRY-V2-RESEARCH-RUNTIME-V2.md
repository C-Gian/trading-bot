# PAPER-ENTRY-V2 + RESEARCH-RUNTIME-V2

Status: **PASS**.

Stage A was committed independently at
`63bbcf8ab6531926fbede318218eacddb3086004` and passed the repository-wide no-data
checker from a clean tree. `PAPER_EXECUTION_V2_CAUSAL_NEXT_MINUTE` now persists an
unarmed Owner-manual intent before any entry observation and permits only a completed
1m open strictly later than its durable server timestamp. V1 remains unchanged and
blocked; no genuine paper trade was created.

Stage B adds `RESEARCH_RUNTIME_V2_BATCH` for future explicit preregistration only.
Ordered batch prediction, deterministic fold traversal, exact positive thresholding,
shared ZERO/DEFAULT/DOUBLE prediction views, DELAY_1H alignment, and fixed-stage timing
records are tested. Research Runner candidates now expose and persist an explicit
runtime binding; existing WP-015 reproduction stays on `WP015_FROZEN_RUNTIME_V1`, while
WP-016 stays disabled on `WP016_PREREGISTERED_RUNTIME_V1`.

The engineering benchmark measured 10,000 synthetic predictions at `8.4899511s`
row-wise and `0.0180344s` batched (`470.7643x`). A governed 513-row WP-015 DEV-2020
sample measured `0.4206421s` row-wise and `0.0016754s` batched (`251.0697x`). Both had
maximum difference `0.0` and zero signal mismatches. The governed model identity,
signals, DEFAULT trade identities and metrics, cost-profile reuse, and delay alignment
matched. No whole-experiment speedup is claimed and no cache was introduced.

This checkpoint changes no experiment result or counter, sealed query, development
cutoff, ALIGNED gate, Champion, genuine paper count, or real-money state. WP-016 remains
`BLOCKED_BEFORE_EXECUTION` because its historical Wikimedia vintage identity is not
demonstrable.

## Validation

- Backend: 671 tests passed.
- Frontend: 41 tests passed; lint, typecheck, and production build passed.
- Static analysis: Ruff check and format verification passed; mypy passed across 153
  source files.
- Focused runtime, runner, and paper tests: 99 tests passed.
- Repository checker: `python scripts/check.py --no-data` passed from the clean,
  committed Stage B implementation.
- Safety: no V2 paper store was created and WP-016 has no result artifact.
