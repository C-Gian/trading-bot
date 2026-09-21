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
