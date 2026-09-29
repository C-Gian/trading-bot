"""G2-02 fixed development batch runner (EXPOSED DEVELOPMENT EVIDENCE, NOT VALIDATION).

Usage:
    python scripts/run_g2_development.py --authorize            # append the ledger record
    python scripts/run_g2_development.py --execute --progress   # simulate + build + ledger
    python scripts/run_g2_development.py --build --progress     # rebuild artifacts from cache
    python scripts/run_g2_development.py --check                # artifact/ledger consistency

`--execute` refuses to run without the prior ledger authorization or when any authorized code
file changed since. `--check` never simulates: it verifies the committed artifacts, the ledger
order and the code binding, and, when the local run cache exists, rebuilds every scorecard from
it and requires byte-identical artifacts. Progress is operational telemetry under `.runtime/`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.g2.development import batch
from app.g2.development.runner import AUTHORIZATION_RECORD, CACHE_DIR
from app.g2.validation import text_sha256
from app.operations.jobs import Job, stderr_echo

BUILD_PHASES = ["load run cache", "score and bootstrap", "write artifacts"]


def build_and_write(job: Job, log_lines: list[str] | None) -> tuple[dict, dict[str, str]]:
    job.phase("load run cache")
    job.phase("score and bootstrap", message="forecast CRPS, policy, execution, uncertainty")
    started = time.monotonic()
    built = batch.build(ROOT)
    if log_lines is not None:
        log_lines.append(f"scoring/bootstrap/autopsy built in {time.monotonic() - started:.1f}s")
    job.phase("write artifacts")
    written = batch.write_artifacts(ROOT, built, log_lines)
    return built, written


def check() -> None:
    ledger = batch.read_ledger(ROOT)
    ids = [entry["record_id"] for entry in ledger]
    if AUTHORIZATION_RECORD not in ids:
        print("G2-02 development batch: not yet authorized (nothing to check)")
        return
    authorization = batch.authorization_record(ROOT)
    assert authorization["adaptive_revision_authorized"] is False
    assert datetime_aware(authorization["timestamp_utc"])
    stored = json.loads((ROOT / batch.AUTHORIZATION_PATH).read_text(encoding="utf-8"))
    assert stored == authorization, "AUTHORIZATION.json must mirror the ledger record"
    assert authorization["code_sha256"] == batch.code_identity(ROOT), (
        "code bound by the G2-02 authorization changed"
    )
    if "G2-02-CHECKPOINT-001" not in ids:
        print("G2-02 development batch: authorized, execution pending")
        return
    auth_index = ids.index(AUTHORIZATION_RECORD)
    executed = [
        i for i, r in enumerate(ledger) if r["record_type"] == "DEVELOPMENT_SYSTEM_EXECUTED"
    ]
    assert len(executed) == 6 and min(executed) > auth_index
    assert ids.index("G2-02-CHECKPOINT-001") > max(executed)
    manifest = json.loads((ROOT / batch.BATCH_MANIFEST_PATH).read_text(encoding="utf-8"))
    for path, digest in manifest["artifacts_sha256"].items():
        assert text_sha256(ROOT / path) == digest, f"{path} differs from the batch manifest"
    results = json.loads((ROOT / batch.RESULTS_PATH).read_text(encoding="utf-8"))
    assert results["determinism"]["fingerprint_identical"] is True
    assert results["claims"]["protected_2025_outcomes_read"] is False
    assert results["claims"]["adaptive_revision_executed"] is False
    for audit in results["reconciliation"].values():
        assert audit["no_observation_at_or_after_2025"] is True
        assert audit["no_entry_before_economic_window"] is True
        assert audit["one_position_at_a_time"] is True
    if (ROOT / CACHE_DIR / "run_manifest.json").is_file():
        built = batch.build(ROOT)
        assert batch.dumps(built["results"]) == (ROOT / batch.RESULTS_PATH).read_text(
            encoding="utf-8"
        ), "RESULTS.json is not reproduced from the run cache"
        assert batch.dumps(built["autopsy"]) == (ROOT / batch.AUTOPSY_PATH).read_text(
            encoding="utf-8"
        ), "AUTOPSY.json is not reproduced from the run cache"
        print("G2-02 development batch: PASS (artifacts reproduced from the run cache)")
    else:
        print("G2-02 development batch: PASS (artifact/ledger binding; run cache absent)")


def datetime_aware(text: str) -> bool:
    from datetime import datetime

    return datetime.fromisoformat(text).tzinfo is not None


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--authorize", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--workers", type=int, default=min(6, os.cpu_count() or 1))
    options = parser.parse_args()
    if options.check:
        check()
        return
    if options.authorize:
        payload = batch.authorize(ROOT)
        print(f"appended {payload['record_id']} at {payload['timestamp_utc']}")
        return
    echo = stderr_echo(options.progress)
    log_lines: list[str] = []
    if options.build:
        with Job("g2-02-build", BUILD_PHASES, ROOT, echo=echo) as job:
            _, written = build_and_write(job, None)
        print(f"rebuilt {len(written)} artifacts")
        return
    phases = ["verify authorization", "simulate batch", *BUILD_PHASES, "append ledger records"]
    with Job("g2-02-development-batch", phases, ROOT, echo=echo) as job:
        job.phase("verify authorization")
        authorization = batch.authorization_record(ROOT)
        log_lines.append(
            f"authorization {authorization['record_id']} {authorization['timestamp_utc']}"
        )
        started = time.monotonic()
        manifest = batch.execute(ROOT, job, options.workers)
        log_lines.append(f"batch simulated in {time.monotonic() - started:.1f}s")
        for key, run in manifest["runs"].items():
            log_lines.append(
                f"run {key}: run_id={run['run_id']} fingerprint={run['fingerprint']} "
                f"elapsed={run['elapsed_seconds']}s records={json.dumps(run['record_counts'])}"
            )
        log_lines.append(f"determinism {json.dumps(manifest['determinism'], sort_keys=True)}")
        built, written = build_and_write(job, log_lines)
        job.phase("append ledger records")
        batch.executed_records(ROOT, built["results"], written)
    print(f"G2-02 batch complete: {len(written)} artifacts; status {batch.STATUS}")


if __name__ == "__main__":
    main()
