"""Generate or verify the deterministic P0 statistical-governance artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.research.statistical_governance import (
    build_aligned_provenance_audit,
    build_repository_ledger,
    json_bytes,
    reconstruct_statistical_evidence,
    render_ledger_markdown,
    render_provenance_markdown,
    render_statistics_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = {
    "ledger_json": ROOT / "reports/statistics/MATERIAL-HYPOTHESIS-LEDGER-V1.json",
    "ledger_md": ROOT / "reports/statistics/MATERIAL-HYPOTHESIS-LEDGER-V1.md",
    "provenance_json": ROOT / "reports/statistics/ALIGNED-CONSTANT-PROVENANCE-V1.json",
    "provenance_md": ROOT / "reports/statistics/ALIGNED-CONSTANT-PROVENANCE-V1.md",
    "statistics_json": ROOT / "reports/statistics/STATISTICAL-EVIDENCE-AUDIT-V1.json",
    "statistics_md": ROOT / "reports/statistics/STATISTICAL-EVIDENCE-AUDIT-V1.md",
}


def expected_outputs() -> dict[Path, bytes]:
    ledger = build_repository_ledger(ROOT)
    provenance = build_aligned_provenance_audit()
    statistics = reconstruct_statistical_evidence(ROOT)
    return {
        OUTPUTS["ledger_json"]: json_bytes(ledger),
        OUTPUTS["ledger_md"]: render_ledger_markdown(ledger).encode("utf-8"),
        OUTPUTS["provenance_json"]: json_bytes(provenance),
        OUTPUTS["provenance_md"]: render_provenance_markdown(provenance).encode("utf-8"),
        OUTPUTS["statistics_json"]: json_bytes(statistics),
        OUTPUTS["statistics_md"]: render_statistics_markdown(statistics).encode("utf-8"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if committed outputs drift")
    args = parser.parse_args()
    expected = expected_outputs()
    if args.check:
        drift = [path for path, content in expected.items() if not path.is_file() or path.read_bytes() != content]
        if drift:
            raise SystemExit("statistical audit drift: " + ", ".join(str(path) for path in drift))
        print("statistical audit: PASS")
        return 0
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print("statistical audit artifacts generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
