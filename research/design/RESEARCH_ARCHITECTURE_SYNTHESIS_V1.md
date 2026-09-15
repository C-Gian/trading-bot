# Research Architecture Synthesis V1

Status: ACCEPTED ARCHITECTURAL DIRECTION. This is not a strategy specification and
does not authorize an experiment.

## Two-axis admission

Every future candidate design must pass two separate pre-execution questions:

1. **Economic plausibility / usefulness.** Is the proposed information or mechanism
   capable of supporting a useful BTCUSDT spot decision after realistic costs and
   execution constraints?
2. **Statistical resolvability under available evidence.** Can the frozen design
   distinguish the effect that matters from an appropriately dependent null at the
   declared alpha and target power using the available admissible evidence?

Neither axis substitutes for the other. A plausible mechanism that cannot be resolved
must fail closed or be explicitly classified as exploratory non-resolution evidence. A
resolvable but economically irrelevant pattern is not a trading candidate.

P1A is the concrete sparse-event lesson. The frozen 120-hour ALIGNED information design
had only 180 clustered raw events and power 0.01424888 at its 24.0 bps/event MESI, versus
an empirical MDE of 285.640052 bps/event. Rare-event selectivity is therefore not
automatically desirable: selectivity that removes too much independent information can
make an otherwise interesting claim unresolvable. This was a power result, not market
evidence about the true ALIGNED effect.

## Eventual single-algorithm slots

The intended eventual **single algorithm** may contain independently evidence-supported
modules for:

- market state / trend;
- momentum / breakout;
- participation / liquidity;
- cyclical phase / timing;
- risk and execution;
- other context only when independently supported.

These are architecture slots, not approved components. No slot is filled merely because
it is theoretically attractive. `ALIGNED_PARTICIPATION_CONTINUATION_V1` is not the final
architecture, and its current semantics are not tuned or rescued here. No final-algorithm
component is approved by this synthesis.

## Synthesis rules

- Establish evidence for a module before considering it for composition.
- Preserve negative evidence and root-family/search ancestry.
- Separate component discovery from combined-algorithm evaluation.
- Freeze candidate construction using chronological training only; keep outer
  evaluation unseen until the candidate is fixed.
- Do not optimize module or ensemble weights against outer results.
- A structural finding is not an economic strategy. Any trading rule derived from one
  is a new `MATERIAL_ECONOMIC_HYPOTHESIS` with its own preregistration, MESI translation,
  realistic execution/cost design, multiplicity accounting, and power gate.

The next bounded slot investigation is P2 time structure only. It does not admit a
cyclical module into the final algorithm.
