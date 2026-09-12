"""PROSPECTIVE_PAPER_FEATURES_V1 must match the frozen ALIGNED gates exactly.

The adapter exists only so forward analysis carries real timestamps. Every fixture is
run through both the frozen research `FeatureSource` and the adapter over identical
pre-cutoff instants and must agree on every field the product uses, so the adapter can
never silently loosen a gate or create extra signals.
"""

from __future__ import annotations

import ast
from dataclasses import asdict
from pathlib import Path

import pytest
from app.product.features import (
    CONTEXT_LOOKBACK,
    HOURLY_LOOKBACK,
    PROSPECTIVE_FEATURES_VERSION,
    ProspectiveFeatureSource,
)
from app.research.continuation import (
    CUTOFF_US,
    FEATURE_VERSION,
    FeatureBar,
    FeatureSource,
    IneligibleSignal,
)
from app.research.evaluation_protocol import utc_us

ROOT = Path(__file__).resolve().parents[2]
HOUR_US = 3_600_000_000
CONTEXT_US = 4 * HOUR_US
PRE_CUTOFF = utc_us("2024-06-03T12:00:00Z")
POST_CUTOFF = utc_us("2026-03-05T12:00:00Z")
VARIANT = "ALIGNED"


def _hourly(signal_us: int, *, breakout: bool, participation: bool) -> list[FeatureBar]:
    """26 completed hourly bars: the union both feature clocks in `decision` need."""
    last_open = signal_us - HOUR_US
    bars = [
        FeatureBar(last_open - (HOURLY_LOOKBACK - index) * HOUR_US, 100.0, 95.0, 10.0)
        for index in range(HOURLY_LOOKBACK + 1)
    ]
    bars[-1] = FeatureBar(
        bars[-1].open_us,
        120.0 if breakout else 99.0,
        120.0 if breakout else 95.0,
        40.0 if participation else 5.0,
    )
    return bars


def _context(signal_us: int, *, persistent_up: bool) -> list[FeatureBar]:
    """44 completed four-hour bars: the union both feature clocks need."""
    last_open = signal_us // CONTEXT_US * CONTEXT_US - CONTEXT_US
    bars = []
    for index in range(CONTEXT_LOOKBACK + 1):
        open_us = last_open - (CONTEXT_LOOKBACK - index) * CONTEXT_US
        close = 50.0 + index if persistent_up else 50.0 + (index % 2)
        bars.append(FeatureBar(open_us, close + 5.0, close, 10.0))
    return bars


def _fixtures(signal_us: int) -> dict[str, tuple[list[FeatureBar], list[FeatureBar]]]:
    """The positive case and each individual gate failing on its own."""
    return {
        "aligned_positive": (
            _hourly(signal_us, breakout=True, participation=True),
            _context(signal_us, persistent_up=True),
        ),
        "breakout_fails": (
            _hourly(signal_us, breakout=False, participation=True),
            _context(signal_us, persistent_up=True),
        ),
        "persistent_up_fails": (
            _hourly(signal_us, breakout=True, participation=True),
            _context(signal_us, persistent_up=False),
        ),
        "participation_fails": (
            _hourly(signal_us, breakout=True, participation=False),
            _context(signal_us, persistent_up=True),
        ),
        "all_gates_fail": (
            _hourly(signal_us, breakout=False, participation=False),
            _context(signal_us, persistent_up=False),
        ),
    }


def _both(name: str, signal_us: int = PRE_CUTOFF, variant: str = VARIANT, delay: int = 0):
    hourly, context = _fixtures(signal_us)[name]
    frozen = FeatureSource(tuple(hourly), tuple(context)).decision(signal_us, variant, delay)
    prospective = ProspectiveFeatureSource(hourly, context).decision(signal_us, variant, delay)
    return frozen, prospective


def _comparable(result) -> tuple:
    emits, feature, reference = result
    return emits, asdict(feature), reference


# --- exact equivalence -----------------------------------------------------------


@pytest.mark.parametrize("fixture", sorted(_fixtures(PRE_CUTOFF)))
def test_prospective_features_match_the_frozen_source_exactly(fixture: str) -> None:
    frozen, prospective = _both(fixture)
    assert _comparable(prospective) == _comparable(frozen)


def test_the_positive_aligned_case_emits_in_both() -> None:
    frozen, prospective = _both("aligned_positive")
    assert frozen[0] is prospective[0] is True
    assert prospective[1].breakout == prospective[1].persistent_up is True
    assert prospective[1].participation is True
    assert prospective[2] == frozen[2]


@pytest.mark.parametrize(
    ("fixture", "gate"),
    [
        ("breakout_fails", "breakout"),
        ("persistent_up_fails", "persistent_up"),
        ("participation_fails", "participation"),
    ],
)
def test_each_individual_failed_gate_blocks_identically(fixture: str, gate: str) -> None:
    frozen, prospective = _both(fixture)
    assert frozen[0] is prospective[0] is False
    assert getattr(prospective[1], gate) is getattr(frozen[1], gate) is False
    assert _comparable(prospective) == _comparable(frozen)


@pytest.mark.parametrize("variant", ["ALIGNED", "REGIME_ONLY", "PARTICIPATION_ONLY"])
@pytest.mark.parametrize("delay", [0, 1])
def test_every_variant_and_timing_profile_agrees(variant: str, delay: int) -> None:
    for fixture in sorted(_fixtures(PRE_CUTOFF)):
        frozen, prospective = _both(fixture, variant=variant, delay=delay)
        assert _comparable(prospective) == _comparable(frozen)


def test_continuous_feature_values_agree_bit_for_bit() -> None:
    frozen, prospective = _both("aligned_positive")
    assert prospective[1].signed_efficiency == frozen[1].signed_efficiency
    assert prospective[1].relative_volume == frozen[1].relative_volume
    assert prospective[1].reference == frozen[1].reference
    assert prospective[1].asof_us == frozen[1].asof_us


# --- missing and non-contiguous data ---------------------------------------------


def test_missing_hourly_data_fails_closed_in_both() -> None:
    hourly, context = _fixtures(PRE_CUTOFF)["aligned_positive"]
    short = hourly[3:]
    with pytest.raises(IneligibleSignal):
        FeatureSource(tuple(short), tuple(context)).decision(PRE_CUTOFF, VARIANT)
    with pytest.raises(IneligibleSignal):
        ProspectiveFeatureSource(short, context).decision(PRE_CUTOFF, VARIANT)


def test_noncontiguous_hourly_data_fails_closed_in_both() -> None:
    hourly, context = _fixtures(PRE_CUTOFF)["aligned_positive"]
    gapped = [bar for index, bar in enumerate(hourly) if index != 10]
    with pytest.raises(IneligibleSignal):
        FeatureSource(tuple(gapped), tuple(context)).decision(PRE_CUTOFF, VARIANT)
    with pytest.raises(IneligibleSignal):
        ProspectiveFeatureSource(gapped, context).decision(PRE_CUTOFF, VARIANT)


def test_missing_four_hour_context_fails_closed_in_both() -> None:
    hourly, context = _fixtures(PRE_CUTOFF)["aligned_positive"]
    short = context[5:]
    with pytest.raises(IneligibleSignal):
        FeatureSource(tuple(hourly), tuple(short)).decision(PRE_CUTOFF, VARIANT)
    with pytest.raises(IneligibleSignal):
        ProspectiveFeatureSource(hourly, short).decision(PRE_CUTOFF, VARIANT)


def test_noncontiguous_four_hour_context_fails_closed_in_both() -> None:
    hourly, context = _fixtures(PRE_CUTOFF)["aligned_positive"]
    gapped = [bar for index, bar in enumerate(context) if index != 20]
    with pytest.raises(IneligibleSignal):
        FeatureSource(tuple(hourly), tuple(gapped)).decision(PRE_CUTOFF, VARIANT)
    with pytest.raises(IneligibleSignal):
        ProspectiveFeatureSource(hourly, gapped).decision(PRE_CUTOFF, VARIANT)


def test_an_incomplete_bar_is_quarantined_in_both() -> None:
    hourly, context = _fixtures(PRE_CUTOFF)["aligned_positive"]
    partial = list(hourly)
    partial[-1] = FeatureBar(partial[-1].open_us, 120.0, 120.0, 40.0, False)
    with pytest.raises(IneligibleSignal):
        FeatureSource(tuple(partial), tuple(context)).decision(PRE_CUTOFF, VARIANT)
    with pytest.raises(IneligibleSignal):
        ProspectiveFeatureSource(partial, context).decision(PRE_CUTOFF, VARIANT)


def test_invalid_observations_are_refused_by_both() -> None:
    hourly, context = _fixtures(PRE_CUTOFF)["aligned_positive"]
    broken = list(hourly)
    broken[0] = FeatureBar(broken[0].open_us, 10.0, 90.0, 1.0)  # high below close
    with pytest.raises(ValueError, match="invalid derived observation"):
        FeatureSource(tuple(broken), tuple(context))
    with pytest.raises(ValueError, match="invalid derived observation"):
        ProspectiveFeatureSource(broken, context)


# --- boundary and alignment ------------------------------------------------------


@pytest.mark.parametrize("offset_hours", [0, 1, 2, 3, 4, 5])
def test_signal_hours_on_and_off_the_four_hour_boundary_agree(offset_hours: int) -> None:
    signal_us = PRE_CUTOFF + offset_hours * HOUR_US
    hourly, context = (
        _hourly(signal_us, breakout=True, participation=True),
        _context(signal_us, persistent_up=True),
    )
    frozen = FeatureSource(tuple(hourly), tuple(context)).decision(signal_us, VARIANT)
    prospective = ProspectiveFeatureSource(hourly, context).decision(signal_us, VARIANT)
    assert _comparable(prospective) == _comparable(frozen)


def test_an_off_hour_signal_clock_is_refused_by_both() -> None:
    hourly, context = _fixtures(PRE_CUTOFF)["aligned_positive"]
    off_hour = PRE_CUTOFF + 7 * 60 * 1_000_000
    with pytest.raises(ValueError, match="hourly"):
        FeatureSource(tuple(hourly), tuple(context)).at(off_hour)
    with pytest.raises(ValueError, match="hourly boundary"):
        ProspectiveFeatureSource(hourly, context).at(off_hour)


def test_unaligned_or_duplicate_bars_are_refused_by_both() -> None:
    _, context = _fixtures(PRE_CUTOFF)["aligned_positive"]
    unaligned = [FeatureBar(PRE_CUTOFF + 61 * 1_000_000, 10.0, 9.0, 1.0)]
    with pytest.raises(ValueError, match="unique aligned"):
        FeatureSource(tuple(unaligned), tuple(context))
    with pytest.raises(ValueError, match="unique aligned"):
        ProspectiveFeatureSource(unaligned, context)
    duplicate = [FeatureBar(PRE_CUTOFF, 10.0, 9.0, 1.0)] * 2
    with pytest.raises(ValueError, match="unique aligned"):
        ProspectiveFeatureSource(duplicate, context)


def test_an_undeclared_variant_or_perturbation_is_refused() -> None:
    hourly, context = _fixtures(PRE_CUTOFF)["aligned_positive"]
    source = ProspectiveFeatureSource(hourly, context)
    with pytest.raises(ValueError, match="undeclared strategy variant"):
        source.decision(PRE_CUTOFF, "SOMETHING_ELSE")
    with pytest.raises(ValueError, match="undeclared strategy variant"):
        source.decision(PRE_CUTOFF, VARIANT, 2)


# --- cutoff separation -----------------------------------------------------------


def test_the_frozen_feature_source_remains_cutoff_protected() -> None:
    assert POST_CUTOFF > CUTOFF_US
    hourly, context = _fixtures(POST_CUTOFF)["aligned_positive"]
    with pytest.raises(ValueError, match="development instants"):
        FeatureSource(tuple(hourly), tuple(context))
    pre_hourly, pre_context = _fixtures(PRE_CUTOFF)["aligned_positive"]
    with pytest.raises(ValueError, match="hourly development boundary"):
        FeatureSource(tuple(pre_hourly), tuple(pre_context)).at(POST_CUTOFF)


def test_the_adapter_accepts_real_post_cutoff_timestamps() -> None:
    hourly, context = _fixtures(POST_CUTOFF)["aligned_positive"]
    emits, feature, reference = ProspectiveFeatureSource(hourly, context).decision(
        POST_CUTOFF, VARIANT
    )
    assert emits is True
    assert feature.asof_us == POST_CUTOFF
    assert reference == 120.0


def test_post_cutoff_results_match_the_same_shape_pre_cutoff() -> None:
    """Only the instants differ; the adapter has no hidden date dependence."""
    for fixture in sorted(_fixtures(PRE_CUTOFF)):
        pre_h, pre_c = _fixtures(PRE_CUTOFF)[fixture]
        post_h, post_c = _fixtures(POST_CUTOFF)[fixture]
        pre = ProspectiveFeatureSource(pre_h, pre_c).decision(PRE_CUTOFF, VARIANT)
        post = ProspectiveFeatureSource(post_h, post_c).decision(POST_CUTOFF, VARIANT)
        assert post[0] == pre[0]
        assert post[2] == pre[2]
        assert asdict(post[1]) | {"asof_us": 0} == asdict(pre[1]) | {"asof_us": 0}


# --- separation from development code --------------------------------------------


def test_frozen_parameters_are_unchanged() -> None:
    from app.product import features

    assert features.HOURLY_LOOKBACK == 25
    assert features.CONTEXT_LOOKBACK == 43
    assert features.BREAKOUT_HOURS == features.VOLUME_BASELINE_HOURS == 24
    assert features.VOLUME_MULTIPLIER == features.UP_TO_DOWN_RATIO == 2
    assert features.FROZEN_FEATURE_VERSION == FEATURE_VERSION == "CONTINUATION_FEATURES_V2"
    assert PROSPECTIVE_FEATURES_VERSION == "PROSPECTIVE_PAPER_FEATURES_V1"


def test_no_research_or_backtest_module_imports_the_prospective_adapter() -> None:
    offenders = []
    for path in sorted((ROOT / "backend/app").rglob("*.py")):
        if path.parts[-2] == "product":
            continue
        source = path.read_text(encoding="utf-8")
        if "product.features" in source or "ProspectiveFeatureSource" in source:
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_the_adapter_never_reaches_market_storage_or_sealed_data() -> None:
    source = (ROOT / "backend/app/product/features.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not {name for name in modules if "data.store" in name or "sealed" in name}
    assert "data/canonical" not in source and "data/derived" not in source
    for forbidden in ("api_key", "secret", "order", "withdraw", "leverage", "margin"):
        assert forbidden not in source.lower()
