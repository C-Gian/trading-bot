# ADR-0034 — Canonical text provenance for scientific text dependencies

Status: RESEARCH_DIRECTOR_ACCEPTED (2026-09-23)

## Context

`EXP-PRED-V2-005` pinned its frozen protocol by the raw SHA-256 of the Owner's Windows
working-tree bytes (`6fb5da71…e012`, CRLF). Git stores the same text; an LF checkout of it
hashes to `fdb355fc…b7cd`. With `core.autocrlf` and no `.gitattributes`, any raw-byte pin of a
text file is environment dependent, so a fresh checkout on another platform could fail
validation although nothing scientific changed.

## Decision

1. Rule `CANONICAL_UTF8_LF_TEXT_V1`, implemented once in
   `backend/app/research/text_provenance.py`: decode strict UTF-8, replace CRLF then lone CR
   with LF, change nothing else, SHA-256 the UTF-8 bytes.
2. Newly created scientific text dependencies (protocols, designs, documents, generated
   text/JSON artifacts they cite) record `canonical_text_sha256` under this rule instead of
   checkout bytes.
3. Historical artifacts are never rewritten. A historical raw-byte pin is honoured through an
   immutable provenance record that preserves the raw digest, lists every place it is
   recorded, and declares the canonical digest it is equivalent to. EXP-PRED-V2-005 has one:
   `reports/validation/PREDICTIVE-V2-PUBLIC-TAKER-FLOW-HORIZON-FOUNDATION-V1-TEXT-PROVENANCE.json`.
4. The rule is not global. Binary files, market data, raw archives and every undeclared
   dependency keep exact raw-byte identity. Any non-newline change, and any numerical replay
   difference, still fails validation.

## Consequences

- EXP-PRED-V2-005 validates on LF and CRLF checkouts without altering its result.
- The Owner script `scripts/run_public_taker_flow_foundation.py --check` still compares raw
  bytes (it is a pinned implementation file); the governed cross-platform replay is
  `backend/app/predictive/taker_flow_validation.py` in data mode.
- Existing ad-hoc CRLF-only normalizers in hash-pinned modules are left unchanged; new code
  uses the central module.
