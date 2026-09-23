"""Deterministic proofs for `PREDICTIVE_V2_PUBLIC_TAKER_FLOW_HORIZON_FOUNDATION_V1`.

Every claim here is hand-computable on synthetic in-memory klines or synthetic hourly panels.
Nothing in this file downloads, reads the pinned archive, or observes a market result.
"""

from __future__ import annotations

import io
import math
import zipfile

import numpy as np
import pytest
from app.predictive.taker_flow_foundation import (
    FAMILY_SEED,
    HORIZONS_HOURS,
    NO_HORIZON_SUPPORTED,
    NOT_SUPPORTED,
    PER_HORIZON_ALPHA,
    SELECTION_OUTCOMES,
    SUPPORTED,
    WINDOW_HOURS,
    FoundationError,
    HourlyPanel,
    ScoredFold,
    block_length_hours,
    bootstrap_interval,
    build_panel,
    calibration_split,
    evaluate_horizon,
    horizon_seed_sequences,
    horizon_targets,
    markdown_bytes,
    outer_fold_masks,
    qualification,
    select_horizon,
    year_start_seconds,
)
from app.predictive.taker_flow_source import (
    DUPLICATED_MINUTE,
    INCOMPLETE_MINUTE,
    INVALID,
    KLINE_COLUMNS,
    MARKETS,
    MINUTE_MS,
    NON_FINITE_VALUE,
    OFF_GRID_TIMESTAMP,
    OUTSIDE_OWN_MONTH,
    SPOT,
    USDM,
    VALID,
    WINDOW_END_MS,
    WINDOW_START_MS,
    MinuteBook,
    TakerFlowSourceError,
    archive_member,
    archive_url,
    build_manifest,
    iter_kline_rows,
    manifest_entry,
    month_bounds_ms,
    months,
    parse_checksum_file,
    sha256_bytes,
    verified_object,
)

HOUR = 3600
JANUARY = month_bounds_ms(2020, 1)


def kline(open_ms: int, close: float, quote: float, taker_quote: float, **overrides: str) -> str:
    fields = {
        "open_time": str(open_ms),
        "open": "1",
        "high": "1",
        "low": "1",
        "close": repr(close),
        "volume": "1",
        "close_time": str(open_ms + MINUTE_MS - 1),
        "quote_volume": repr(quote),
        "count": "1",
        "taker_buy_volume": "1",
        "taker_buy_quote_volume": repr(taker_quote),
        "ignore": "0",
    }
    fields.update(overrides)
    return ",".join(fields[name] for name in KLINE_COLUMNS)


def hour_rows(hour: int, close: float, quote: float, taker_quote: float) -> list[str]:
    start = WINDOW_START_MS + hour * 60 * MINUTE_MS
    return [kline(start + minute * MINUTE_MS, close, quote, taker_quote) for minute in range(60)]


def ingest(book: MinuteBook, rows: list[str]) -> None:
    book.ingest(iter_kline_rows("\n".join(rows) + "\n"), *JANUARY)


def two_books(
    spot: tuple[float, float] = (10.0, 6.0), um: tuple[float, float] = (20.0, 5.0)
) -> dict[str, MinuteBook]:
    books = {market: MinuteBook(market) for market in MARKETS}
    for hour in range(3):
        ingest(books[SPOT], hour_rows(hour, 100.0 + hour, *spot))
        ingest(books[USDM], hour_rows(hour, 100.0 + hour, *um))
    return books


# --------------------------------------------------------------------------------------
# Source identity and parsing.
# --------------------------------------------------------------------------------------


def test_archive_identity_is_official_monthly_and_inside_the_window() -> None:
    assert len(months()) == 60
    assert months()[0] == (2020, 1) and months()[-1] == (2024, 12)
    assert archive_url(SPOT, 2020, 1) == (
        "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2020-01.zip"
    )
    assert archive_url(USDM, 2024, 12) == (
        "https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/"
        "BTCUSDT-1m-2024-12.zip"
    )


def test_checksum_file_parsing_and_verification_fail_closed() -> None:
    digest = sha256_bytes(b"payload")
    assert parse_checksum_file(f"{digest}  BTCUSDT-1m-2020-01.zip\n", "BTCUSDT-1m-2020-01.zip")
    with pytest.raises(TakerFlowSourceError):
        parse_checksum_file(f"{digest}  BTCUSDT-1m-2020-02.zip", "BTCUSDT-1m-2020-01.zip")
    with pytest.raises(TakerFlowSourceError):
        parse_checksum_file("abc  BTCUSDT-1m-2020-01.zip", "BTCUSDT-1m-2020-01.zip")


def zipped(name: str, text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, text)
    return buffer.getvalue()


def test_manifest_entry_pins_path_sizes_and_official_checksum() -> None:
    member = "\n".join(hour_rows(0, 100.0, 10.0, 6.0)) + "\n"
    content = zipped("BTCUSDT-1m-2020-01.csv", member)
    entry = manifest_entry(SPOT, 2020, 1, content, sha256_bytes(content), "2026-09-23T00:00:00Z")
    assert entry["archive_size_bytes"] == len(content)
    assert entry["member_size_bytes"] == len(member.encode("utf-8"))
    assert entry["official_checksum_sha256"] == entry["sha256"] == sha256_bytes(content)
    assert entry["source_path"] == "data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2020-01.zip"
    with pytest.raises(TakerFlowSourceError):
        manifest_entry(SPOT, 2020, 1, content, "0" * 64, "2026-09-23T00:00:00Z")
    with pytest.raises(TakerFlowSourceError):
        archive_member(zipped("other.csv", member), 2020, 1)


def test_manifest_requires_every_market_month_exactly_once() -> None:
    entries = [
        {"market": market, "month": f"{y:04d}-{m:02d}", "sha256": "0" * 64}
        for market in MARKETS
        for y, m in months()
    ]
    assert build_manifest(entries)["objects"] == 120
    with pytest.raises(TakerFlowSourceError):
        build_manifest(entries[:-1])
    with pytest.raises(TakerFlowSourceError):
        build_manifest([*entries, entries[0]])


def test_stored_object_is_reverified_against_the_manifest(tmp_path) -> None:
    content = zipped("BTCUSDT-1m-2020-01.csv", "x")
    (tmp_path / "raw.zip").write_bytes(content)
    entry = {
        "raw_path": "raw.zip",
        "archive_size_bytes": len(content),
        "sha256": sha256_bytes(content),
        "official_checksum_sha256": sha256_bytes(content),
    }
    assert verified_object(tmp_path, entry) == content
    (tmp_path / "raw.zip").write_bytes(content + b"!")
    with pytest.raises(TakerFlowSourceError):
        verified_object(tmp_path, entry)


def test_parser_accepts_the_official_header_and_rejects_bad_schema() -> None:
    row = kline(WINDOW_START_MS, 100.0, 10.0, 6.0)
    with_header = ",".join(KLINE_COLUMNS) + "\n" + row + "\n"
    assert list(iter_kline_rows(with_header)) == [
        (WINDOW_START_MS, WINDOW_START_MS + 59_999, 100.0, 10.0, 6.0)
    ]
    assert list(iter_kline_rows(row + "\n")) == list(iter_kline_rows(with_header))
    with pytest.raises(TakerFlowSourceError):
        list(iter_kline_rows("1,2,3\n"))
    with pytest.raises(TakerFlowSourceError):
        list(iter_kline_rows(kline(WINDOW_START_MS * 1000, 1.0, 1.0, 1.0)))
    with pytest.raises(TakerFlowSourceError):
        list(iter_kline_rows(row + "\n" + ",".join(KLINE_COLUMNS) + "\n"))


def test_minute_book_marks_every_invalidity_and_never_repairs() -> None:
    book = MinuteBook(SPOT)
    base = WINDOW_START_MS
    ingest(
        book,
        [
            kline(base, 1.0, 1.0, 1.0),
            kline(base, 1.0, 1.0, 1.0),  # exact duplicate still invalidates the minute
            kline(base + MINUTE_MS + 7, 1.0, 1.0, 1.0),
            kline(base + 2 * MINUTE_MS, 1.0, 1.0, 1.0, close_time=str(base + 2 * MINUTE_MS)),
            kline(base + 3 * MINUTE_MS, 1.0, float("nan"), 1.0),
            kline(base + 4 * MINUTE_MS, 1.0, 1.0, 1.0),
        ],
    )
    assert book.status[:6].tolist() == [INVALID, INVALID, INVALID, INVALID, VALID, 0]
    assert book.invalid_reasons[DUPLICATED_MINUTE] == 1
    assert book.invalid_reasons[OFF_GRID_TIMESTAMP] == 1
    assert book.invalid_reasons[INCOMPLETE_MINUTE] == 1
    assert book.invalid_reasons[NON_FINITE_VALUE] == 1
    assert math.isnan(book.close[0])

    february = MinuteBook(SPOT)
    february.ingest(iter_kline_rows(kline(base, 1.0, 1.0, 1.0)), *month_bounds_ms(2020, 2))
    assert february.invalid_reasons[OUTSIDE_OWN_MONTH] == 1


def test_post_cutoff_record_fails_closed() -> None:
    book = MinuteBook(SPOT)
    with pytest.raises(TakerFlowSourceError):
        book.ingest(iter_kline_rows(kline(WINDOW_END_MS, 1.0, 1.0, 1.0)), *JANUARY)


# --------------------------------------------------------------------------------------
# Features: maker/taker arithmetic, causality, fail-closed availability.
# --------------------------------------------------------------------------------------


def test_taker_imbalance_arithmetic_is_exact() -> None:
    panel = build_panel(two_books(spot=(10.0, 6.0), um=(20.0, 5.0)))
    # spot: buy=360, total=600 -> (720-600)/600 = 0.2; um: buy=300, total=1200 -> -0.5
    assert panel.feature_valid[0]
    assert panel.features[0] == pytest.approx([0.2, -0.5, 0.7], abs=1e-15)
    assert panel.decision_times[0] == WINDOW_START_MS // 1000 + HOUR
    assert panel.decision_close[0] == 100.0
    assert panel.feature_valid[:3].all() and not panel.feature_valid[3:].any()


def test_features_read_only_minutes_completed_by_the_decision_instant() -> None:
    books = two_books()
    reference = build_panel(books)
    # Minute [T, T+1m) for T = first decision instant is hour 1's first minute.
    books[SPOT].taker_quote[60] = 0.0
    books[SPOT].close[60] = 999.0
    changed = build_panel(books)
    assert changed.features[0].tolist() == reference.features[0].tolist()
    assert changed.decision_close[0] == reference.decision_close[0]
    # The last minute before T does enter the feature at T.
    books[SPOT].taker_quote[59] = 0.0
    assert build_panel(books).features[0][0] != reference.features[0][0]


def test_missing_duplicated_or_non_positive_minutes_make_the_vector_unavailable() -> None:
    missing = two_books()
    missing[USDM].status[30] = 0
    assert not build_panel(missing).feature_valid[0]

    duplicated = {market: MinuteBook(market) for market in MARKETS}
    for market in MARKETS:
        rows = hour_rows(0, 100.0, 10.0, 6.0)
        ingest(duplicated[market], [*rows, rows[10]])
    panel = build_panel(duplicated)
    assert not panel.feature_valid[0]
    assert np.isnan(panel.features[0]).all()

    zero = two_books(spot=(0.0, 0.0))
    assert not build_panel(zero).feature_valid[0]


# --------------------------------------------------------------------------------------
# Targets, folds and purge.
# --------------------------------------------------------------------------------------


def synthetic_panel(closes: np.ndarray, features: np.ndarray | None = None) -> HourlyPanel:
    count = closes.shape[0]
    times = WINDOW_START_MS // 1000 + (np.arange(count, dtype=np.int64) + 1) * HOUR
    if features is None:
        features = np.zeros((count, 3))
    return HourlyPanel(
        decision_times=times,
        features=features,
        feature_valid=np.isfinite(features).all(axis=1),
        decision_close=closes,
    )


def test_targets_are_exact_terminal_signs_per_horizon() -> None:
    closes = np.array([100.0, 101.0, 101.0, 99.0, np.nan, 100.0])
    returns, code = horizon_targets(synthetic_panel(closes), 1)
    assert returns[0] == pytest.approx(math.log(101 / 100))
    assert code.tolist() == [1, -1, 0, -2, -2, -2]
    _, four = horizon_targets(synthetic_panel(closes), 4)
    assert four.tolist() == [-2, 0, -2, -2, -2, -2]


def test_outer_folds_are_annual_and_purged_per_horizon() -> None:
    times = WINDOW_START_MS // 1000 + (np.arange(WINDOW_HOURS, dtype=np.int64) + 1) * HOUR
    for horizon in HORIZONS_HOURS:
        for year in (2021, 2022, 2023, 2024):
            training, evaluation = outer_fold_masks(times, horizon, year)
            start = year_start_seconds(year)
            assert (times[training] + horizon * HOUR).max() == start
            assert times[evaluation].min() == start
            assert times[evaluation].max() == year_start_seconds(year + 1) - HOUR
            assert not (training & evaluation).any()


def test_calibration_split_is_chronological_with_two_horizon_embargo() -> None:
    times = np.arange(100, dtype=np.int64) * HOUR
    base, calibration = calibration_split(times.tolist(), 4)
    assert calibration.tolist() == list(range(80, 100))
    assert base.max() == 72  # 72h + 8h embargo == first calibration instant at 80h
    assert base.tolist() == list(range(73))
    with pytest.raises(FoundationError):
        calibration_split(times[::-1].tolist(), 4)


# --------------------------------------------------------------------------------------
# Bootstrap, qualification and selection.
# --------------------------------------------------------------------------------------


def scored_fold(year: int, values: np.ndarray, first: int = 0) -> ScoredFold:
    times = first + np.arange(values.shape[0], dtype=np.int64) * HOUR
    return ScoredFold(year, first, int(times[-1]), times, values)


def test_block_length_and_seed_streams_are_frozen() -> None:
    assert [block_length_hours(h) for h in HORIZONS_HOURS] == [48, 48, 48]
    assert block_length_hours(36) == 72
    seeds = horizon_seed_sequences()
    assert list(seeds) == [24, 4, 1]
    assert all(seed.entropy == FAMILY_SEED for seed in seeds.values())
    assert PER_HORIZON_ALPHA == pytest.approx(0.0166666667)


def test_bootstrap_is_deterministic_and_stays_inside_folds() -> None:
    rng = np.random.default_rng(1)
    folds = [scored_fold(2021, rng.normal(size=500)), scored_fold(2022, rng.normal(size=300))]
    seed = horizon_seed_sequences()[24]
    first = bootstrap_interval(folds, 48, seed, replicates=300)
    second = bootstrap_interval(folds, 48, horizon_seed_sequences()[24], replicates=300)
    assert first == second
    assert first["blocks_cross_fold_boundaries"] is False
    assert first["fold_geometry"]["2021"]["block_start_positions"] == 500 - 48 + 1
    lower, upper = first["interval"]
    assert lower < upper

    constant = [scored_fold(2021, np.full(200, 0.25)), scored_fold(2022, np.full(100, 0.25))]
    interval = bootstrap_interval(constant, 48, seed, replicates=100)["interval"]
    assert interval == pytest.approx([0.25, 0.25])


def summary(**overrides) -> dict:
    folds = [{"feature_coverage": 0.97, "brier_improvement": 0.001} for _ in range(4)]
    base = {
        "pooled_feature_coverage": 0.97,
        "folds": folds,
        "pooled_brier_improvement": 0.001,
        "bootstrap": {"lower_bound": 0.0001},
        "pooled_model_log_loss": 0.69,
        "pooled_control_log_loss": 0.692,
    }
    base.update(overrides)
    return base


def test_qualification_requires_every_frozen_criterion() -> None:
    assert qualification(summary())["classification"] == SUPPORTED
    failing = [
        summary(pooled_feature_coverage=0.9499),
        summary(folds=[{"feature_coverage": 0.89, "brier_improvement": 0.001}] * 4),
        summary(pooled_brier_improvement=0.0),
        summary(bootstrap={"lower_bound": 0.0}),
        summary(
            folds=[{"feature_coverage": 0.97, "brier_improvement": -0.001}] * 2
            + [{"feature_coverage": 0.97, "brier_improvement": 0.0}] * 2
        ),
        summary(pooled_model_log_loss=0.693),
    ]
    for item in failing:
        assert qualification(item)["classification"] == NOT_SUPPORTED
    three_of_four = summary(
        folds=[{"feature_coverage": 0.97, "brier_improvement": -0.01}]
        + [{"feature_coverage": 0.97, "brier_improvement": 0.0}] * 3
    )
    assert qualification(three_of_four)["classification"] == SUPPORTED


def test_horizon_selection_follows_frozen_precedence_not_scores() -> None:
    assert select_horizon({24: SUPPORTED, 4: SUPPORTED, 1: SUPPORTED}) == SELECTION_OUTCOMES[24]
    assert select_horizon({24: NOT_SUPPORTED, 4: SUPPORTED, 1: SUPPORTED}) == (
        "FOUNDATION_SUPPORTS_4H_RESEARCH_ONLY"
    )
    assert select_horizon({24: NOT_SUPPORTED, 4: NOT_SUPPORTED, 1: SUPPORTED}) == (
        "FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY"
    )
    assert select_horizon(dict.fromkeys(HORIZONS_HOURS, NOT_SUPPORTED)) == NO_HORIZON_SUPPORTED
    with pytest.raises(FoundationError):
        select_horizon({24: SUPPORTED})


# --------------------------------------------------------------------------------------
# End to end on a synthetic panel: the pipeline recovers a planted signal.
# --------------------------------------------------------------------------------------


def planted_panel(strength: float) -> HourlyPanel:
    rng = np.random.default_rng(7)
    features = rng.normal(size=(WINDOW_HOURS, 3))
    step = strength * features[:, 0] + rng.normal(size=WINDOW_HOURS)
    # The one-hour step after T is driven by the feature observed at T.
    closes = 100.0 * np.exp(np.concatenate(([0.0], np.cumsum(step[:-1] * 1e-3))))
    features[5] = np.nan
    return synthetic_panel(closes, features)


def test_evaluate_horizon_recovers_a_planted_signal_and_writes_a_report() -> None:
    seeds = horizon_seed_sequences()
    item = evaluate_horizon(planted_panel(1.0), 1, seeds[1], replicates=200)
    assert [fold["year"] for fold in item["folds"]] == [2021, 2022, 2023, 2024]
    assert item["pooled_feature_coverage"] > 0.999
    assert item["pooled_brier_improvement"] > 0
    assert item["qualification"]["classification"] == SUPPORTED
    for fold in item["folds"]:
        assert fold["training_last_label_end"] <= f"{fold['year']}-01-01T00:00:00Z"
        assert (
            fold["base_fit_rows"] + fold["embargo_dropped_rows"] + fold["calibration_rows"]
            == fold["training_rows"]
        )

    null = evaluate_horizon(planted_panel(0.0), 1, seeds[1], replicates=200)
    assert null["qualification"]["classification"] == NOT_SUPPORTED

    result = {
        "experiment_id": "X",
        "protocol": {"path": "p", "sha256": "0"},
        "source": {"manifest_path": "m", "manifest_sha256": "0"},
        "selection": select_horizon({24: NOT_SUPPORTED, 4: NOT_SUPPORTED, 1: SUPPORTED}),
        "horizons": {str(h): item for h in HORIZONS_HOURS},
    }
    assert b"FOUNDATION_SUPPORTS_1H_RESEARCH_ONLY" in markdown_bytes(result)
