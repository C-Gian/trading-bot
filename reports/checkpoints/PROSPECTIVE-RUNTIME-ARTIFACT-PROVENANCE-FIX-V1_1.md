# Prospective runtime artifact provenance fix V1_1

## Defect

The first local backend start activated the observer at `2026-09-16T12:58:55.229177Z`.
It immediately reported `DEGRADED` with `UNVERIFIED_SCIENTIFIC_BUILD`, evaluated no
boundary, fetched no market data, and was stopped at `13:03:53Z`.

The observer writes its durable health store to `data/paper/`, `.gitignore` covered only
`data/paper/*.lock` and `data/paper/*.lease`, and `BUILD_PROVENANCE_V1` derived
`worktree_clean` from an unrestricted `git status --porcelain`. The observer therefore
dirtied its own repository and invalidated its own build provenance as a direct
consequence of activating. The health file additionally reached the Git index, which
disables ignore rules, so it surfaced as `AM` rather than `??`.

The same latent defect applied to the manual paper ledger
`data/paper/PAPER_TRADES_V2.json`, which was neither tracked nor ignored: an Owner manual
paper trade would have unverified the automated build in exactly the same way.

No repository code mutates the Git index. `scripts/dev.py` runs only uvicorn and the Vite
dev server, no git hooks are installed, and no `git add`, `git commit`, `git stash`,
`update-index` or `write-tree` appears anywhere under `backend/app`. The staged state was
an external local index action on the Owner's machine, not a runtime path, and a test now
asserts the absence of index mutation in runtime code.

## Fix

`data/paper/` holds only generated durable state: the manual paper ledger, the automated
prospective evidence and health stores, and their lock, lease and staging files. No
source, configuration or governance file lives there. Each store is now ignored by
explicit path, with `*.lock`, `*.lease` and `*.staging` patterns alongside.

Because an ignored file that reaches the index stops being ignored, provenance now also
excludes governed runtime artifacts from its dirtiness verdict, and records the remaining
`unverified_paths` so an unverified build states its own reason. The exclusion is narrow:
the observer declares its own three stores explicitly, and the generic rule is limited to
the `data/paper/` runtime directory.

The semantic manifest is untouched and still hashes the exact bytes of the observer,
analysis, continuation, causal execution engine, governed cost implementation and the
evidence contract; modifying any member still fails closed, as does any other tracked
source, configuration or governance change. `worktree_clean` is never unconditionally
true, and a failed git invocation is still never treated as clean.

## Evidence and safety

No genuine prospective observation existed or exists: the evidence store was never
created. The health store is operational state, not scientific evidence. It was preserved
byte-identical, removed from the Git index without deleting the file, and never
committed. Nothing was backfilled, and the boundary that passed while the build was
unverified remains missed.

ALIGNED, the execution geometry, the cost model, manual paper V2 and the
20-completed-trade review boundary are unchanged. Historical accounting remains 26
experiments, 12 observed material historical hypotheses, zero sealed queries, Champion
`NONE`, and real money false. Validation was synthetic throughout; the production
observer was not started and live market data was not contacted during this checkpoint.
