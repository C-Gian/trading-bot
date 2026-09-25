"""The single System G1 Development V1 historical batch command (guarded; no preview mode).

It refuses unless `state/current_state.json -> system_g1_development` explicitly carries a
Research Director execution authorization whose decision record exists. Phase B additionally
requires the Phase-A selection artifact and runs only the automatically selected configuration.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.g1.batch import (
    RUN_DIR,
    ExecutionNotAuthorized,
    authorize_real_sources,
    run_phase_a,
    run_phase_b,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("A", "B"), required=True)
    options = parser.parse_args()
    try:
        source = authorize_real_sources(ROOT)
    except ExecutionNotAuthorized as exc:
        raise SystemExit(f"REFUSED: {exc}") from exc
    runner = run_phase_a if options.phase == "A" else run_phase_b
    artifact = runner(source, ROOT / RUN_DIR, ROOT)
    print(
        f"phase {options.phase}: {artifact.get('disposition') or artifact['selected_configuration']}"
    )


if __name__ == "__main__":
    main()
