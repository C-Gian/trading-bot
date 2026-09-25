# Executor policy

Version 2 — effective 2026-09-25
([ADR-0036](../decisions/ADR-0036-OWNER-PRACTICAL-ECONOMIC-OBJECTIVE-AND-CONSTITUTION-V3.md)).

- **Owner** — mission, evaluation principles, product/risk objective and any real-capital gate.
- **Astra** — strategic scientific authority for material research-allocation decisions; the
  escalation list is in `docs/canonical/RESEARCH_STAGE_POLICY_V1.md` §5.
- **ChatGPT Research Director** — routine scientific design, architecture, tasking,
  implementation review, experiment adjudication and ordinary decisions inside Astra's
  directive.
- **Claude Code** — the sole coding / repository implementation executor.
- **Codex** — not part of the normal implementation workflow.

These roles are task-allocation policy, never runtime dependencies of the product.
Scientific truth lives in versioned repository records and deterministic artifacts, not agent
conversations. No agent can authorize real capital.

---

## Superseded Version 1, preserved verbatim

ChatGPT / GPT-5.6 Sol is the Research Director and scientific/product authority
within Owner-controlled governance. Codex is the primary high-throughput
engineering and research executor. Claude Code is the overflow executor when
Codex usage is unavailable. Tasks and repository records must remain portable
between Codex and Claude Code.

Astra Ultra is allocated explicitly to selected high-leverage reasoning
checkpoints; it is not the default for ordinary implementation. These roles are
task-allocation policy, never runtime dependencies of the product.

Scientific truth lives in versioned repository records and deterministic
artifacts, not agent conversations. No agent can authorize real capital.
