"""AGGRESSIVE_BUY_FLOW_TRANSITION_V1: causal order-flow features and two frozen variants.

The event is a transition in exchange-reported aggressive buying: the previous completed
hour was not buy-dominant, the just-completed hour is, and the most recent completed
non-overlapping 4h context is already buy-dominant.

There is no price boundary, no trend membership, no persistence ratio, no volume
multiple and no pullback rule. The only price condition anywhere in the family is the
same-hour close-above-open confirmation used by the secondary variant.

The 0.5 balance point comes from the accounting meaning of the field — taker-buy base
volume equal to half of total base volume — and is never fitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .evaluation_protocol import HOUR_US, utc_us
from .order_flow import BALANCE, FEATURE_VERSION, FlowBucket, read_buckets
from .wp004 import ROOT

STRATEGY_VERSION = "AGGRESSIVE_BUY_FLOW_TRANSITION_V1"
VARIANTS = ("FLOW_CORE", "FLOW_PRICE_RESPONSE")
CONTEXT_MINUTES = 240
CONTEXT_US = 4 * HOUR_US
CUTOFF_US = utc_us("2024-12-31T23:59:00Z")
CONTEXT_RULE = (
    "MOST_RECENT_COMPLETED_NON_OVERLAPPING_4H_BUCKET_CLOSING_AT_OR_BEFORE_SIGNAL_MINUS_1H"
)

__all__ = [
    "BALANCE",
    "CONTEXT_RULE",
    "CONTEXT_US",
    "FEATURE_VERSION",
    "STRATEGY_VERSION",
    "VARIANTS",
    "FlowFeatures",
    "FlowSource",
    "IneligibleFlowSignal",
    "context_open",
]


class IneligibleFlowSignal(ValueError):
    """A required completed, unquarantined, traded bucket is unavailable at signal time."""


def context_open(signal_us: int) -> int:
    """Open of the most recent completed 4h bucket whose close is at or before ``t-1h``.

    A 4h bucket opening at ``b`` closes at ``b + 4h``, so the constraint ``b + 4h <= t - 1h``
    gives ``b = floor((t - 5h) / 4h) * 4h``. This guarantees the context never contains the
    current 1h signal bar.
    """
    return (signal_us - 5 * HOUR_US) // CONTEXT_US * CONTEXT_US


@dataclass(frozen=True)
class FlowFeatures:
    """Everything the two frozen rules may consult, observed at the decision boundary."""

    asof_us: int
    reference: float
    current_open: float
    current_share: float
    previous_share: float
    context_share: float
    context_open_us: int
    context_close_us: int
    context_staleness_us: int
    previous_non_dominant: bool
    current_dominant: bool
    transition: bool
    context_dominant: bool
    price_response: bool


class FlowSource:
    """Holds only completed, eligible order-flow buckets; never the execution path."""

    def __init__(self, hourly: tuple[FlowBucket, ...], context: tuple[FlowBucket, ...]):
        self.hourly = {bucket.open_us: bucket for bucket in hourly}
        self.context = {bucket.open_us: bucket for bucket in context}
        if len(self.hourly) != len(hourly) or len(self.context) != len(context):
            raise ValueError("order-flow buckets must have unique aligned open instants")
        for bucket in (*hourly, *context):
            if bucket.open_us > CUTOFF_US:
                raise ValueError("order-flow buckets must stay inside the development boundary")
        self._cache: dict[int, FlowFeatures] = {}

    def _eligible(self, buckets: dict[int, FlowBucket], open_us: int) -> FlowBucket:
        bucket = buckets.get(open_us)
        if bucket is None or not bucket.eligible or bucket.share is None:
            raise IneligibleFlowSignal("required completed unquarantined bucket unavailable")
        return bucket

    def at(self, signal_us: int) -> FlowFeatures:
        if signal_us % HOUR_US or signal_us > CUTOFF_US:
            raise ValueError("signal clock outside hourly development boundary")
        if signal_us in self._cache:
            return self._cache[signal_us]
        current = self._eligible(self.hourly, signal_us - HOUR_US)
        previous = self._eligible(self.hourly, signal_us - 2 * HOUR_US)
        opened = context_open(signal_us)
        context = self._eligible(self.context, opened)
        assert current.share is not None and previous.share is not None
        assert context.share is not None
        closed = opened + CONTEXT_US
        result = FlowFeatures(
            asof_us=signal_us,
            reference=current.close,
            current_open=current.open,
            current_share=current.share,
            previous_share=previous.share,
            context_share=context.share,
            context_open_us=opened,
            context_close_us=closed,
            context_staleness_us=signal_us - closed,
            previous_non_dominant=previous.share <= BALANCE,
            current_dominant=current.share > BALANCE,
            transition=previous.share <= BALANCE and current.share > BALANCE,
            context_dominant=context.share > BALANCE,
            price_response=current.close > current.open,
        )
        self._cache[signal_us] = result
        return result

    def decision(
        self, signal_us: int, variant: str, delay_hours: int = 0
    ) -> tuple[bool, FlowFeatures, float]:
        """Emit the frozen rule; the delay control shifts the condition, never the barriers."""
        if variant not in VARIANTS or delay_hours not in (0, 1):
            raise ValueError("undeclared strategy variant or timing perturbation")
        # Both feature clocks are required for every profile: the same quality universe.
        current = self.at(signal_us)
        previous = self.at(signal_us - HOUR_US)
        feature = previous if delay_hours else current
        emits = feature.transition and feature.context_dominant
        if variant == "FLOW_PRICE_RESPONSE":
            emits = emits and feature.price_response
        return emits, feature, current.reference


def flow_source(root: Path = ROOT) -> FlowSource:
    """Load the hash-verified order-flow substrate as a signal-time feature source."""
    return FlowSource(read_buckets("1h", root), read_buckets("4h", root))
