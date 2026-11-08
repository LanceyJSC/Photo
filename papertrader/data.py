"""Candle feeds: synthetic (for testing the code) and Binance public data (live)."""
import json
import math
import random
import time
import urllib.parse
import urllib.request
from collections import namedtuple

Candle = namedtuple("Candle", "ts o h l c v")  # ts = open time, epoch seconds

BINANCE = "https://data-api.binance.vision/api/v3/klines"
INTERVAL_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}


def fetch_binance(symbol, interval, start_ts, end_ts, timeout=20):
    """Closed candles in [start_ts, end_ts). Paginates 1000 at a time."""
    step = INTERVAL_SECONDS[interval]
    out = []
    cursor = int(start_ts)
    while cursor < end_ts:
        q = urllib.parse.urlencode({
            "symbol": symbol, "interval": interval, "limit": 1000,
            "startTime": cursor * 1000, "endTime": int(end_ts) * 1000})
        with urllib.request.urlopen(f"{BINANCE}?{q}", timeout=timeout) as r:
            rows = json.load(r)
        if not rows:
            break
        for k in rows:
            ts = k[0] // 1000
            # only fully closed candles
            if ts + step <= time.time() and ts < end_ts:
                out.append(Candle(ts, float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])))
        nxt = rows[-1][0] // 1000 + step
        if nxt <= cursor:
            break
        cursor = nxt
        if len(rows) < 1000:
            break
    return out


def synthetic(symbols, bars, seed=1, start_ts=1_700_000_000, step=3600):
    """Regime-switching random walk. ONLY for testing code paths: results on
    synthetic data say nothing about real-market profitability."""
    rng = random.Random(seed)
    base = {"BTCUSDT": 70000.0, "ETHUSDT": 2300.0, "SOLUSDT": 90.0}
    regimes = [(0.00015, 0.004), (-0.00015, 0.006), (0.0, 0.003), (0.0, 0.008)]  # drift, vol per bar
    series = {s: [] for s in symbols}
    price = {s: base.get(s, 100.0) for s in symbols}
    regime = regimes[0]
    left = 0
    for i in range(bars):
        if left <= 0:
            regime = rng.choice(regimes)
            left = rng.randint(100, 600)
        left -= 1
        common = rng.gauss(0, 1)
        for s in symbols:
            z = 0.7 * common + 0.714 * rng.gauss(0, 1)
            drift, vol = regime
            ret = drift + vol * z
            o = price[s]
            c = o * math.exp(ret)
            wick = abs(rng.gauss(0, vol * 0.5))
            h = max(o, c) * (1 + wick)
            l = min(o, c) * (1 - wick)
            series[s].append(Candle(start_ts + i * step, o, h, l, c, rng.uniform(100, 1000)))
            price[s] = c
    return series


def align(series):
    """Keep only timestamps present for every symbol; return sorted ts list and per-symbol dicts."""
    common = None
    for cs in series.values():
        ts = {c.ts for c in cs}
        common = ts if common is None else common & ts
    order = sorted(common or [])
    by = {s: {c.ts: c for c in cs} for s, cs in series.items()}
    return order, by
