import numpy as np
from app.research.baselines import random_seed, signal_for


def test_fixed_trend_breakout_and_delayed_rules():
    closes = np.arange(1.0, 171.0)
    highs = closes + 1
    assert signal_for("TREND", closes, highs, 169)
    assert signal_for("TREND_DELAY_1H", closes, highs, 169)
    highs[145:169] = 1000
    assert not signal_for("BREAKOUT", closes, highs, 169)
    highs[145:169] = 1
    assert signal_for("BREAKOUT", closes, highs, 169)


def test_random_seeds_are_fixed_sha256_values():
    assert random_seed(0) == 16912590939832400125
    assert len({random_seed(i) for i in range(32)}) == 32


def test_no_trade_and_future_access_rejection():
    values = np.ones(169)
    assert not signal_for("NO_TRADE", values, values, 168)
    try:
        signal_for("TREND", values, values, 169)
    except (IndexError, ValueError):
        pass
    else:
        raise AssertionError("future/incomplete index access should fail")
