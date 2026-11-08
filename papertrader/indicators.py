"""Plain-Python indicators. All functions use only data up to the last item."""


def ema(values, period):
    if not values:
        return []
    k = 2.0 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(out[-1] + k * (v - out[-1]))
    return out


def atr(candles, period):
    """Wilder ATR series, same length as candles."""
    trs = []
    prev_close = None
    for c in candles:
        if prev_close is None:
            tr = c.h - c.l
        else:
            tr = max(c.h - c.l, abs(c.h - prev_close), abs(c.l - prev_close))
        trs.append(tr)
        prev_close = c.c
    out = []
    for i, tr in enumerate(trs):
        if i == 0:
            out.append(tr)
        elif i < period:
            out.append((out[-1] * i + tr) / (i + 1))
        else:
            out.append((out[-1] * (period - 1) + tr) / period)
    return out


def percentile_rank(history, value):
    """Fraction of history values <= value."""
    if not history:
        return 0.5
    return sum(1 for h in history if h <= value) / len(history)
