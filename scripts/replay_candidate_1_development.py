"""Deterministic replay of the single recorded Candidate #1 Development execution.

Recomputes the frozen evaluation exactly as `scripts/run_candidate_1_development.py --execute`
did, with the same code path, and compares it byte-for-byte with the preserved result. It writes
nothing and is not a new experiment.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.research import candidate_1_development as dev
from run_candidate_1_development import _finite, _json


def main() -> None:
    stored = (ROOT / dev.RESULT_PATH).read_text(encoding="utf-8").replace("\r\n", "\n")
    identity = dev.identity_checks(ROOT)
    replay = subprocess.run(
        [sys.executable, "scripts/audit_candidate_1_frozen_admission.py", "--check"],
        cwd=ROOT,
        check=False,
    )
    episodes, _ = dev.load_admission(ROOT)
    result = dev.evaluate(
        episodes,
        dev.canonical_spot_prices(ROOT),
        {**identity, "ADMISSION_REPLAY": replay.returncode == 0},
    )
    if _json(_finite(result)) != stored:
        raise SystemExit("candidate #1 Development result does not replay")
    print("candidate #1 Development replay: PASS")


if __name__ == "__main__":
    main()
