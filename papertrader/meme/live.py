"""Live feed: DexScreener (market data) + RugCheck (safety). checked against real responses on 2026-11-09 (field names confirmed, a handful of tokens).\nRe-run `papertrader meme-check` if results look odd; the APIs can change. Safety fails closed."""
import json
import time
import urllib.request

from .model import Safety, Snap

DEX = "https://api.dexscreener.com"
RUG = "https://api.rugcheck.xyz/v1"


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "papertrader/0.1", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def parse_pair(p, now):
    """DexScreener pair -> Snap, or None if fields are missing."""
    try:
        tx = p["txns"]["m5"]
        created = p.get("pairCreatedAt")
        return Snap(int(now), p["baseToken"]["address"], p["baseToken"]["symbol"], float(p["priceUsd"]),
                    float(p["liquidity"]["usd"]), float(p["volume"]["m5"]), int(tx["buys"]), int(tx["sells"]),
                    float(p["priceChange"]["m5"]) / 100.0, float(p["priceChange"]["h1"]) / 100.0,
                    (now - created / 1000.0) / 60.0 if created else -1.0)
    except (KeyError, TypeError, ValueError):
        return None


def parse_rugcheck(rep):
    """RugCheck FULL report (/tokens/{mint}/report) -> Safety. Verified against real responses
    on 2026-11-09. Anything missing stays None (= fail closed).
    NOTE: sell_sim_ok is NOT a real sell simulation. It is True only when RugCheck shows no
    sell-blocking indicator (rugged flag, any 'danger' risk, transfer fee/hook/delegate, etc.)."""
    none = Safety(None, None, None, None, None)
    if not isinstance(rep, dict) or "risks" not in rep or "mintAuthority" not in rep:
        return none
    mint_ok = rep["mintAuthority"] is None
    freeze_ok = rep.get("freezeAuthority", "missing") is None

    known = rep.get("knownAccounts") or {}
    pooled = {a for a, v in known.items() if v.get("type") in ("AMM", "LOCKER")}
    holders = [h for h in (rep.get("topHolders") or [])
               if h.get("owner") not in pooled and h.get("address") not in pooled]
    top10 = sum(h.get("pct", 0.0) for h in holders[:10]) if rep.get("topHolders") else None

    best, best_liq = None, -1.0
    for m in rep.get("markets") or []:
        lp = m.get("lp") or {}
        liq = (lp.get("quoteUSD") or 0.0) + (lp.get("baseUSD") or 0.0)
        if liq > best_liq and lp.get("lpLockedPct") is not None:
            best, best_liq = lp["lpLockedPct"], liq

    ext = rep.get("token_extensions") or {}
    blocked = (rep.get("rugged") is True
               or any(r.get("level") == "danger" for r in rep["risks"])
               or ((rep.get("transferFee") or {}).get("pct") or 0) > 0
               or any(ext.get(k) for k in ("transferFeeConfig", "permanentDelegate", "transferHook",
                                            "pausableConfig", "defaultAccountState"))
               or ext.get("nonTransferable") is True)
    return Safety(mint_ok, freeze_ok, top10, best, not blocked)


class LiveFeed:
    def __init__(self, max_track=150):
        self.tracked, self.max_track, self.safety_cache = {}, max_track, {}

    def discover(self):
        for url in (f"{DEX}/token-profiles/latest/v1", f"{DEX}/token-boosts/latest/v1"):
            try:
                for t in _get(url):
                    if t.get("chainId") == "solana":
                        self.tracked.setdefault(t["tokenAddress"], time.time())
            except Exception as e:                       # noqa: BLE001 - feed must not crash the loop
                print("discover failed:", e)
        cutoff = time.time() - 86400
        self.tracked = dict(sorted(((a, t) for a, t in self.tracked.items() if t > cutoff),
                                   key=lambda kv: -kv[1])[: self.max_track])

    def snaps(self):
        now, out, addrs = time.time(), {}, list(self.tracked)
        for i in range(0, len(addrs), 30):
            try:
                for p in _get(f"{DEX}/latest/dex/tokens/{','.join(addrs[i:i + 30])}").get("pairs") or []:
                    if p.get("chainId") != "solana":
                        continue
                    s = parse_pair(p, now)
                    if s and (s.addr not in out or s.liq > out[s.addr].liq):
                        out[s.addr] = s
            except Exception as e:                       # noqa: BLE001
                print("pairs failed:", e)
        return out

    def safety(self, addr):
        if addr not in self.safety_cache:
            try:
                self.safety_cache[addr] = parse_rugcheck(_get(f"{RUG}/tokens/{addr}/report"))
            except Exception:                            # noqa: BLE001 - unknown = fail closed
                self.safety_cache[addr] = Safety(None, None, None, None, None)
        return self.safety_cache[addr]
