# CURRENT TASK — P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE-PREP

Status: COMPLETED_PENDING_RESEARCH_DIRECTOR_REVIEW

POWER_GATE_STATUS: REDESIGN_REQUIRED

Starting HEAD: `44c604508e470e4e06fa6ac5334d2c12f49c3d3e` on local `main`.

Design and prospective power analysis only for the future material hypothesis
`ALIGNED_SIGNAL_PERSISTS_TO_120H_V1`. The checkpoint did not answer whether the frozen
ALIGNED signal carries positive directional information persisting to five days; it
determined only whether BTC-only development data can answer that question at the Owner's
economic threshold.

The design is frozen in `research/design/ALIGNED_SIGNAL_PERSISTENCE_V1_DESIGN.md` with
rationale in `decisions/ADR-0013-P1A-ALIGNED-SIGNAL-PERSISTENCE-POWER-GATE.md`: 120h
primary horizon, 120h forward return in bps from the governed next-1m open to the close
of the 1m bar opening at signal + 7199 minutes, no stop/target/trailing/R denominator and
no one-position-at-a-time rule, raw ALIGNED events unaffected by portfolio occupancy, and
a matched control of deterministic within-fold circular calendar shifts with a minimum
absolute displacement of 168 positions.

180 raw ALIGNED events survive the 120h containment requirement (38/37/12/7/43/43 across
the six fixed annual folds), down from 195 emitted conditions on the historical
24h-containment window. All 7369 admissible shifts were enumerated deterministically; the
minimum attainable randomization p-value of 1/7370 clears `alpha_effective = 0.05/13`.

At the frozen `P1A_INFORMATION_MESI_BPS = 24.0`, empirical power is 0.0142 against an
empirical MDE of 285.640052 bps/event, so the gate fails closed. P1A was not
preregistered, no runner candidate was registered, no other horizon was tried, the MESI
was not lowered and no asset was added.

No zero-shift statistic, ALIGNED-minus-placebo effect, P1A p-value or P1A performance
classification was computed or recorded. ALIGNED semantics and all stop/target/volume/
trend/breakout parameters are unchanged. `experiments_completed` remains 26, observed
material hypotheses remain 12, sealed queries remain 0, Champion remains NONE and real
money remains false.

Full local validation passed on a clean tree and exact head
`8d3286a29093e542ed2fdeff5c457666dca5ea66` passed GitHub Actions run `34993308932`.

Next action: Research Director review of the redesign decision.
