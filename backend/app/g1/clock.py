"""Virtual clock, replay control and the two synthetic adapters.

Replay speed is a wall-clock pacing multiplier only: `tick(wall_seconds)` converts elapsed wall
time into a virtual-time target (`speed * wall_seconds`), and the core then processes every minute
boundary up to that target exactly as it would one minute at a time. Event identities never
contain wall time, so every speed reproduces the same records.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import StrEnum

from .bars import MINUTE, Bar
from .core import G1Core

SPEEDS = (60, 900, 3600, 14400)  # virtual seconds per wall second
DEFAULT_SPEED = 900


class ReplayStatus(StrEnum):
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETE = "COMPLETE"


class ReplayController:
    """Historical-replay adapter: a preloaded synthetic source released by a virtual cursor."""

    def __init__(self, core: G1Core, source: tuple[Bar, ...]) -> None:
        self.core = core
        self._pending = deque(source)
        self.status = ReplayStatus.READY
        self.speed = DEFAULT_SPEED
        self._carry = 0.0

    @property
    def cursor(self) -> datetime:
        return self.core.cursor

    def _advance(self, target: datetime) -> None:
        while self._pending and self._pending[0].available_at <= target:
            self.core.ingest(self._pending.popleft())
        self.core.advance_to(target)
        if self.core.complete:
            self.status = ReplayStatus.COMPLETE

    def start(self) -> None:
        if self.status is not ReplayStatus.COMPLETE:
            self.status = ReplayStatus.RUNNING

    def pause(self) -> None:
        if self.status is ReplayStatus.RUNNING:
            self.status = ReplayStatus.PAUSED

    def set_speed(self, speed: int) -> None:
        if speed not in SPEEDS:
            raise ValueError(f"speed must be one of {SPEEDS}")
        self.speed = speed

    def step(self, unit: str = "15m") -> None:
        """Single step while not running: one 1m source event or to the next 15m decision."""
        if self.status is ReplayStatus.RUNNING:
            raise ValueError("pause before single-stepping")
        if self.status is ReplayStatus.COMPLETE:
            return
        if unit == "1m":
            target = self.cursor + MINUTE
        elif unit == "15m":
            target = self.cursor + MINUTE
            while target.minute % 15:
                target += MINUTE
        else:
            raise ValueError("step unit must be 1m or 15m")
        self._advance(target)
        if self.status is ReplayStatus.READY:
            self.status = ReplayStatus.PAUSED

    def tick(self, wall_seconds: float) -> None:
        """Advance by `speed * wall_seconds` of virtual time while running (UI pacing only)."""
        if self.status is not ReplayStatus.RUNNING:
            return
        if not 0 < wall_seconds <= 5:
            raise ValueError("wall_seconds must be in (0, 5]")
        # Whole virtual minutes advance; the sub-minute remainder carries to the next tick.
        self._carry += self.speed * wall_seconds
        minutes = max(1, int(self._carry // 60))
        self._carry = max(0.0, self._carry - minutes * 60)
        self._advance(self.cursor + timedelta(minutes=minutes))

    def run_to_end(self, pace: Callable[[], float] | None = None) -> None:
        self.start()
        while self.status is ReplayStatus.RUNNING:
            self.tick(pace() if pace else 1.0)


class LiveStyleAdapter:
    """Push adapter: minutes arrive one by one at their availability instant, plus heartbeats.

    It feeds the same `G1Core` as replay; only the arrival mechanics differ.
    """

    def __init__(self, core: G1Core) -> None:
        self.core = core

    def on_minute(self, bar: Bar) -> None:
        self.core.advance_to(bar.available_at - MINUTE)
        self.core.ingest(bar)
        self.core.advance_to(bar.available_at)

    def heartbeat(self, now: datetime) -> None:
        self.core.advance_to(now)
