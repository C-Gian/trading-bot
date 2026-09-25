# Checkpoint — SYSTEM-G1-CHECKPOINT-1-SYNTHETIC-VERTICAL-SLICE

Status: `SYSTEM_G1_CHECKPOINT_1_READY_PENDING_RESEARCH_DIRECTOR_REVIEW`
Evidence class: synthetic fixtures only — not market evidence.
Validation record: `reports/validation/SYSTEM-G1-CHECKPOINT-1-IMPLEMENTATION-VALIDATION.json`.

## What was built

| Stage | Result | Where |
|---|---|---|
| 0 Fail-closed migration | PASS — guard keys on `validated_strategy is null`, not on `PARKED`; analyser never called; paper trades 409; legacy runner 409 unless explicitly authorized | `backend/app/main.py`, `test_fail_closed_action_surface.py` |
| 1 Domain records | PASS — frozen, content-addressed records; append-only `EventStore` refuses re-issue with different content | `app/g1/records.py`, `store.py`, `canonical.py` |
| 2 Aggregation + virtual clock | PASS — 1m -> 3m/15m/1h/4h/1d/1w/1M UTC completed bars with `available_at`; incomplete windows flagged; future observations rejected; start/pause/step/speed; identical records at every speed and under the live-style adapter | `bars.py`, `core.py`, `clock.py` |
| 3 Signed reference-paper ledger | PASS — LONG/SHORT signed P&L, adverse fee/friction, signed funding, next-eligible-minute fill, missing-minute rejection, adverse gap, conservative collision, 4h expiry, one position, 0.25% risk / 1x notional, 1% day and 5% run entry stops; LONG reconciles with the legacy engine | `ledger.py` |
| 4 Prediction/decision/realization | PASS — fixture-controlled emitter (no fitted model); prediction + decision at every eligible 15m candle incl. NO_TRADE; realization is a separate record at +4h; weak / HIGH-but-risk-blocked / LONG / SHORT / conflicting / data-unavailable cases exercised | `pipeline.py`, `fixtures.py` |
| 5 Cycle method | PASS — six frozen scales, streaming ACP reconciled with an independent batch reference (max period diff ~1e-12); causal projection, confirmed turns, warm-up and gap re-warm; decision role always `METHOD_NOT_READY` | `cycle.py`, `cycle_reference.py`, `cycle_diagnostics.py` |
| 6 Replay API + UI | PASS — causal cursor and completed-run review modes; Replay page with chart, prediction glyphs above / decision glyphs below candles, entry/exit marks at simulated minutes, hover details, current panels, matured-only stats | `api.py`, `service.py`, `frontend/src/Replay.tsx` |
| 7 Event/news isolation | PASS — HotWindow/PostAnalysisReport only after completion, separate store, run fingerprint unchanged, no decision-path module imports them; no news fetched | `post_analysis.py` |

API reference: `docs/canonical/SYSTEM_G1_REPLAY_API_V1.md`.

## Cycle quality gate — returned to the Research Director

Artifact: `reports/research/SYSTEM-G1-CYCLE-SYNTHETIC-DIAGNOSTICS-V1.json` (7 fixtures × 6 scales,
regenerates byte-identically via `scripts/build_g1_cycle_diagnostics.py --check`).

- No WEAK/USABLE threshold was chosen. Post-warm-up labels are
  `UNLABELED_THRESHOLDS_PENDING_RESEARCH_DIRECTOR`; decision-path role `METHOD_NOT_READY`;
  `CYCLE_DECISION_ACTIVATION = False`; a test proves forged/active cycle states leave every
  decision unchanged.
- Implementation choices needing adjudication are listed in the artifact
  (`implementation_choices_for_review`): HP/SuperSmoother cutoffs, max-normalization without decay,
  DFT lag range, projection coordinate, turn rule, gap re-warm.
- Observed on fixtures (descriptive only): clean in-band sinusoids are estimated ~3–5% above the
  nominal period (centre-of-gravity bias); white noise yields lower `explained_fraction`
  (median ~0.46–0.67 vs ~0.99); the 3h scale adapts slowly to an abrupt period change.

## Synthetic replay fixture

`G1-SYNTHETIC-VERTICAL-SLICE-FIXTURE-V1`: 3 days of deterministic 1m bars dated 2001 (before BTC
existed), 4 missing minutes, synthetic funding rates, and a scenario script. Its P&L and hit rates
are fixture artefacts, not evidence of anything.

## Governance

- Pre-existing validation drift repaired: `check.py` and one test still expected the Constitution
  3.0 header (now 4.0 with 3.0 verified verbatim as Appendix C); state JSON re-encoded ASCII-escaped
  (a raw em-dash broke locale-default readers).
- `current_project_status.disposition` = strategic disposition; `operational_compatibility_note`
  removed; `action_guard = FAIL_CLOSED_ON_NULL_VALIDATED_STRATEGY`; `validated_strategy = null`;
  NO_TRADE; no market trial / confirmation / prospective collection; Champion NONE; real money false.
- Task archived; `tasks/CURRENT_TASK.md` is review-only
  `RESEARCH-DIRECTOR-REVIEW-SYSTEM-G1-CHECKPOINT-1`.

No real historical G1 outcome was inspected, no market data was accessed, no sealed query was made,
no P1/P2 rule or forecaster was defined or fitted.
