# ADR-0025 — Runtime artifacts are not scientific build state

Status: ACCEPTED

Corrects a defect in [ADR-0023](ADR-0023-PROSPECTIVE-SHADOW-EVIDENCE-INTEGRITY-V1_1.md);
its integrity decisions otherwise remain in force.

## Context

ADR-0023 made a scientific build unverifiable whenever the working tree was dirty, on the
reasoning that a commit says nothing about whether the tree that produced an observation
matched it. That reasoning is sound, but the rule was applied to the whole working tree
without distinguishing what the tree contains.

The observer keeps its durable stores inside the repository, under `data/paper/`. So the
first local backend start produced a self-defeating result: the observer activated, wrote
its own health store, and that write made its own build unverified. It reported `DEGRADED`
with `UNVERIFIED_SCIENTIFIC_BUILD` before it could evaluate anything. The integrity
mechanism was not too strict in principle; it was measuring the wrong thing.

The same defect applied to the manual paper ledger, which was equally untracked and
unignored: an Owner manual paper trade would have unverified the automated build.

A second detail mattered. The health file surfaced as `AM`, not `??`, because it had
reached the Git index, and an ignored file that is in the index stops being ignored. So
ignore rules alone are a necessary but not sufficient remedy.

## Decision

Classify `data/paper/` as generated local runtime state. It holds the manual paper
ledger, the automated prospective evidence and health stores, and their lock, lease and
staging files, and nothing else: no source, configuration or governance file lives there.
Each store is ignored by explicit path, alongside `*.lock`, `*.lease` and `*.staging`
patterns.

Additionally, exclude governed runtime artifacts from the provenance dirtiness verdict,
so that an artifact which somehow reaches the index cannot silently unverify the build
again. The exclusion is deliberately narrow: the observer declares its own three stores
explicitly, and the generic rule is confined to the `data/paper/` runtime directory and
runtime suffixes. Provenance also now records the remaining `unverified_paths`, so an
unverified build states its own reason instead of being a bare flag.

The core invariant is unchanged. The semantic manifest still hashes the exact bytes of
the observer, analysis, continuation, causal execution engine, governed cost
implementation and the evidence contract. Modifying any manifest member still fails
closed, as does any other tracked source, configuration or governance change.
`worktree_clean` is never unconditionally true, and a failed git invocation is still
never treated as clean.

## Consequences

The observer can now activate under a verified build instead of unverifying itself, and
the manual paper workflow no longer interferes with automated provenance.

Generated runtime state is, by this decision, outside the scientific build identity. That
is the correct boundary — the evidence store's integrity is protected by the audit chain
and its own atomic durable writes, not by Git — but it does mean provenance alone says
nothing about the contents of the ledger. The tamper-evident chain remains the mechanism
that governs the evidence itself.

No genuine prospective observation existed when this defect was found, so nothing was
lost, reinterpreted or backfilled. The health store was preserved byte-identical, removed
from the Git index without deleting the file, and never committed. The boundary that
passed while the build was unverified remains missed, as the frozen operating policy
requires.

One gap is recorded here rather than acted on, because it expands scope beyond this
defect: `provenance.py`, `audit_chain.py` and `observer_lease.py` are not themselves
semantic manifest members, so a future change to the integrity machinery would not move
the build identity. With zero observations recorded this is currently harmless, and it is
left to the Research Director to decide.
