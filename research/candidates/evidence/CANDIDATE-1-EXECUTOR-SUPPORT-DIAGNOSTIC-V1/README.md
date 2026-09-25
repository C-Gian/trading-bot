# Candidate #1 executor support diagnostic V1 — preserved evidence bundle

Classification (permanent): **`EXPOSED_SUPPORT_DIAGNOSTIC — DIRECTOR_UNAPPROVED_SPECIFICATION`**

Astra adjudication (2026-09-25):
`PRIOR_SUPPORT_DIAGNOSTIC_NONAUTHORITATIVE — ONE_DIRECTOR_FROZEN_ADMISSION_ALLOWED`.

This diagnostic is **not** the terminal Candidate #1 disposition and is not authoritative for
any admission decision. It is preserved because it was run and its counts were observed: the
support information it exposed is part of the Candidate #1 lineage. It must never be deleted,
edited, re-run as an admission, or cited as a rejection.

## What it was

An executor-authored source/timing/support audit, run once during
`GOVERNANCE-TRANSITION-AND-CANDIDATE-ADMISSION-V1` (starting HEAD
`c163887d16610ce884d0e3a8c326204df4122a79`, uncommitted working tree), before any Research
Director or Astra specification existed. No forward return, label, outcome, model or
post-cutoff data was computed or accessed; sealed queries 0.

Executor-selected specification (never approved):

| Element | Executor choice |
|---|---|
| Sell-off | trailing 24h spot log return at `T` <= -0.05 (reference; -0.075 and -0.10 also counted) |
| Separation | 72h declustering after each event |
| Joint state | 24h OI log change < 0 **and** 24h perp-minus-spot relative-price change < 0 |
| OI timing | `create_time <= T - 5m`, age <= 15m (contract rule also reported) |
| Relative price | `log(UM_PERP_1M_CLOSE / SPOT_1M_CLOSE)` on the completed minute `[T-1m, T)` |
| Admissible years | 2022-2024 (carried-forward OI restriction) |
| Feasibility floor | >= 30 pooled admissible events per arm; completeness >= 0.90; hourly joint availability >= 0.95 per year |

Observed counts (reference threshold, 2022-2024): **73 events, 25 joint-state, 48
complement**; `support_feasible: false` under the executor floor. Full output in
`original_CANDIDATE-1-SOURCE-SUPPORT-ADMISSION-V1.json`.

Assumptions: OI archive publication lag unproven (residual assumption of
`PREDICTIVE_OPEN_INTEREST_STRUCTURE_V1`); 1m closes are last trades within the minute
(asynchrony <= 1 minute); 448 exact-zero OI quantities treated as unavailable.

## Contents (sha256 over the files as written, LF)

| File | sha256 | Original location |
|---|---|---|
| `original_audit_candidate_1_admission.py` | `945f93029c8e9d11a9de38af84cdc08c79e9ef6f8ed6907732504a94274685b3` | `scripts/audit_candidate_1_admission.py` (version `CANDIDATE_1_SOURCE_SUPPORT_ADMISSION_AUDIT_V1`) |
| `original_CANDIDATE-1-SOURCE-SUPPORT-ADMISSION-V1.json` | `07907158e7c7184a054628d72e27e673a4cbb593b94d888f5f51f0771971a451` | `reports/validation/CANDIDATE-1-SOURCE-SUPPORT-ADMISSION-V1.json` |
| `original_ADR-0037-draft.md` | `de44d864f812d4029a36dc3b58d188a48c4b47c044433bd584e9b4e07cd1063c` | `decisions/ADR-0037-CANDIDATE-1-SOURCE-SUPPORT-ADMISSION-BLOCK.md` (uncommitted draft) |
| `original_candidate_card_draft.md` | `e68ed73c4547134ba4279753a049889d2224bd07f29d4a7f32ce6514e65b503b` | `research/candidates/CANDIDATE-CARD-1-…md` (uncommitted draft) |
| `original_state_governance_transition_v3.json` | `6937670f9ec271555d693091b85de4b20e3f993acc41b9898c3b6167fe68e1cc` | `state/current_state.json` → `governance_transition_v3` (uncommitted draft) |
| `original_checkpoint_draft.md` | `4ec947661f0faba4fa840effd492b0702cb2f3ed21a83df67bb1c5100a68dc3d` | `reports/checkpoints/GOVERNANCE-TRANSITION-AND-CANDIDATE-ADMISSION-V1.md` (uncommitted draft) |
| `original_next_task_draft.md` | `4143b82be102addbba38262765e9afaee60a84f0fcbb712566ffcd008ccf96d5` | `tasks/CURRENT_TASK.md` (uncommitted draft) |
| `original_allocation_map_draft.md` | `12042519dc65ad1383d9bbd4f5b3e0a06e974e76b50627f034a71a559685b674` | `docs/canonical/STRATEGIC_ALLOCATION_MAP_V1.md` (uncommitted draft) |

Inputs it read (unchanged):

| Input | sha256 |
|---|---|
| `data/manifests/BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1.json` | `cf696350cfe6294ffcbb74bef657ba9e58be22d232e7aab30c9cc7aa4c204bc4` |
| `data/manifests/BTCUSDT-USDM-OPEN-INTEREST-DEV-v1.json` | `f7bfbb460528cc3e9aa5b0babaf66545293dbcfc5c3a9845cd8e5f6c4831782c` |
| `data/derived/BTCUSDT-USDM-open-interest-5m-v1.parquet` | `1050081fe37dabca539fa0c4543adfe802251d8a03026ec9b949bd025e0bb8b6` |
| `backend/app/predictive/taker_flow_source.py` | `83cab4b5cfcf785e1eb7c664b64fb66b8da086858e8ccc076af7db293e8bd644` |
| `backend/app/predictive/open_interest_source.py` | `202af5d0a0eb38b25b7d1e422bf1befae59da29cfe7238aafcf595879da2a280` |

The preserved script resolves `ROOT` as its own parent's parent; to replay it, copy it back to
`scripts/` unchanged and run `--check` against the preserved record at its original path.
