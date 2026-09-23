# CURRENT TASK — IMPLEMENT-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1

Status: ACTIVE_IMPLEMENTATION_ONLY_NO_EXECUTION

Read only:
- `AGENTS.md`;
- `decisions/ADR-0032-OWNER-SELECTS-NO-COST-PUBLIC-DATA-PATH.md`;
- `research/protocols/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md`;
- the smallest existing predictive/source modules needed for implementation.

## Implement

Implement the frozen public taker-flow horizon foundation exactly as specified.

Required code/artifacts:
- official Binance spot + USD-M BTCUSDT 1m kline downloader/acquisition path for 2020-2024;
- checksum/source manifest support;
- deterministic parser and hourly feature builder;
- exact 3 frozen features;
- exact 24h/4h/1h targets and annual 2021-2024 fold construction;
- exact fixed logistic + training-only Platt pipeline;
- exact Brier/control/bootstrap qualification scorer;
- deterministic tests/fixtures covering source parsing, maker/taker arithmetic, timestamp causality, missing-minute failure, folds/purge, bootstrap and horizon selection;
- a single Owner-facing command for source acquisition;
- a single Owner-facing command for the foundation run/validation;
- result/report writers, but DO NOT create result-bearing artifacts yet;
- update any lightweight task metadata needed to make the two Owner commands discoverable.

## Do not execute

Do NOT:
- download the full 2020-2024 dataset;
- run the foundation experiment;
- run full test suites or `scripts/check.py`;
- create market result artifacts;
- alter the frozen protocol;
- add features/models/horizons;
- use post-cutoff/sealed data;
- git add/commit/push/pull;
- inspect/poll GitHub CI.

You may run only trivial syntax/import checks if absolutely necessary to finish coding; otherwise leave execution to the Owner.

## Stop condition

When code is ready, stop and return only:

`CODE_READY`

then:
- changed_files: <count>
- acquire_command: <one PowerShell command>
- run_command: <one PowerShell command>
- expected_outputs: <paths>
- notes: <only if manual prerequisite exists>

## Owner commands (implementation ready)

1. Source acquisition (official archive, checksum-pinned, re-runnable):
   `.venv\Scripts\python.exe scripts\acquire_public_taker_flow.py`
   -> `data/manifests/BTCUSDT-PUBLIC-TAKER-FLOW-KLINES-DEV-v1.json`, raw objects under
   `data/raw/public-taker-flow/` (untracked).
2. Foundation run (verifies the pinned source, runs once, refuses to overwrite results;
   `--check` replays and compares byte for byte):
   `.venv\Scripts\python.exe scripts\run_public_taker_flow_foundation.py`
   -> `research/experiments/EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION/result.json`,
   `reports/research/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md`.

Deterministic tests: `backend/tests/test_public_taker_flow_foundation.py`.
