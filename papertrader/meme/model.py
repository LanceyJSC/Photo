from collections import namedtuple

# One observation of a token at one moment. liq/vol in USD-equivalent units.
Snap = namedtuple("Snap", "ts addr sym price liq vol5m buys5m sells5m chg5m chg1h age_min")
# Any field None = unknown. Unknown is treated as FAIL (fail closed).
Safety = namedtuple("Safety", "mint_revoked freeze_revoked top10_pct lp_locked_pct sell_sim_ok")
