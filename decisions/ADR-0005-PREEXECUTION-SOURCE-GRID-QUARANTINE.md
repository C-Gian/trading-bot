# ADR-0005: Pre-execution quarantine of off-grid source intervals

Status: Accepted before any WP-004 strategy result or execution-profile attempt.

The first loader invocation after preregistration failed closed on 21,602 source
timestamps off the UTC minute grid. Source-hash verification passed. Timestamp-only
inspection located two intervals in December 2017 and February 2018; no signal or
strategy outcome was calculated. The immutable abort record preserves this event.
The accepted dataset, its source objects, manifest and WP-003 results stay unchanged.

Row count alone does not prove a derived hour is complete: a last minute starting
late can end after the nominal close. Feature version V2 therefore marks every
1h/4h bucket intersecting an off-grid source interval [open,open+1m) ineligible,
even if the existing derived count-based flag says complete. Source timestamps are
never rounded, repaired or forward-filled. The existing simulator still rejects
nonconsecutive path minutes and unavailable exact entry opens. Global data admission
checks ordering/cutoff and records the anomaly; valid later windows remain usable.

These anomalies end long before the first 2019 validation fold and its warm-up.
This is a timestamp-integrity correction, with zero strategy outputs observed,
not a result-driven strategy filter or an additional tested variant. Full-history
WP-003 interpretations gain a data-availability limitation; those records are not
rerun or corrected in this allocation. Sliced 2019–2024 comparisons avoid these
intervals but retain their other stated comparability limitations.

Keep each original preregistration and admission immutable. Add experiment-version
2 preregistrations at `preregistration.v2.json` and an immutable amendment registry
linking old/new hashes and this zero-trial abort. Commit corrected implementation
before version-2 preregistrations, then commit all amendments before execution.
The same three hypotheses/configurations and 12 profiles remain allocated; version
1 never reached a strategy trial. Final results must link only to the effective
version-2 declaration. Any later result-affecting correction would require a new
scientific allocation; this pre-execution exception cannot overwrite observed results.
