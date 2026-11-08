"""Live feed: DexScreener (market data) + RugCheck (safety). NOT TESTED against the live
APIs from the build sandbox (hosts were blocked). Field names below come from my memory of
the public docs; parse_* are unit-tested only against fixtures I wrote, so verify them with
`papertrader meme-check` before trusting anything. Safety fails closed on any doubt."""
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
    """RugCheck summary -> Safety. Anything missing stays None (= fail closed)."""
    if not isinstance(rep, dict) or "risks" not in rep:
        return Safety(None, None, None, None, None)
    names = [(r.get("name", ""), r.get("level", "")) for r in rep["risks"]]
    danger = any(lvl == "danger" for _, lvl in names)
    has = lambda s: any(s in n.lower() for n, _ in names)
    mint_ok = not has("mint authority")
    freeze_ok = not has("freeze authority")
    top10 = 50.0 if has("top 10") or has("high ownership") else 10.0   # coarse: flag only
    lp_ok = not has("liquidity") and not has("lp unlocked")
    return Safety(mint_ok, freeze_ok, top10, 100.0 if lp_ok else 0.0, not danger)


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
                self.safety_cache[addr] = parse_rugcheck(_get(f"{RUG}/tokens/{addr}/report/summary"))
            except Exception:                            # noqa: BLE001 - unknown = fail closed
                self.safety_cache[addr] = Safety(None, None, None, None, None)
        return self.safety_cache[addr]
