# PAPER-ENTRY-V2 — Stage A safe checkpoint

Status: **PASS**.

`PAPER_EXECUTION_V2_CAUSAL_NEXT_MINUTE` restores manual paper entry through a separate
V2 store and contract. V1 remains unchanged and blocked. The server now durably commits
an unarmed LONG intent before taking its authoritative persistence timestamp, then allows
only completed 1m bars with `open_time > intent_persisted_at`. Exact-boundary persistence
advances to the following minute. Missing opportunities advance an immutable cursor;
five unavailable opportunities invalidate the intent. Transport failure advances
nothing.

Actual future fill price anchors the unchanged 2% stop, 4% target, and 1,440-minute
horizon. Pending UI records show no fabricated price levels and expose decision time,
earliest entry, and signal age. Records are `MANUAL_PROSPECTIVE_PAPER` / `OWNER_MANUAL`.
Caller-supplied plan fields are rejected. Flushed atomic writes, same-path thread and
operating-system lifecycle locking, restart recovery, malformed-fill rejection,
terminal immutability, and no-order/no-credential boundaries are covered by
deterministic synthetic tests, including concurrent backend processes on Windows.

Research Director acceptance of PROJECT-RETROSPECTIVE-V1 is recorded as
`ACCEPTED_WITH_BLOCKERS`. WP-016 remains disabled and unexecuted. Historical evidence,
ALIGNED status, scientific counters, genuine paper count, sealed queries, Champion, and
real-money state are unchanged.

Validation: 659 backend tests and 40 frontend tests passed. Ruff, format verification,
mypy, and frontend lint/typecheck/build passed. `scripts/check.py --no-data` is run from
the clean Stage A commit because clean-tree verification is one of its final assertions.
No genuine paper trade was created.
