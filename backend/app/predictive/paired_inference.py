"""Paired, fold-stratified moving-block bootstrap for a candidate-minus-baseline delta.

The primary effect of `PREDICTIVE-INTERNAL-STRUCTURE-V1` is

    candidate actionable directional win rate - matched ALWAYS_UP win rate

on the exact timestamps where the candidate is actionable. Candidate and baseline are
scored on the same records, so the delta is paired record by record.

Blocks are contiguous on the **original hourly evaluation timeline**, not on the compressed
sequence of scored records: an abstention or a canonical gap keeps its hour slot and simply
contributes no record, so abstentions are never pulled into adjacency by resampling. Blocks
are drawn independently inside each outer fold and never span a fold boundary.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .labels import HOUR_SECONDS

PAIRED_METHOD = "PAIRED_FOLD_STRATIFIED_MOVING_BLOCK_BOOTSTRAP"
PAIRED_BLOCK_LENGTH_HOURS = 48
PAIRED_REPLICATES = 10_000
PAIRED_SEED = 20260916
PAIRED_ALPHA = 0.025
# Fixed so the draw order, and therefore the interval, is reproducible bit for bit.
REPLICATE_CHUNK = 500


class PairedInferenceError(RuntimeError):
    """The paired resample was asked for something the frozen design does not allow."""


@dataclass(frozen=True)
class PairedRecord:
    """One candidate-actionable, non-NEUTRAL decision instant scored both ways."""

    open_time: int
    candidate_correct: bool
    baseline_correct: bool


@dataclass(frozen=True)
class PairedFold:
    """One outer fold's hourly evaluation timeline and the records sitting on it."""

    name: str
    first_open_time: int
    last_open_time: int
    records: tuple[PairedRecord, ...]

    @property
    def span_hours(self) -> int:
        return (self.last_open_time - self.first_open_time) // HOUR_SECONDS + 1


def build_paired_fold(
    name: str, eligible_open_times: Sequence[int], records: Sequence[PairedRecord]
) -> PairedFold:
    """Lay one fold's records on the hourly timeline spanned by its eligible instants."""
    if not eligible_open_times:
        raise PairedInferenceError(f"{name}: the fold has no eligible decision instant")
    first, last = min(eligible_open_times), max(eligible_open_times)
    for record in records:
        if not first <= record.open_time <= last:
            raise PairedInferenceError(f"{name}: a record sits outside the fold timeline")
        if (record.open_time - first) % HOUR_SECONDS:
            raise PairedInferenceError(f"{name}: a record is not on the hourly grid")
    ordered = tuple(sorted(records, key=lambda item: item.open_time))
    if len({item.open_time for item in ordered}) != len(ordered):
        raise PairedInferenceError(f"{name}: duplicate decision instants in one fold")
    return PairedFold(name=name, first_open_time=first, last_open_time=last, records=ordered)


def _slot_arrays(fold: PairedFold) -> tuple[Any, Any, Any]:
    """Hour-slot indicators: candidate hits, baseline hits, and record presence."""
    import numpy as np

    span = fold.span_hours
    candidate = np.zeros(span, dtype=np.float64)
    baseline = np.zeros(span, dtype=np.float64)
    present = np.zeros(span, dtype=np.float64)
    for record in fold.records:
        slot = (record.open_time - fold.first_open_time) // HOUR_SECONDS
        candidate[slot] = 1.0 if record.candidate_correct else 0.0
        baseline[slot] = 1.0 if record.baseline_correct else 0.0
        present[slot] = 1.0
    return candidate, baseline, present


def block_sums(values: Any, block_length: int) -> tuple[Any, Any, int, int]:
    """Sums of every full block and of the truncated final block, plus the draw geometry.

    Returns `(full, partial, draws, block)` where `full[s]` sums `values[s:s+block]`,
    `partial[s]` sums `values[s:s+remainder]`, `draws` is how many blocks a replicate
    concatenates, and `block` is the effective block length on this timeline.
    """
    import numpy as np

    total = int(values.shape[0])
    if block_length <= 0:
        raise PairedInferenceError("the block length must be strictly positive")
    block = min(block_length, total)
    draws = math.ceil(total / block)
    remainder = total - (draws - 1) * block
    prefix = np.concatenate(([0.0], np.cumsum(values)))
    starts = total - block + 1
    full = prefix[block : block + starts] - prefix[0:starts]
    partial = prefix[remainder : remainder + starts] - prefix[0:starts]
    return full, partial, draws, block


def observed_delta(folds: Sequence[PairedFold]) -> dict[str, Any]:
    """The pooled paired delta actually observed, with its two component win rates."""
    records = [record for fold in folds for record in fold.records]
    total = len(records)
    if total == 0:
        raise PairedInferenceError("the paired comparison has no actionable record")
    candidate = sum(1 for record in records if record.candidate_correct)
    baseline = sum(1 for record in records if record.baseline_correct)
    return {
        "paired_records": total,
        "candidate_win_rate": candidate / total,
        "matched_baseline_win_rate": baseline / total,
        "delta": (candidate - baseline) / total,
    }


def paired_delta_interval(
    folds: Sequence[PairedFold],
    block_length: int = PAIRED_BLOCK_LENGTH_HOURS,
    replicates: int = PAIRED_REPLICATES,
    seed: int = PAIRED_SEED,
    alpha: float = PAIRED_ALPHA,
    chunk: int = REPLICATE_CHUNK,
) -> dict[str, Any]:
    """Central `1 - alpha` percentile interval for the pooled paired delta.

    Each replicate resamples whole hourly blocks inside every fold independently, pools the
    resampled records across folds, and takes the candidate win rate minus the matched
    baseline win rate on that pooled set.
    """
    import numpy as np

    if not folds:
        raise PairedInferenceError("the paired comparison has no fold")
    if replicates <= 0 or chunk <= 0:
        raise PairedInferenceError("the replicate budget must be strictly positive")
    if not 0.0 < alpha < 1.0:
        raise PairedInferenceError("alpha must lie strictly inside (0, 1)")

    candidate_totals = np.zeros(replicates, dtype=np.float64)
    baseline_totals = np.zeros(replicates, dtype=np.float64)
    record_totals = np.zeros(replicates, dtype=np.float64)
    generator = np.random.default_rng(seed)
    geometry: list[dict[str, int]] = []

    for fold in folds:
        candidate, baseline, present = _slot_arrays(fold)
        full_c, partial_c, draws, block = block_sums(candidate, block_length)
        full_b, partial_b, _, _ = block_sums(baseline, block_length)
        full_m, partial_m, _, _ = block_sums(present, block_length)
        starts_available = int(full_c.shape[0])
        geometry.append(
            {
                "timeline_hours": fold.span_hours,
                "effective_block_hours": block,
                "blocks_per_replicate": draws,
                "block_start_positions": starts_available,
                "records": len(fold.records),
            }
        )
        done = 0
        while done < replicates:
            size = min(chunk, replicates - done)
            starts = generator.integers(0, starts_available, size=(size, draws))
            head, tail = starts[:, : draws - 1], starts[:, draws - 1]
            candidate_totals[done : done + size] += full_c[head].sum(axis=1) + partial_c[tail]
            baseline_totals[done : done + size] += full_b[head].sum(axis=1) + partial_b[tail]
            record_totals[done : done + size] += full_m[head].sum(axis=1) + partial_m[tail]
            done += size

    if not np.all(record_totals > 0):
        raise PairedInferenceError("a replicate resampled no actionable record at all")
    deltas = (candidate_totals - baseline_totals) / record_totals
    lower, upper = np.quantile(deltas, [alpha / 2, 1 - alpha / 2])
    summary = observed_delta(folds)
    summary.update(
        {
            "method": PAIRED_METHOD,
            "block_length_hours": block_length,
            "replicates": replicates,
            "seed": seed,
            "alpha": alpha,
            "interval_mass": 1.0 - alpha,
            "interval": [float(lower), float(upper)],
            "interval_lower_bound_above_zero": bool(lower > 0.0),
            "blocks_cross_fold_boundaries": False,
            "abstentions_compressed_into_adjacency": False,
            "fold_geometry": {
                fold.name: record for fold, record in zip(folds, geometry, strict=True)
            },
        }
    )
    return summary


__all__ = [
    "PAIRED_ALPHA",
    "PAIRED_BLOCK_LENGTH_HOURS",
    "PAIRED_METHOD",
    "PAIRED_REPLICATES",
    "PAIRED_SEED",
    "REPLICATE_CHUNK",
    "PairedFold",
    "PairedInferenceError",
    "PairedRecord",
    "block_sums",
    "build_paired_fold",
    "observed_delta",
    "paired_delta_interval",
]
