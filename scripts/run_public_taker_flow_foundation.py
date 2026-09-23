"""Run `PREDICTIVE_V2_PUBLIC_TAKER_FLOW_HORIZON_FOUNDATION_V1` exactly once, or replay it.

The run re-verifies every pinned official object against the acquisition manifest, builds the
three frozen features and the 24h/4h/1h targets, fits the one fixed model per horizon and
annual fold, scores it against the matched training-base-rate control and writes:

- `research/experiments/EXP-PRED-V2-005-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION/result.json`;
- `reports/research/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1.md`.

Results are never rewritten: if either output already exists the run refuses. ``--check``
recomputes everything and asserts that the committed outputs match byte for byte.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.predictive.taker_flow_foundation import (
    HORIZONS_HOURS,
    REPORT_MARKDOWN_PATH,
    RESULT_PATH,
    RESULT_PATHS,
    FoundationError,
    markdown_bytes,
    result_bytes,
    run_foundation,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="replay and compare with the written outputs"
    )
    options = parser.parse_args()

    existing = [path for path in RESULT_PATHS if (ROOT / path).exists()]
    if not options.check and existing:
        raise FoundationError(f"results already exist and are never rewritten: {existing}")
    if options.check and len(existing) != len(RESULT_PATHS):
        raise FoundationError("--check needs both written outputs")

    result = run_foundation(ROOT)
    outputs = {RESULT_PATH: result_bytes(result), REPORT_MARKDOWN_PATH: markdown_bytes(result)}

    if options.check:
        mismatched = [
            path for path, payload in outputs.items() if (ROOT / path).read_bytes() != payload
        ]
        if mismatched:
            raise FoundationError(f"replay does not reproduce: {mismatched}")
        print(f"public taker-flow foundation replay: PASS selection={result['selection']}")
        return

    for path, payload in outputs.items():
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    print(f"public taker-flow foundation written: selection={result['selection']}")
    for horizon in HORIZONS_HOURS:
        item = result["horizons"][str(horizon)]
        print(
            f"  {horizon}h: scored={item['scored_rows']} "
            f"coverage={item['pooled_feature_coverage']:.4f} "
            f"brier_improvement={item['pooled_brier_improvement']:.7f} "
            f"interval={item['bootstrap']['interval']} "
            f"classification={item['qualification']['classification']}"
        )
    for path in outputs:
        print(f"  wrote {path}")


if __name__ == "__main__":
    main()
