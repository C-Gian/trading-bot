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

## Development V1 records (IMPLEMENT-SYSTEM-G1-DEVELOPMENT-V1)

`GET /api/v1/g1/runs` now lists three synthetic registered runs (`kind`):
`CHECKPOINT_1_CONTRACT_FIXTURE`, and two `SYSTEM_G1_DEVELOPMENT_V1_ENGINE` runs of the frozen engine
on a synthetic 2000-2001 path (display configurations S_FULL and S0). No real-market run exists.

For development runs the cursor view `current` block carries:

- `signals` — grouped by `family` (`STRUCTURE_TREND`, `PRICE_LOCATION_VALUE`,
  `MOMENTUM_VOLATILITY`, `PARTICIPATION_FLOW`, `CYCLICAL_STATE`), each with state/quality/role and
  causal `available_at`;
- `cycle` — `decision_role = ACTIVE`, ADR-0046 `timing_qualifier`, `groups`
  (FAST / INTERMEDIATE / SLOW direction and USABLE scales; SLOW recorded only) and six `scales`
  with quality label, slope and last confirmed turn;
- `market_state` — bias, 4h regime, 1h structure, daily corroboration, VWAP location,
  participation, cycle qualifier, supporting/opposing P1/P2 events;
- `prediction` — mixture probability with `probability_status =
  EMPIRICAL_SHRUNK_CONDITIONAL_PROBABILITY_NOT_CALIBRATED`, mean/median/q10/q90, prior risk scale,
  support (`CELL_N`, `SHRINKAGE_W`) or `unavailable_reason`;
- `setups` — recognized P1/P2 triggers with stop, objective, reward/risk and plan veto;
- `decision` — LONG / SHORT / NO_TRADE for the displayed configuration with LOW/MEDIUM/HIGH
  conviction and blockers; trade plans carry stop, objective and planned reward/risk.

The historical Development batch is not reachable through the API; it runs only through
`scripts/run_g1_development.py`, which refuses without a state authorization.
