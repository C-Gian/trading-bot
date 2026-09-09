"""Independent WP-005 provenance, feature, result, and replay reconciliation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import zipfile
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .continuation_lab import ContinuationLab, ResearchInputs
from .evaluation_protocol import HOUR_US, load_protocol, utc_us

MINUTE_US = 60_000_000
CUTOFF_US = utc_us("2024-12-31T23:59:00Z")
ARCHIVE_MONTHS = ("2017-12", "2018-02")
VARIANT_EXPERIMENTS = {
    "REGIME_ONLY": "EXP-ALG-007-REGIME",
    "PARTICIPATION_ONLY": "EXP-ALG-008-PARTICIPATION",
    "ALIGNED": "EXP-ALG-009-ALIGNED",
}
PROFILES = ("DEFAULT", "ZERO", "DOUBLE", "DELAY_1H")
RAW_MAPPING = {
    "open_time": 0,
    "open": 1,
    "high": 2,
    "low": 3,
    "close": 4,
    "volume": 5,
    "close_time": 6,
    "quote_volume": 7,
    "trades": 8,
    "taker_base": 9,
    "taker_quote": 10,
}


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def instant_us(value: int) -> str:
    return (datetime(1970, 1, 1, tzinfo=UTC) + timedelta(microseconds=value)).isoformat().replace(
        "+00:00", "Z"
    )


def _unsafe(times: np.ndarray, width: int) -> set[int]:
    bad = times[times % MINUTE_US != 0]
    starts = bad // width * width
    ends = (bad + MINUTE_US - 1) // width * width
    return set(map(int, np.concatenate((starts, ends))))


def _mask_hash(times: np.ndarray) -> str:
    one = np.asarray(sorted(_unsafe(times, HOUR_US)), dtype="<i8")
    four = np.asarray(sorted(_unsafe(times, 4 * HOUR_US)), dtype="<i8")
    return hashlib.sha256(one.tobytes() + four.tobytes()).hexdigest()


def source_provenance(root: Path) -> dict[str, Any]:
    """Verify official local ZIP rows against canonical rows without normalizing timestamps."""
    manifest_path = root / "data/manifests/BTCUSDT-SPOT-1M-DEV-v1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = [
        item
        for item in manifest["source"]["raw_objects"]
        if any(month in item["path"] for month in ARCHIVE_MONTHS)
    ]
    if len(selected) != 2:
        raise ValueError("required accepted archives are not uniquely identified")

    raw_rows: list[list[str]] = []
    archive_records = []
    for item in selected:
        path = root / item["path"]
        digest = file_hash(path)
        if digest != item["sha256"]:
            raise ValueError(f"raw archive hash mismatch: {item['path']}")
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != 1 or not names[0].endswith(".csv"):
                raise ValueError("unexpected official archive layout")
            with archive.open(names[0]) as source:
                decoded = (line.decode("utf-8") for line in source)
                month_rows = list(csv.reader(decoded))
        if any(len(row) < 11 for row in month_rows):
            raise ValueError("raw Binance column layout is incomplete")
        raw_rows.extend(month_rows)
        archive_records.append(
            {
                "path": item["path"],
                "url": item["url"],
                "accepted_sha256": item["sha256"],
                "observed_sha256": digest,
                "member": names[0],
                "rows": len(month_rows),
                "status": "MATCH",
            }
        )

    raw_ms = np.asarray([int(row[0]) for row in raw_rows], dtype=np.int64)
    if np.any(np.diff(raw_ms) <= 0) or np.any(raw_ms * 1000 > CUTOFF_US):
        raise ValueError("raw archive order/cutoff violation")
    bad_indices = np.flatnonzero(raw_ms % 60_000 != 0)
    groups = np.split(bad_indices, np.flatnonzero(np.diff(bad_indices) != 1) + 1)
    anomaly_rows = [raw_rows[int(index)] for index in bad_indices]
    anomaly_us = raw_ms[bad_indices] * 1000

    canonical_path = root / manifest["files"]["canonical"]["path"]
    if file_hash(canonical_path) != manifest["files"]["canonical"]["sha256"]:
        raise ValueError("canonical byte hash mismatch")
    columns = list(RAW_MAPPING)
    table = pq.read_table(canonical_path, columns=columns)
    canonical_us = table["open_time"].cast(pa.int64()).to_numpy()
    if np.any(np.diff(canonical_us) <= 0) or int(canonical_us[-1]) > CUTOFF_US:
        raise ValueError("canonical order/cutoff violation")
    positions = np.searchsorted(canonical_us, anomaly_us)
    timestamp_mismatches = int(
        np.count_nonzero((positions >= len(canonical_us)) | (canonical_us[positions] != anomaly_us))
    )
    if timestamp_mismatches:
        raise ValueError("raw anomaly timestamp is missing from canonical data")

    payload_mismatches = Counter()
    for output_index, (row, position) in enumerate(zip(anomaly_rows, positions, strict=True)):
        del output_index
        for name, raw_index in RAW_MAPPING.items():
            if name == "open_time":
                expected: int | float = int(row[raw_index]) * 1000
                actual = int(canonical_us[position])
            elif name in {"close_time", "trades"}:
                expected = int(row[raw_index])
                actual = int(table[name][position].as_py())
            else:
                expected = float(row[raw_index])
                actual = float(table[name][position].as_py())
            if actual != expected:
                payload_mismatches[name] += 1
    if payload_mismatches:
        raise ValueError(f"raw/canonical payload mismatch: {dict(payload_mismatches)}")

    intervals = []
    for group in groups:
        values = raw_ms[group]
        first_index, last_index = int(group[0]), int(group[-1])
        spacing = Counter(map(int, np.diff(values)))
        timestamp_text = [raw_rows[int(index)][0] for index in group]
        intervals.append(
            {
                "start": instant_us(int(values[0]) * 1000),
                "end": instant_us(int(values[-1]) * 1000),
                "rows": len(values),
                "raw_first_column_sha256": hashlib.sha256(
                    ("\n".join(timestamp_text) + "\n").encode("ascii")
                ).hexdigest(),
                "timestamp_modulo_minute_ms": dict(
                    sorted(Counter(map(int, values % 60_000)).items())
                ),
                "internal_spacing_ms": dict(sorted(spacing.items())),
                "transition_in": {
                    "previous_raw_ms": int(raw_ms[first_index - 1]),
                    "first_anomaly_raw_ms": int(raw_ms[first_index]),
                    "delta_ms": int(raw_ms[first_index] - raw_ms[first_index - 1]),
                    "previous": instant_us(int(raw_ms[first_index - 1]) * 1000),
                    "first_anomaly": instant_us(int(raw_ms[first_index]) * 1000),
                },
                "transition_out": {
                    "last_anomaly_raw_ms": int(raw_ms[last_index]),
                    "next_raw_ms": int(raw_ms[last_index + 1]),
                    "delta_ms": int(raw_ms[last_index + 1] - raw_ms[last_index]),
                    "last_anomaly": instant_us(int(raw_ms[last_index]) * 1000),
                    "next": instant_us(int(raw_ms[last_index + 1]) * 1000),
                },
            }
        )

    off_grid = np.flatnonzero(canonical_us % MINUTE_US != 0)
    one = _unsafe(canonical_us, HOUR_US)
    four = _unsafe(canonical_us, 4 * HOUR_US)
    expected_grid = json.loads(
        (root / "reports/validation/WP-004-SOURCE-GRID.json").read_text(encoding="utf-8")
    )
    observed_timestamp_hash = hashlib.sha256(
        canonical_us[off_grid].astype("<i8").tobytes()
    ).hexdigest()
    observed_mask_hash = _mask_hash(canonical_us)
    if (
        len(off_grid) != expected_grid["off_grid_rows"]
        or len(one) != expected_grid["quarantined_1h_buckets"]
        or len(four) != expected_grid["quarantined_4h_buckets"]
        or observed_timestamp_hash != expected_grid["off_grid_timestamps_sha256"]
        or observed_mask_hash != expected_grid["quarantine_masks_sha256"]
    ):
        raise ValueError("WP-004 quarantine identity did not reproduce independently")

    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    required_one: set[int] = set()
    required_four: set[int] = set()
    for fold in protocol["folds"]:
        for signal in range(
            utc_us(fold["validation_start"]),
            utc_us(fold["last_signal_inclusive"]) + 1,
            HOUR_US,
        ):
            for decision in (signal, signal - HOUR_US):
                last_one = decision - HOUR_US
                required_one.update(last_one - index * HOUR_US for index in range(25))
                last_four = decision // (4 * HOUR_US) * (4 * HOUR_US) - 4 * HOUR_US
                required_four.update(last_four - index * 4 * HOUR_US for index in range(43))
    intersections = {
        "1h": len(one & required_one),
        "4h": len(four & required_four),
    }
    if intersections != {"1h": 0, "4h": 0}:
        raise ValueError("source anomaly intersects validation feature requirements")

    return {
        "schema_version": 1,
        "audit_id": "WP-005-SOURCE-PROVENANCE",
        "status": "PASS",
        "classification": "SOURCE_ARCHIVE_OFF_GRID_CONFIRMED",
        "scope": "accepted official Binance Spot monthly archives 2017-12 and 2018-02 only",
        "archives": archive_records,
        "parser_column_mapping": RAW_MAPPING,
        "parser_mapping_status": "PASS",
        "timestamp_unit_conversion": "raw open_time integer milliseconds * 1000 -> canonical UTC microseconds",
        "unit_conversion_status": "PASS",
        "raw_to_canonical_timestamp_mismatches": timestamp_mismatches,
        "raw_to_canonical_payload_mismatches": dict(payload_mismatches),
        "ohlcv_payload_status": "EXACT_MATCH_ALL_ANOMALY_ROWS",
        "off_grid_rows": len(off_grid),
        "raw_anomaly_rows": len(bad_indices),
        "off_grid_rows_strictly_ordered": True,
        "intervals": intervals,
        "canonical_off_grid_timestamps_sha256": observed_timestamp_hash,
        "quarantine": {
            "policy": "QUARANTINE_SOURCE_OFF_GRID_INTERVALS_V1",
            "quarantined_1h_buckets": len(one),
            "quarantined_4h_buckets": len(four),
            "quarantine_masks_sha256": observed_mask_hash,
            "wp004_exact_reproduction": True,
            "repairs_or_fills": 0,
        },
        "validation_required_bucket_intersections": intersections,
        "validation_window_or_warmup_intersection": False,
        "maximum_raw_timestamp_read": instant_us(int(raw_ms[-1]) * 1000),
        "maximum_canonical_timestamp_read": instant_us(int(canonical_us[-1])),
        "development_cutoff": "2024-12-31T23:59:00Z",
        "post_cutoff_bytes_read": False,
        "manifest_sha256": file_hash(manifest_path),
        "dataset_content_hash": manifest["content_hash"]["value"],
    }


class OracleBars:
    """Independent array oracle; deliberately has no dependency on FeatureSource."""

    def __init__(self, root: Path):
        minute = pq.read_table(root / "data/canonical/BTCUSDT-1m.parquet", columns=["open_time"])
        self.minute_times = minute["open_time"].cast(pa.int64()).to_numpy()
        self.unsafe_one = _unsafe(self.minute_times, HOUR_US)
        self.unsafe_four = _unsafe(self.minute_times, 4 * HOUR_US)
        self.series: dict[int, dict[str, np.ndarray]] = {}
        for width, name in ((HOUR_US, "1h"), (4 * HOUR_US, "4h")):
            table = pq.read_table(
                root / f"data/derived/BTCUSDT-{name}.parquet",
                columns=["open_time", "high", "close", "volume", "complete"],
            )
            self.series[width] = {
                "time": table["open_time"].cast(pa.int64()).to_numpy(),
                "high": table["high"].to_numpy(),
                "close": table["close"].to_numpy(),
                "volume": table["volume"].to_numpy(),
                "complete": table["complete"].to_numpy(),
            }

    def window(self, signal: int, width: int, count: int) -> dict[str, np.ndarray] | None:
        data = self.series[width]
        expected_last = signal // width * width - width
        end = int(np.searchsorted(data["time"], expected_last, side="right"))
        start = end - count
        if start < 0:
            return None
        expected = expected_last - np.arange(count - 1, -1, -1, dtype=np.int64) * width
        actual = data["time"][start:end]
        unsafe = self.unsafe_one if width == HOUR_US else self.unsafe_four
        if (
            len(actual) != count
            or not np.array_equal(actual, expected)
            or not bool(np.all(data["complete"][start:end]))
            or any(int(value) in unsafe for value in actual)
        ):
            return None
        return {key: value[start:end] for key, value in data.items() if key != "time"} | {
            "time": actual
        }

    def features(self, signal: int) -> dict[str, Any] | None:
        hours = self.window(signal, HOUR_US, 25)
        context = self.window(signal, 4 * HOUR_US, 43)
        if hours is None or context is None:
            return None
        changes = np.diff(context["close"].astype(float))
        up = math.fsum(max(float(value), 0.0) for value in changes)
        down = math.fsum(max(-float(value), 0.0) for value in changes)
        previous_volume_mean = math.fsum(map(float, hours["volume"][:-1])) / 24
        return {
            "asof_us": signal,
            "reference": float(hours["close"][-1]),
            "breakout": float(hours["close"][-1]) > max(map(float, hours["high"][:-1])),
            "persistent_up": up + down > 0 and up >= 2 * down,
            "participation": previous_volume_mean > 0
            and float(hours["volume"][-1]) >= 2 * previous_volume_mean,
            "signed_efficiency": (up - down) / (up + down) if up + down else None,
            "relative_volume": float(hours["volume"][-1]) / previous_volume_mean
            if previous_volume_mean
            else None,
        }


def _emit(feature: dict[str, Any], variant: str) -> bool:
    return bool(
        feature["breakout"]
        and (variant == "PARTICIPATION_ONLY" or feature["persistent_up"])
        and (variant == "REGIME_ONLY" or feature["participation"])
    )


def _rounded(value: Decimal | None) -> float | None:
    return round(float(value), 10) if value is not None else None


def independent_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    records = [trade["record"] for trade in trades]
    valid = [record for record in records if record["data_quality_status"] == "VALID"]
    net = [Decimal(record["net_r"]) for record in valid]
    gross = [Decimal(record["gross_r"]) for record in valid]
    wins = [value for value in net if value > 0]
    losses = [value for value in net if value < 0]
    cumulative = sum(net, Decimal(0))
    equity = peak = drawdown = Decimal(0)
    for value in net:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    unresolved = sum(record["data_quality_status"] == "UNRESOLVED" for record in records)
    invalid = sum(record["data_quality_status"] == "INVALID" for record in records)
    return {
        "attempted_setups": len(records),
        "trade_count": len(valid),
        "invalid_attempts": invalid,
        "unresolved_trades": unresolved,
        "net_expectancy_r": _rounded(cumulative / len(net)) if net else None,
        "cumulative_net_r": _rounded(cumulative) if net else None,
        "profit_factor": _rounded(sum(wins, Decimal(0)) / -sum(losses, Decimal(0)))
        if losses
        else None,
        "maximum_drawdown_r": _rounded(drawdown) if net else None,
        "cost_drag_r": _rounded(sum(gross, Decimal(0)) - cumulative) if net else None,
    }


def feature_and_result_reconciliation(root: Path) -> dict[str, Any]:
    oracle = OracleBars(root)
    production = ResearchInputs.load(root)
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    trials = {
        variant: json.loads(
            (root / f"research/experiments/{experiment}/trials.json").read_text(encoding="utf-8")
        )
        for variant, experiment in VARIANT_EXPERIMENTS.items()
    }
    candidates: dict[str, dict[str, list[int]]] = {
        variant: {fold["fold_id"]: [] for fold in protocol["folds"]}
        for variant in VARIANT_EXPERIMENTS
    }
    eligible_counts = Counter()
    production_mismatches = 0
    feature_value_mismatches = 0
    for fold in protocol["folds"]:
        fold_id = fold["fold_id"]
        for signal in range(
            utc_us(fold["validation_start"]),
            utc_us(fold["last_signal_inclusive"]) + 1,
            HOUR_US,
        ):
            current = oracle.features(signal)
            previous = oracle.features(signal - HOUR_US)
            if current is None or previous is None:
                eligible_counts[(fold_id, "ineligible")] += 1
                continue
            eligible_counts[(fold_id, "eligible")] += 1
            for variant in VARIANT_EXPERIMENTS:
                expected = _emit(current, variant)
                observed, feature, reference = production.features.decision(signal, variant, 0)
                if observed != expected:
                    production_mismatches += 1
                if reference != current["reference"]:
                    feature_value_mismatches += 1
                for name in (
                    "asof_us",
                    "reference",
                    "breakout",
                    "persistent_up",
                    "participation",
                    "signed_efficiency",
                    "relative_volume",
                ):
                    actual = getattr(feature, name)
                    wanted = current[name]
                    if actual != wanted:
                        feature_value_mismatches += 1
                if expected:
                    candidates[variant][fold_id].append(signal)
    if production_mismatches or feature_value_mismatches:
        raise ValueError("independent feature oracle disagrees with production behavior")

    candidate_checks = {}
    executed_checks = {}
    metric_checks = []
    for variant, variant_trials in trials.items():
        default = next(item for item in variant_trials if item["profile"] == "DEFAULT")
        expected_counts = {
            fold: len(values) for fold, values in candidates[variant].items()
        }
        stored_counts = {
            item["fold_id"]: item["conditions_emitted"] for item in default["clock_diagnostics"]
        }
        if expected_counts != stored_counts:
            raise ValueError(f"candidate count mismatch for {variant}")
        candidate_checks[variant] = {
            "per_fold": expected_counts,
            "all_candidate_timestamps_sha256": canonical_hash(candidates[variant]),
            "status": "EXACT_MATCH",
        }
        candidate_set = {value for fold in candidates[variant].values() for value in fold}
        executed = [trade["signal_us"] for trade in default["trades"]]
        if any(value not in candidate_set for value in executed):
            raise ValueError(f"executed non-candidate in {variant}")
        for trade in default["trades"]:
            expected = oracle.features(trade["signal_us"])
            if expected is None or trade["reference"] != expected["reference"]:
                raise ValueError("executed trade reference does not reconcile")
        executed_checks[variant] = {
            "executed_default_attempts": len(executed),
            "executed_timestamps_sha256": canonical_hash(executed),
            "candidate_membership": "EXACT_MATCH",
            "reference_close": "EXACT_MATCH",
        }
        for trial in variant_trials:
            overall = independent_metrics(trial["trades"])
            stored = trial["summary"]["metrics"]
            for key, value in overall.items():
                if stored[key] != value:
                    raise ValueError(f"independent metric mismatch {variant}/{trial['profile']}/{key}")
            fold_results = {}
            for fold in protocol["folds"]:
                subset = [trade for trade in trial["trades"] if trade["fold_id"] == fold["fold_id"]]
                computed = independent_metrics(subset)
                stored_fold = next(
                    item["metrics"]
                    for item in trial["summary"]["folds"]
                    if item["fold_id"] == fold["fold_id"]
                )
                for key, value in computed.items():
                    if stored_fold[key] != value:
                        raise ValueError(
                            f"independent fold metric mismatch {variant}/{trial['profile']}/{fold['fold_id']}/{key}"
                        )
                fold_results[fold["fold_id"]] = computed
            metric_checks.append(
                {
                    "variant": variant,
                    "profile": trial["profile"],
                    "overall": overall,
                    "folds_sha256": canonical_hash(fold_results),
                    "status": "EXACT_MATCH",
                }
            )

    return {
        "schema_version": 1,
        "artifact_id": "WP-005-INDEPENDENT-FEATURE-RESULT-RECONCILIATION",
        "status": "PASS",
        "oracle_independence": "Does not call FeatureSource.at()/decision() for expected values; production calls are observed-side comparisons only.",
        "feature_definition": {
            "breakout": "completed 1h close > max preceding 24 completed 1h highs",
            "volume": "current completed 1h volume >= 2 * mean preceding 24 completed 1h volumes",
            "persistence": "43 completed 4h closes; U/D over 42 increments; U+D>0 and U>=2D",
            "common_eligibility": "current and t-1h each have contiguous complete 25x1h and 43x4h suffixes after quarantine",
            "reference": "current completed 1h close",
            "quarantine": "independently derived from canonical off-grid [open, open+1m) intersections",
        },
        "eligible_clocks": {
            fold["fold_id"]: {
                "eligible": eligible_counts[(fold["fold_id"], "eligible")],
                "ineligible": eligible_counts[(fold["fold_id"], "ineligible")],
            }
            for fold in protocol["folds"]
        },
        "candidate_reconciliation": candidate_checks,
        "executed_default_reconciliation": executed_checks,
        "feature_mismatches": production_mismatches + feature_value_mismatches,
        "metric_reconciliation": metric_checks,
        "metric_method": "Decimal recomputation from immutable TradeRecord fields; no signal selection rerun",
        "resolved_count_cumulative_net_expectancy_profit_factor_drawdown_cost_drag": "EXACT_MATCH",
        "fold_metrics": "EXACT_MATCH",
        "post_cutoff_bytes_read": False,
    }


def exact_wp004_replay(root: Path) -> dict[str, Any]:
    """Replay all 12 frozen trials in memory; never writes staging trial outputs."""
    protocol = load_protocol(root / "research/protocols/DEVELOPMENT_WALK_FORWARD_V1.json")
    inputs = ResearchInputs.load(root)
    lab = ContinuationLab(inputs, protocol)
    entries = []
    for variant, experiment in VARIANT_EXPERIMENTS.items():
        prereg = json.loads(
            (root / f"research/experiments/{experiment}/preregistration.v2.json").read_text(
                encoding="utf-8"
            )
        )
        dependencies = prereg["parameter_space"]["dependencies"]
        for dependency in dependencies:
            if file_hash(root / dependency["path"]) != dependency["sha256"]:
                raise ValueError(f"WP-004 dependency identity drift: {dependency['path']}")
        config_path = root / f"research/configs/wp004/{variant.lower()}.json"
        if variant == "REGIME_ONLY":
            config_path = root / "research/configs/wp004/regime_only.json"
        elif variant == "PARTICIPATION_ONLY":
            config_path = root / "research/configs/wp004/participation_only.json"
        else:
            config_path = root / "research/configs/wp004/aligned.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        finalized = json.loads(
            (root / f"research/experiments/{experiment}/trials.json").read_text(encoding="utf-8")
        )
        for profile in PROFILES:
            trial_id = f"{variant}:{profile}"
            replayed = {"trial_id": trial_id, "status": "COMPLETED", **lab.run_trial(config, trial_id)}
            original = next(item for item in finalized if item["trial_id"] == trial_id)
            replay_hash = canonical_hash(replayed)
            original_hash = canonical_hash(original)
            if replay_hash != original_hash:
                raise ValueError(f"exact WP-004 replay mismatch: {trial_id}")
            entries.append(
                {
                    "trial_id": trial_id,
                    "canonical_content_sha256": replay_hash,
                    "finalized_canonical_content_sha256": original_hash,
                    "status": "EXACT_MATCH",
                }
            )
    return {
        "schema_version": 1,
        "artifact_id": "WP-005-WP004-INTEGRITY-REPLAY",
        "status": "PASS",
        "classification": "INTEGRITY_REPLAY",
        "profiles_replayed": len(entries),
        "fold_components_replayed": len(entries) * 6,
        "temporary_outputs": "IN_MEMORY_ONLY_NONE_RETAINED",
        "new_experiment_result_ids": 0,
        "dataset_content_hash": "02168b73d8513d825978cdde3cc133e466b4aebcc0aaa48fecfb473de6e3acb2",
        "trials": entries,
        "post_cutoff_bytes_read": False,
    }
