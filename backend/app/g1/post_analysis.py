"""Event/news post-analysis isolation boundary (core contracts section 14).

HotWindow and PostAnalysisReport are after-run entities. They are created only from a *completed*
run's issued records, they are stored separately from the run's EventStore, and no module of the
signal / state / prediction / decision path imports this module (enforced by
`backend/tests/test_g1_post_analysis_isolation.py`). No news is fetched in Checkpoint 1: the report
is a placeholder that records the boundary, not an explanation.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from .canonical import content_id
from .records import ClosedTrade, HotWindow, PostAnalysisReport

WINDOW_PADDING = timedelta(minutes=30)


class RunNotCompleteError(RuntimeError):
    """Post-analysis may run only after replay completion."""


class PostAnalysisStore:
    """Separate storage for post-analysis entities; never shared with a run's EventStore."""

    def __init__(self) -> None:
        self.windows: list[HotWindow] = []
        self.reports: list[PostAnalysisReport] = []


def create_hot_windows(core: Any, store: PostAnalysisStore) -> tuple[HotWindow, ...]:
    if not core.complete:
        raise RunNotCompleteError("hot windows are created only after the run completes")
    windows = []
    for trade in core.store.of_type(ClosedTrade):
        start, end = trade.entry_time - WINDOW_PADDING, trade.exit_time + WINDOW_PADDING
        trigger = f"CLOSED_TRADE_{trade.side.value}_{trade.exit_reason}"
        payload = (core.run_id, start, end, trigger, trade.trade_id)
        windows.append(
            HotWindow(
                content_id("HOT", payload), core.run_id, start, end, trigger, (trade.trade_id,)
            )
        )
    store.windows.extend(windows)
    return tuple(windows)


def create_report(
    core: Any, store: PostAnalysisStore, windows: tuple[HotWindow, ...]
) -> PostAnalysisReport:
    if not core.complete:
        raise RunNotCompleteError("post-analysis reports are created only after completion")
    ids = tuple(window.hot_window_id for window in windows)
    report = PostAnalysisReport(
        content_id("PAR", (core.run_id, ids)),
        core.run_id,
        ids,
        "PLACEHOLDER_NO_NEWS_OR_EVENT_SOURCE_FETCHED",
        (),
        (
            "RETROSPECTIVE_EXPLANATION_ONLY",
            "NOT_AN_INPUT_TO_SIGNAL_STATE_PREDICTION_OR_DECISION",
            "CANNOT_MUTATE_THE_RUN_OR_ITS_CONFIGURATION",
        ),
    )
    store.reports.append(report)
    return report
