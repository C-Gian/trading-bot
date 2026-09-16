# CURRENT TASK — PROSPECTIVE-RUNTIME-ARTIFACT-PROVENANCE-FIX-V1_1

Status: IMPLEMENTED_PENDING_RESEARCH_DIRECTOR_REVIEW

Starting HEAD: `56191d4e197574bf7dc66ea20b6eb3e0274b3db4` on local `main`.

The first local backend start activated the observer, which immediately reported
`DEGRADED` with `UNVERIFIED_SCIENTIFIC_BUILD`. The observer writes its durable health
store to `data/paper/`, `.gitignore` covered only `*.lock` and `*.lease`, and build
provenance used an unrestricted `git status --porcelain`. The observer therefore dirtied
its own repository and invalidated its own build the moment it activated. This is a
semantic software bug and qualified for early review under the frozen prospective
operating policy.

The same latent defect applied to the manual paper ledger, which was likewise neither
tracked nor ignored, so an Owner manual paper trade would have unverified the build too.

Runtime stores under `data/paper/` are now explicitly classified as generated local state
and ignored by Git, and build provenance excludes governed runtime artifacts from the
dirtiness verdict so an artifact that somehow reaches the index cannot silently unverify
the build again. The semantic manifest is unchanged: modifying the observer, ALIGNED,
execution, cost or contract sources still fails closed, and `worktree_clean` is never
unconditionally true.

No genuine prospective observation existed or exists. The health store is operational
state, not scientific evidence; it was preserved byte-identical, removed from the Git
index without deleting the file, and never committed. No boundary was backfilled. The
boundary that passed while the build was unverified remains missed.

ALIGNED, the execution geometry, the cost model, manual paper V2 and the
20-completed-trade review boundary are unchanged. Historical accounting remains 26
experiments, 12 observed material historical hypotheses, zero sealed queries, Champion
`NONE`, and real money false. Validation was synthetic; the production observer was not
started and live market data was not contacted during this checkpoint.

Next action: RESEARCH DIRECTOR REVIEW.
