# ADR-0020 — sparse cross-section closes power-blocked and ALIGNED development parks

Status: ACCEPTED NEGATIVE METHODOLOGICAL RESULT. Date: 2026-09-16. Checkpoint:
`CROSS-SECTION-SPARSE-HYPOTHESIS-CLOSURE + ALIGNED-GATE-INTENSITY-POWER-GATE-V1`.

## Context

`ALIGNED_COMMON_CROSS_SECTION_EFFECT_V1` was frozen, built and power-gated without ever
inspecting its true zero-alignment effect. It failed on two independent grounds: the
design resolved only ~44.9 bps/event against a frozen 24.0 bps/event threshold
(power 0.2117 against a 0.80 target), and its analytic two-way clustered inference failed
its own non-zero placebo calibration at 9.2x the nominal size.

## Decisions

1. **Close the sparse hypothesis.** Record the Research Director disposition
   `POWER_BLOCKED_INFERENCE_CALIBRATION_FAILED_NOT_EXECUTED`. It is explicitly not
   `REJECT`, not `INCONCLUSIVE` market evidence, and not evidence that `beta <= 0`. No
   same-hypothesis inference rescue is authorized. All feasibility artifacts are preserved.

2. **Reconcile the two frozen artifacts exactly.** The 3,380 → 3,378 signal and 259 → 258
   cluster differences are fully explained by one typed deterministic rule:
   `epoch_decision_rows < 504`, the participation requirement of the retired position-shift
   placebo. It excluded 35 instrument epochs, of which exactly one — `RIFUSDT#2021-01-07`,
   230 rows — carried signals, and it carried exactly the two missing events. A second
   typed item accounts for the intensity field being 169 rows larger than the outcome
   panel: the outcome panel additionally requires a valid 24h forward return, and it loses
   no signal.

   The reconciliation is exact, but the rule **fails closed**. Its input is the epoch's
   total decision-row count over the whole development window, which is not knowable at
   decision time, and for 6 of the 35 excluded epochs it is co-determined by in-window
   delisting. `EVENT_RECONCILIATION_STATUS = FAIL_CLOSED_NON_POINT_IN_TIME_PARTICIPATION_RULE`.
   The rule never touched the frozen universe, the frozen signal counts, or any market
   result, and it is retired together with the placebo that required it.

3. **Freeze one final ALIGNED descendant.** `ALIGNED_GATE_INTENSITY_COMMON_EFFECT_V1`
   keeps all three frozen gates untouched and scores every eligible asset-hour with the
   unweighted integer sum `int(direction) + int(breakout) + int(participation)`. Verified
   mechanically over 2,556,535 rows: the score is an integer in `0..3`, and
   `ALIGNED_SIGNAL == 1` exactly when `GATE_INTENSITY == 3` (3,380 rows on both sides).
   The gate decomposition is a pure refactor verified row-for-row against the frozen
   engine. One primary coefficient `beta_gate`, threshold `8.0` bps/gate derived as
   `24 / 3`, prospective family size 13, alpha `0.05 / 13`, target power `0.80`.

4. **Replace the failed placebo.** The per-asset position-shift placebo is retired for
   inference. The new `CALENDAR_SYNCHRONOUS_WHOLE_WEEK_YEAR_SHIFT_V1` moves the entire
   cross-sectional score field together: one common signed whole-UTC-week displacement per
   development year, shared by every asset, magnitude 2..13 weeks, never zero, no circular
   wrap, requiring eligibility at both source and destination. 1,024 unique six-year
   vectors were generated from a fixed seed by counter-based SHA-256 over the 24 legal
   displacements; the family hash is
   `7e135af46a20c30d8c1f19e39d56b663254ab293b007c84a694437e82e8cf12d`. Construction depends
   only on the seed and calendar geometry.

5. **Stop before measuring.** `EVENT_RECONCILIATION_STATUS` is a frozen prerequisite of
   the gate. Because it failed closed, the randomization support gate and the prospective
   power stages were **not run**: `RANDOMIZATION_SUPPORT_STATUS` and
   `RANDOMIZATION_INFERENCE_STATUS` are `NOT_RUN_BLOCKED` and no power number exists.
   Measuring power after a prerequisite had already failed would have produced exactly the
   result-dependent framing the governance forbids.

## Consequences

`GATE_INTENSITY_POWER_GATE_STATUS = REDESIGN_REQUIRED`, and therefore
`ALIGNED_DEVELOPMENT_FAMILY_STATUS = PARKED_DEVELOPMENT_SEARCH_EXHAUSTED`. The executor may
not change the score, weight gates, test 2-of-3, test individual gates, add interactions,
alter the horizon, alter the universe, lower MESI, lower power, or try another placebo.

The park is an inherited reconciliation defect in a retired calibration panel, not a
demonstrated power failure of the gate-intensity design. That design remains frozen and
unmeasured, so a Research Director who chooses to reopen it can do so from a clean,
already-preregistered starting point.

As a result-dependent descendant this consumes one adaptive decision and one
result-dependent fork: adaptive decisions 15 → 16, result-dependent forks 12 → 13. No
market outcome was observed, so completed experiments remain 26, known observed material
economic hypotheses remain 12, sealed queries remain 0, Champion remains `NONE`, and real
money remains false. The product universe remains `BTCUSDT_SPOT_V1_UNCHANGED` with no
multi-asset trading, Analyze Market surface, allocation logic or order path.
