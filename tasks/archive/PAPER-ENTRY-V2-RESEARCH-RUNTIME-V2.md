# CURRENT TASK — PAPER-ENTRY-V2 + RESEARCH-RUNTIME-V2

Status: COMPLETED_PENDING_RESEARCH_DIRECTOR_REVIEW

Starting HEAD: `a30783888ffc719133a24332ff334a658f5c3010` on local `main`.

This is an engineering checkpoint with no trading experiment. Stage A introduces a
separate durable-intent-first causal paper entry version while preserving blocked V1.
Stage A was validated and committed independently at
`63bbcf8ab6531926fbede318218eacddb3086004`. Stage B adds the prospective
`RESEARCH_RUNTIME_V2_BATCH` without changing the frozen historical implementations.
See `reports/checkpoints/PAPER-ENTRY-V2-RESEARCH-RUNTIME-V2.md`.

WP-016 remains `BLOCKED_BEFORE_EXECUTION`; it must not run or be re-enabled. Scientific
counters, historical experiment artifacts and frozen ALIGNED semantics remain unchanged.
