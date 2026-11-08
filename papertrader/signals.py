"""Signal agent: one slow trend/breakout rule + one volatility measure. Long-only.
Uses only candles up to and including the latest closed bar (no lookahead)."""
from collections import namedtuple

from .indicators import atr, ema, percentile_rank

Signal = namedtuple("Signal", "symbol ts ref_price stop stop_pct atr reason")


def evaluate(symbol, candles, cfg):
    """Return (Signal or None, reason string for the decision log)."""
    n = len(candles)
    need = cfg.ema_slow + cfg.slope_lookback + 5
    if n < need:
        return None, "warmup"
    closes = [c.c for c in candles]
    fast = ema(closes, cfg.ema_fast)
    slow = ema(closes, cfg.ema_slow)
    a = atr(candles, cfg.atr_period)
    px = closes[-1]

    if not (px > slow[-1] and fast[-1] > slow[-1]):
        return None, "no uptrend"
    if not slow[-1] > slow[-1 - cfg.slope_lookback]:
        return None, "slow EMA not rising"
    prior_high = max(c.h for c in candles[-1 - cfg.donchian:-1])
    if not px > prior_high:
        return None, "no breakout"

    atr_pct = a[-1] / px
    hist = [a[i] / closes[i] for i in range(max(0, n - cfg.vol_lookback), n - 1)]
    rank = percentile_rank(hist, atr_pct)
    if rank < cfg.vol_pct_low:
        return None, f"volatility too low (pct {rank:.2f})"
    if rank > cfg.vol_pct_high:
        return None, f"volatility too high (pct {rank:.2f})"

    stop = px - cfg.atr_stop_mult * a[-1]
    stop_pct = (px - stop) / px
    # economics gate: reward (min_rr x risk) must clear cost_multiple x round-trip cost
    if cfg.min_rr * stop_pct < cfg.cost_multiple * cfg.round_trip_cost:
        return None, (f"move too small vs costs (target {cfg.min_rr * stop_pct:.2%} < "
                      f"{cfg.cost_multiple * cfg.round_trip_cost:.2%})")
    return Signal(symbol, candles[-1].ts, px, stop, stop_pct, a[-1],
                  f"breakout above {cfg.donchian}-bar high in uptrend"), "signal"
