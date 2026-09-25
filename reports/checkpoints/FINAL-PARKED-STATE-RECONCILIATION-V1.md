# Checkpoint — FINAL-PARKED-STATE-RECONCILIATION-V1

Status: **PARKED_STATE_RECONCILIATION_READY**. Finite archival/governance closure under
[ADR-0042](../../decisions/ADR-0042-PARK-ACTIVE-ALPHA-RESEARCH.md). Pre-closure HEAD `8c680143`.
No market experiment, outcome inspection, data access or new research.

## Reconciled

- **State:** new top-level `current_project_status` (disposition
  `PARKED_NO_CREDIBLE_EDGE_UNDER_CURRENT_CONSTRAINTS`, zero allocation, no active Candidate,
  Candidate #1 closed, #2 unallocated, NO_TRADE output, no trial / confirmation / collection, no
  automatic next package, Champion NONE, real money false, sealed 0) with explicit precedence over
  the listed historical top-level fields (phase, selected family, ALIGNED product analysis, paper
  trading, prospective collection, runner, prediction-first objectives). Nothing was deleted.
  `governance_transition_v3` now records ADR-0042, the parked project state, the parked allocation
  posture and the reviewed Execute checkpoint. Schema reconciled with the Director's ADR-0041/0042
  values; state and schema validate.
- **Operating files:** `AGENTS.md` and `docs/operations/NEW_CHAT_BOOTSTRAP.md` open with the
  parked status, the no-resume rule, NO_TRADE, reopening (dossier + Astra; Owner for material
  scope) and the real-capital gate.
- **Automation:** no active project-internal alpha/prospective schedule exists. The ALIGNED shadow
  observer is already suspended in code (`AUTOMATIC_COLLECTION_ENABLED = False`); CI has no
  schedule. Implementations are preserved; nothing was run or scheduled.
- **App action surface (smallest change, `backend/app/main.py`):** while parked,
  `POST /api/v1/product/analysis` returns `decision: NO_TRADE`, `plan: null`,
  `data_status: RESEARCH_PARKED`, `research_status: PARKED_NO_VALIDATED_STRATEGY` without
  evaluating the ALIGNED strategy; the capability endpoint reports `PARKED_NO_TRADE`; paper-trade
  creation and research-run start return 409. One copy line in `frontend/src/format.ts` renders
  the parked reason. Hash-pinned product modules (`analysis.py`, `paper_v2.py`) are unchanged.
- **Validation:** `scripts/check.py` gains `parked_state_checks` (state, task, operating files and a
  live fail-closed API probe).
- **Preservation:** `reports/handover/PARKED-STATE-PRESERVATION-MANIFEST-V1.md`.
- **Task:** archived to `tasks/archive/FINAL-PARKED-STATE-RECONCILIATION-V1.md`;
  `tasks/CURRENT_TASK.md` is `PARKED-NO-ACTIVE-RESEARCH-TASK` (no executor work, no scheduled
  review).
