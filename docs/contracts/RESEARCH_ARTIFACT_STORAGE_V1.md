# RESEARCH_ARTIFACT_STORAGE_V1

Status: accepted prospectively for WP-008 and later work packages.

This contract changes how new research artifacts are stored. It does not migrate,
delete, rewrite, or reinterpret any historical experiment evidence.

## Compact tracked records

Git stores preregistrations, executable configs and protocols, allocation and
search-memory decisions, result and fold summaries, reports, artifact manifests,
machine-readable state, checkpoints, and task archives as compact text.

## Executed trial and trade rows

High-volume WP-008-and-later trial/trade rows are stored as ZSTD-compressed Parquet,
not pretty-printed JSON. Each artifact has an explicit fixed Arrow schema, is sorted
by its declared sort key before writing, and is written with deterministic writer
settings. Its result summary records:

- repository-relative path;
- row count and schema version;
- sort key;
- file SHA-256 over exact Parquet bytes;
- logical SHA-256 over canonical schema plus sorted row content;
- writer settings and PyArrow version.

The logical hash is the encoding-independent scientific identity. The file hash
detects byte changes to the tracked artifact. Nulls and floating-point values are
encoded canonically; non-finite floating-point values are forbidden.

## Training matrices and labels

Row-by-row training matrices and labels are regeneration products and are not
committed. For each fold, compact deterministic manifests record:

- validation fold and exact feature order;
- fit-row count and all exclusion counts;
- minimum and maximum training signal timestamps;
- maximum training label-outcome timestamp;
- validation bounds and purge boundary;
- feature-matrix and label-vector logical hashes;
- feature/label implementation and dependency hashes;
- exact regeneration command.

These manifests bind model inputs without placing large derived matrices in Git.

## Validation

Checkpoint validation must reproduce logical hashes, verify Parquet file hashes and
schema/sort order, reject any WP-008 row-level JSON trial artifact, reject committed
training matrices or labels, and prove every historical experiment artifact remains
byte-identical to the accepted WP-007 starting HEAD.
