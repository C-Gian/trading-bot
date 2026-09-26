# Methodological qualifications V1 (append-only)

Recorded 2026-09-25 under `GOVERNANCE-TRANSITION-AND-CANDIDATE-ADMISSION-V1`
([ADR-0036](../../decisions/ADR-0036-OWNER-PRACTICAL-ECONOMIC-OBJECTIVE-AND-CONSTITUTION-V3.md)).

These qualifications are appended to the record. They do not rerun, rewrite, reclassify or
rescue any historical result, and no historical artifact is modified. Later qualifications are
appended as new sections or new versions of this file; existing sections are never edited.

## Q-001 — Incremental power-gate sign-description mismatch

Scope: `EXP-PRED-V2-006-PUBLIC-TAKER-FLOW-1H-INCREMENTAL`,
`reports/validation/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-GATE-V1.json`,
[ADR-0035](../../decisions/ADR-0035-PUBLIC-TAKER-FLOW-1H-INCREMENTAL-POWER-BLOCK.md).

The frozen prose and code metadata describe the proxy series as
`FLOW_ONLY_BRIER_LOSS - TRAINING_BASE_RATE_CONSTANT_BRIER_LOSS` (flow minus constant), while the
executable foundation differences consumed by the replay are control Brier loss minus model
Brier loss (constant minus flow — an improvement orientation, consistent with the observed
pooled proxy mean +0.0006438 equal to the foundation's 1h Brier improvement).

Preserved exactly: the original artifacts; deterministic replay PASS; power_at_mesi = 0.1871;
analog MDE = 0.0005414; classification `POWER_BLOCKED_NOT_EXECUTED`; EXP-PRED-V2-006 model
fits = 0; no incremental market result exists.

This qualification corrects a description, not a computation, and never authorizes a rerun or
a corrected rescue of the gate or the experiment.

## Q-002 — Macro contamination reasoning

Scope: [ADR-0028](../../decisions/ADR-0028-GENERATION-V2-SELECTIVE-LONG-REBASELINE.md) §2
("a lookahead can only make a candidate look better"), the Stage-3 macro vintage and macro
release-state results and the residual source finding
`reports/validation/PREDICTIVE-STAGE3-MACRO-RELEASE-STATE-V1-RESIDUAL-SOURCE-FINDING.json`.

The claim that look-ahead contamination can only improve a fitted candidate is not logically
valid: contaminated inputs can also add noise, shift the fitted relationship, or be absorbed
differently by the matched control, so contamination can bias a comparison in either
direction.

Preserved: the original macro results and their rejection, the source finding, the prospective
`ALFRED_OBSERVATION_DATE_GUARD_V1` contract, and the exhausted macro source-redesign budget.
Qualification: those macro results are **not a clean point-in-time falsification** of macro
information. This does not rerun or reopen the macro allocation, whose current disposition is
set by `docs/canonical/STRATEGIC_ALLOCATION_MAP_V1.md` (context only where required; no general
predictor programme).

## Q-003 — Generation V2 pooled enrichment composition

Scope: `PREDICTIVE_RESEARCH_GENERATION_V2` pooled selective enrichment
(`SELECTIVE_LONG_WIN_RATE - FULL_FOLD_UP_RATE`, pooled across folds), the V2 calendar and
internal-structure selective families.

The pooled enrichment compares the action sample with a pooled ambient reference. When actions
are distributed across folds/years differently from the ambient timestamps, the pooled contrast
partly reflects fold/year composition rather than within-period selection skill.

Preserved: every old V2 rejection and classification. For all future selective evaluation, the
contrast must be matched within fold, or otherwise composition-controlled, and defined before
outcomes (Constitution Version 3.0, "Economic and predictive quantities").


## Q-004 — Stopped Phase-A policies do not measure unrestricted 2022 opportunity counts

Scope: System G1 Phase A, especially `S0` and `S_MINUS_CYCLE`.

Both policies triggered the frozen run-level drawdown stop in 2021. Their 2022 trade count of zero
therefore describes the **executed stopped policy path**, not an unrestricted count of how many base
setups/opportunities might otherwise have appeared in 2022.

Preserved exactly: the frozen risk rule, the observed stopped paths, their negative economics and
selection-stage rejection.

This qualification does not authorize resetting/removing the stop or rerunning G1.

## Q-005 — Zero executed P2 trades does not locate the P2 recognition bottleneck

Scope: `SYSTEM-G1-P2-FAILED-AUCTION-REENTRY`.

`S_P2_ONLY` produced zero executed/scorable trades and `S_P1_ONLY` matched `S_FULL`.

This establishes that P2 contributed no full-configuration executed trade in Phase A.

It does **not** establish which stage prevented execution: raw boundary excursion, re-entry,
4h RANGE classification, participation/cycle corroboration, reward/risk admissibility, occupancy,
data readiness or another frozen gate.

No historical funnel analysis or favorable relaxation is authorized. P2's exact G1 construction is
closed.

## Q-006 — G1 conjunction ablations do not identify standalone component alpha

Scope: comparisons among `S_FULL`, `S_MINUS_CYCLE`, `S_MINUS_PARTICIPATION`,
`S_MINUS_DAILY_HTF` and `S0`.

Differences in trade counts and P&L arise from different admission paths, occupancy, risk-stop
trajectories and later system states. They are not clean causal estimates of cycle, participation or
daily context as standalone predictors or alpha sources.

Preserved: the full seven-configuration rejection and all component-role uncertainty.

This qualification neither validates nor disproves those components outside their exact G1 roles.

## Q-007 — Phase-A selection summary does not adjudicate continuous-forecast quality

Scope: System G1 continuous 4h prediction layer.

The canonical Phase-A selection artifact contains trade/configuration selection metrics but no
complete forecast score table.

Therefore no conclusion is authorized from Phase A about whether the forecaster was accurate,
inaccurate, calibrated, uncalibrated in practice, or economically useful.

Preserved: the model's declared
`EMPIRICAL_SHRUNK_CONDITIONAL_PROBABILITY_NOT_CALIBRATED` status and the requirement that any
future allocation score all matured forecasts separately from trade-policy economics.

No extra G1 forecast run/report is authorized by this qualification.
