from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .models import Bar


@dataclass(frozen=True)
class AsOfView:
    signal_time: datetime
    signal_bars_1h: tuple[Bar, ...]
    context_bars_4h: tuple[Bar, ...]

    @classmethod
    def build(cls, signal_time: datetime, bars_1h: tuple[Bar, ...], bars_4h: tuple[Bar, ...]):
        eligible_1h = tuple(
            b for b in bars_1h if b.complete and b.open_time + timedelta(hours=1) <= signal_time
        )
        eligible_4h = tuple(
            b for b in bars_4h if b.complete and b.open_time + timedelta(hours=4) <= signal_time
        )
        if not eligible_1h:
            raise ValueError("no completed signal bar available")
        return cls(signal_time, eligible_1h, eligible_4h)
