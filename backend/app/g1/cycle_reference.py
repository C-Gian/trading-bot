"""Independent batch reference implementation of the ACP for numerical reconciliation.

Written separately from the streaming `cycle.AutocorrelationPeriodogram` (vectorized numpy over a
whole synthetic series, explicit index arithmetic instead of deques) so that the two can be
reconciled on synthetic fixtures, as the cycle method contract requires before use. It is still
causal: output at index t depends only on inputs 0..t. It is used by tests and the diagnostic
artifact only, never by the live/replay decision path.
"""

from __future__ import annotations

import numpy as np

AVG = 3


def reference_acp(values: np.ndarray, period1: int, period2: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (filtered, dominant_period) arrays; dominant is NaN until defined."""
    n = len(values)
    w = 0.707 * 2 * np.pi / period2
    alpha = (np.cos(w) + np.sin(w) - 1) / np.cos(w)
    hp = np.zeros(n)
    for t in range(2, n):
        hp[t] = (
            (1 - alpha / 2) ** 2 * (values[t] - 2 * values[t - 1] + values[t - 2])
            + 2 * (1 - alpha) * hp[t - 1]
            - (1 - alpha) ** 2 * hp[t - 2]
        )
    a1 = np.exp(-1.414 * np.pi / period1)
    c2 = 2 * a1 * np.cos(1.414 * np.pi / period1)
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    filt = np.zeros(n)
    for t in range(n):
        hp_prev = hp[t - 1] if t >= 1 else 0.0
        f1 = filt[t - 1] if t >= 1 else 0.0
        f2 = filt[t - 2] if t >= 2 else 0.0
        filt[t] = c1 * (hp[t] + hp_prev) / 2 + c2 * f1 + c3 * f2
    periods = np.arange(period1, period2 + 1)
    lags = np.arange(AVG, period2 + 1)
    cos_m = np.cos(2 * np.pi * np.outer(1.0 / periods, lags))
    sin_m = np.sin(2 * np.pi * np.outer(1.0 / periods, lags))
    r = np.zeros(len(periods))
    dominant = np.full(n, np.nan)
    first = period2 + AVG - 1
    for t in range(first, n):
        x = filt[t - np.arange(AVG)]
        corr = np.zeros(period2 + 1)
        for lag in range(period2 + 1):
            y = filt[t - lag - np.arange(AVG)]
            xm, ym = x - x.mean(), y - y.mean()
            den = (xm @ xm) * (ym @ ym)
            if den > 0:
                corr[lag] = (xm @ ym) / np.sqrt(den)
        sq = (cos_m @ corr[AVG:]) ** 2 + (sin_m @ corr[AVG:]) ** 2
        r = 0.2 * sq**2 + 0.8 * r
        top = r.max()
        if top <= 0:
            continue
        pwr = r / top
        mask = pwr >= 0.5
        if pwr[mask].sum() > 0:
            dominant[t] = float((periods[mask] * pwr[mask]).sum() / pwr[mask].sum())
    return filt, dominant
