# ADR-0017 — canonical gaps defeat the frozen Null V2 long-block support gate

Status: ACCEPTED NEGATIVE METHODOLOGICAL RESULT. Date: 2026-09-15. Checkpoint:
`P2-CYCLE-NULL-V2-REDESIGN + P2-CYCLE-POWER-GATE-V2`.

## Context

Null V2 and its support rule were committed in `87b4bf2` before donor topology was
measured. The method draws raw training-only contiguous 4h returns in stationary blocks
with expected length 1,080, terminates at every canonical source gap, and tests no other
length. Every fold was required to retain same-block survival of at least 0.50 at lag
540 before fidelity could run.

## Result

`BLOCK_SUPPORT_STATUS = REDESIGN_REQUIRED`. All six folds fail. Lag-540 survival is
0.0685355004, 0.0698315312, 0.0514556200, 0.0700931254, 0.1475164933 and
0.1982639388 for DEV-2019 through DEV-2024. Maximum contiguous donor segments are 807,
807, 807, 928, 2,216 and 3,245 observations; the exact realized mean block lengths after
forced termination are only 221.97, 213.56, 208.82, 212.83, 294.59 and 359.06.

The canonical gap topology therefore collapses the effective 90-day dependence horizon
despite the ideal gap-free geometric survival of about 0.61. The result is a property of
the preregistered gap-safe mechanism, not a reason to reinterpret gaps as contiguous.

## Decision and consequences

Stop. Do not alter 1,080, wrap across gaps, interpolate returns, try another block
length, reintroduce AR, or add GARCH/HAR/FIGARCH. Null V2 fidelity, joint spectral proof,
compute benchmarking and synthetic detectability were not run. Consequently
`P2_POWER_GATE_STATUS = REDESIGN_REQUIRED` and the actual P2 structural result remains
unobserved and unclassified.

This is not evidence against cycles. It is evidence that the frozen raw-return
long-block null cannot preserve the required dependence horizon on the canonical
eligible-return topology under honest gap semantics. The next action belongs to the
Research Director.

