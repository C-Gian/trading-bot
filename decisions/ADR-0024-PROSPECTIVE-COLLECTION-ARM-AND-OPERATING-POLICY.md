# ADR-0024 — Prospective collection arm and operating policy

Status: ACCEPTED

Builds on [ADR-0022](ADR-0022-ALIGNED-FINAL-CLOSURE-AND-PROSPECTIVE-SHADOW-OBSERVER.md)
and [ADR-0023](ADR-0023-PROSPECTIVE-SHADOW-EVIDENCE-INTEGRITY-V1_1.md).

## Context

`PROSPECTIVE_SHADOW_PAPER_OBSERVER_V1_1` and `FUTURE_SHADOW_PAPER_EVIDENCE_V1_1` are
accepted. The repository is therefore leaving engineering and entering a phase whose
output is produced by the passage of time rather than by work: the value of a prospective
ledger is precisely that each record was written before its outcome was knowable.

That makes the phase unusual to govern. Almost every normal engineering reflex — fix a
detail, adjust a threshold, restart to pick up a change, look at partial results and
react — damages the evidence rather than improving it. The integrity machinery already
enforces the mechanical half of this: an unverified or dirty build cannot record a
decision, a second process cannot write, and missed boundaries can never be
reconstructed. What is missing is the human-facing half, written down before there is any
result to argue about.

## Decision

Record `PROSPECTIVE_COLLECTION_STATUS = ARMED_NOT_YET_OBSERVED`. The observer activates
only when the local backend starts. Opening the backend is not itself an observation: a
genuine one additionally requires a verified clean build, the single observer lease, an
hourly boundary strictly after durable activation, and durable persistence inside the
frozen five-minute window. There is no backfill.

Adopt `PROSPECTIVE_COLLECTION_OPERATING_POLICY_V1`. Semantic code changes must not be
made while the observer is running. Necessary engineering follows a fixed sequence: stop
the backend and observer, preserve existing evidence, make and validate the change,
version evidence semantics if the change is scientifically material, restore a clean
worktree, and only then restart prospectively. A dirty worktree is expected to fail
closed as `UNVERIFIED_SCIENTIFIC_BUILD`, and the boundaries lost while it was dirty stay
missed.

Keep the review boundary at 20 completed automated shadow trades and record explicitly
that this is a minimum freeze boundary, not evidence that 20 trades validate the
strategy. No result-driven strategy adaptation occurs before it. Ordinary `NO_TRADE`
observations and a normal absence of LONG signals are recorded as not justifying
adaptation, because they are the most likely thing to be seen first and the most
tempting thing to over-read.

Early Research Director review is reserved for a persistently degraded observer, an
audit-integrity failure, suspected corruption of genuine evidence, a discovered semantic
software bug, or any proposal to approach a real-money boundary.

## Consequences

The repository's next state change is expected to come from elapsed time, not from a
commit. `tasks/CURRENT_TASK.md` becomes a collection-state record rather than a work
package.

Accounting stays split: historical research remains 26 experiments, 12 observed material
historical hypotheses, zero sealed queries, Champion `NONE`, and real money false, while
prospective counters accumulate separately and are not historical experiments.

The cost of the policy is real. Local development on this repository while the backend
runs will produce missed boundaries instead of observations, and collection will be
slower than the calendar suggests. That is accepted: a gap in observation is recoverable
by waiting, whereas an observation that cannot be tied to a known build, or that a later
edit could have touched, is not recoverable at all.

This ADR governs conduct during collection. It does not authorize real capital, promote a
Champion, or permit reopening historical ALIGNED development.
