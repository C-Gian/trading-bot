# System G1 Replay API V1 (Checkpoint 1, synthetic only)

Thin FastAPI boundary: `backend/app/g1/api.py` -> `backend/app/g1/service.py`. The UI displays
these payloads and computes no authoritative trading outcome. No route accepts a scientific
parameter, threshold, price, plan or timestamp.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/g1/status` | generation, disposition, `validated_strategy` (null), operational `NO_TRADE`, cycle method status |
| GET | `/api/v1/g1/runs` | the registered synthetic run manifest(s) |
| POST | `/api/v1/g1/replay/sessions` `{run_id}` | new causal replay session at the dataset start |
| GET | `/api/v1/g1/replay/sessions/{id}` | **causal cursor view** |
| POST | `/api/v1/g1/replay/sessions/{id}/control` `{action: start\|pause\|step\|speed, speed?, unit?}` | replay control; `speed` only from the fixed pacing list |
| POST | `/api/v1/g1/replay/sessions/{id}/tick` `{wall_seconds}` | UI pacing: advances `speed * wall_seconds` of virtual time while running |
| GET | `/api/v1/g1/runs/{run_id}/review` | **completed-run review view** (whole run, exposure record, fingerprint) |
| POST | `/api/v1/g1/runs/{run_id}/post-analysis` | after completion only: HotWindows + placeholder PostAnalysisReport, stored separately |

## View modes

- **Causal cursor view** (`mode = CAUSAL_CURSOR`): only records with `available_at <= cursor`:
  completed 15m candles, issued PredictionSnapshots, DecisionSnapshots (including `NO_TRADE`),
  TradePlans after readiness, fills after execution, PredictionRealizations only after the +4h
  target matured, the latest signal/cycle/state/prediction/decision panel, the ledger snapshot and
  matured-only running statistics. `production_action` is always `NO_TRADE`.
- **Completed-run review view** (`mode = COMPLETED_RUN_REVIEW`): every record of the completed run.

Speed changes wall pacing only; the core processes every minute boundary in event-time order, so
record identities are identical at every speed and under the live-style adapter.

The production action surface (`/api/v1/product/*`) is unaffected and fails closed while
`current_project_status.validated_strategy` is null.
