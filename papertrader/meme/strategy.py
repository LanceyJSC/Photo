"""Signal + safety agents for memecoins. Fails closed: unknown safety data = reject."""


def safety_ok(sf, cfg):
    if sf is None:
        return False, "no safety data"
    if sf.mint_revoked is not True:
        return False, "mint authority not revoked/unknown"
    if sf.freeze_revoked is not True:
        return False, "freeze authority not revoked/unknown"
    if sf.top10_pct is None or sf.top10_pct > cfg.max_top10_pct:
        return False, "top-10 holders too concentrated/unknown"
    if sf.lp_locked_pct is None or sf.lp_locked_pct < cfg.min_lp_locked_pct:
        return False, "liquidity not locked/unknown"
    if sf.sell_sim_ok is not True:
        return False, "simulated sell failed/unknown (honeypot risk)"
    return True, "ok"


def entry_ok(s, cfg):
    """Momentum on a young, liquid, actively traded token that has not already gone vertical."""
    if not (cfg.min_age_min <= s.age_min <= cfg.max_age_min):
        return False, "age"
    if s.liq < cfg.min_liq:
        return False, "liquidity"
    if s.vol5m < cfg.min_vol5m or s.buys5m + s.sells5m < cfg.min_txns:
        return False, "volume"
    if s.buys5m < cfg.min_buy_sell * max(s.sells5m, 1):
        return False, "buy/sell ratio"
    if not (cfg.min_chg1h <= s.chg1h <= cfg.max_chg1h) or s.chg5m <= 0:
        return False, "momentum window"
    return True, "ok"
