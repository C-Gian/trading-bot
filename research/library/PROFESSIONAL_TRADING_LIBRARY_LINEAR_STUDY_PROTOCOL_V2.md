# Professional Trading Library — Linear Study Protocol V2

Date: 2026-09-26
Status: ACTIVE
Authority: Owner direction / ADR-0051

## Purpose

Study the entire private Google Drive corpus **linearly and source-by-source**, preserving each
document's internal logic before any cross-source synthesis.

The study order is the order of the canonical source registry:

`LIB-001 -> LIB-020`.

Do not reorganize primary reading by topic.

## Per-source rule

Each source is treated independently.

For every source:

1. identify/verify bibliographic metadata;
2. read the complete accessible source;
3. inspect figures/tables/appendices when materially relevant;
4. distinguish:
   - SOURCE CLAIM
   - EVIDENCE/METHOD
   - LIMITATIONS
   - RESEARCH DIRECTOR INTERPRETATION
   - POTENTIAL PROJECT RELEVANCE
   - OPEN QUESTIONS
5. record contradictions **without resolving them from other sources yet**;
6. create one persistent source dossier:

   `research/library/source_notes/LIB-XXX-<slug>.md`

7. only after the dossier exists and the complete accessible source has been reviewed may the
   source registry status become `REVIEWED`.

For datasets, create a dataset dossier covering schema, provenance, definitions, time coverage,
reconstruction/update policy, and relationship to the associated paper. Dataset inspection does not
substitute for studying the associated paper.

## No premature synthesis

Before all accessible sources are reviewed:

- do not freeze signal weights;
- do not design System G2;
- do not decide a final signal-family architecture;
- do not treat emerging agreement as final consensus;
- do not start BTC backtests or parameter calibration.

Local observations may be recorded in the per-source dossier, but the **cross-source brainstorming
and system synthesis happens only after corpus completion**.

## Astra role

Astra does not need to duplicate the entire primary reading pass by default.

After the Research Director completes the corpus:

1. assemble the 20 per-source dossiers plus source registry and contradiction register;
2. produce a cross-source synthesis draft;
3. give Astra the dossiers and synthesis for independent review;
4. Astra may open any original source selectively when:
   - a claim is disputed;
   - provenance is unclear;
   - a source is central to an architectural decision;
   - the dossier seems incomplete or overinterpreted.

If Astra concludes that independent full-source rereading is required for a critical subset, perform
that reread before architecture freeze.

## Existing out-of-order pilot work

Before this protocol was adopted, LIB-006, LIB-007, LIB-008, LIB-009 and LIB-015 were fully reviewed
as a thematic pilot.

Their `REVIEWED` status remains valid, but they still require individual per-source dossiers in the
canonical format before final synthesis.

The linear primary pass now starts at LIB-001 and proceeds through LIB-020. Previously reviewed
sources are revisited only as needed to create/complete their individual dossiers; they are not
reinterpreted through later sources until the final synthesis stage.

## Scanned PDFs

For image/scanned PDFs such as LIB-001:

- use rendered-page inspection;
- use text extraction where available;
- OCR only if necessary and only as a support tool;
- figures/layout remain authoritative;
- do not mark REVIEWED from filename/front matter alone.

## Completion condition

Corpus study is complete only when:

- every accessible LIB-001..LIB-020 source has a dossier;
- every narrative source is REVIEWED or explicitly UNREADABLE with reason;
- every dataset has a completed dataset dossier;
- unresolved contradictions are registered;
- missing-knowledge gaps are updated.

Only then begin:

`PROFESSIONAL_TRADING_CORPUS_FINAL_SYNTHESIS_V1`

followed by Astra review.
