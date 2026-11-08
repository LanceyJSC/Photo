"""Safety agent: data sanity, liquidity hours, scheduled-event blackouts."""


def bar_is_sane(prev_close, candle, cfg):
    if candle.c <= 0 or candle.h < candle.l:
        return False
    if prev_close and abs(candle.c / prev_close - 1) > cfg.max_bar_move:
        return False
    return True


def entry_allowed(symbol, ts, cfg):
    """Check the timestamp the order would fill at. Returns (ok, reason)."""
    hour = (ts // 3600) % 24
    lo, hi = cfg.entry_hours
    if not (lo <= hour < hi):
        return False, f"outside entry hours (hour {hour} UTC)"
    for sym, start, end in cfg.blackouts:
        if sym in ("*", symbol) and start <= ts < end:
            return False, "scheduled-event blackout"
    return True, "ok"
