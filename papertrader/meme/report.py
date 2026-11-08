from collections import Counter


def summarize(eng, cfg):
    trades = eng.ledger.trades()
    curve = eng.ledger.equity_curve()
    final = curve[-1][1] if curve else cfg.start_equity
    peak, mdd = cfg.start_equity, 0.0
    for _, e in curve:
        peak = max(peak, e)
        mdd = max(mdd, 1 - e / peak)
    n = len(trades)
    wins = [t for t in trades if t[7] > 0]
    gw = sum(t[7] for t in wins)
    gl = -sum(t[7] for t in trades if t[7] <= 0)
    by_reason = Counter(t[9] for t in trades)
    return {
        "final": final, "ret": (final / cfg.start_equity - 1) * 100, "mdd": mdd * 100,
        "trades": n, "win": (len(wins) / n * 100) if n else 0.0,
        "avg_ret_on_position": (sum(t[8] for t in trades) / n * 100) if n else 0.0,
        "pf": (gw / gl) if gl else (float("inf") if gw else 0.0),
        "fees": sum(t[6] for t in trades), "reasons": by_reason, "open": len(eng.pos),
        "halted": eng.risk.halted, "stats": eng.stats,
        "max_exposure": eng.max_exposure_seen * 100,
        "edge": ("UNPROVEN: fewer than %d closed trades" % cfg.min_trades_for_edge) if n < cfg.min_trades_for_edge
        else ("net-positive after costs" if sum(t[7] for t in trades) > 0 else "NO EDGE after costs"),
    }


def fmt(r):
    L = [f"Final equity       : {r['final']:.2f} ({r['ret']:+.1f}%)   max drawdown {r['mdd']:.1f}%",
         f"Closed trades      : {r['trades']}  win rate {r['win']:.0f}%  avg return/position {r['avg_ret_on_position']:+.1f}%  profit factor {r['pf']:.2f}",
         f"Fees+gas paid      : {r['fees']:.2f}   peak exposure {r['max_exposure']:.0f}% of equity at market value (cap applies to cost)   open now {r['open']}"]
    if r["reasons"]:
        L.append("Exits              : " + ", ".join(f"{k} x{v}" for k, v in r["reasons"].most_common()))
    rej = {k: v for k, v in r["stats"].items() if k.startswith(("rejected", "vetoed", "skipped"))}
    if rej:
        L.append("Blocked            : " + ", ".join(f"{k} x{v}" for k, v in sorted(rej.items(), key=lambda kv: -kv[1])))
    if r["halted"]:
        L.append(f"HALTED             : {r['halted']}")
    L.append(f"Edge status        : {r['edge']}")
    return "\n".join(L)
