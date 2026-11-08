"""Synthetic memecoin market. EVERY number here is my assumption, not measured data.
It exists to test the code and to show how sensitive results are to the assumed
share of 'runners'. It cannot tell you whether real memecoins are profitable."""
import math
import random
from collections import defaultdict

from .model import Safety, Snap

FATES = {"bleed": 0.49, "rug": 0.22, "honeypot": 0.08, "pump_fade": 0.17, "runner": 0.04}


def _fates_with_runner(r):
    others = {k: v for k, v in FATES.items() if k != "runner"}
    scale = (1 - r) / sum(others.values())
    out = {k: v * scale for k, v in others.items()}
    out["runner"] = r
    return out


class Token:
    __slots__ = ("addr", "sym", "launch", "fate", "bars", "safety", "honeypot")


def _gen(rng, idx, launch, fate, nbars, informative=True):
    liq = max(3000.0, rng.lognormvariate(math.log(25000), 0.8))
    price, hist, bars = 1.0, [1.0], []
    rug_bar = rng.randint(6, 60)
    pump_len, run_len, hp_len = rng.randint(10, 25), rng.randint(40, 120), rng.randint(20, 50)
    rugged = False
    burst0 = rng.randint(6, 200)   # control market: when a runner/pump bursts, unpredictably
    for b in range(nbars):
        if not informative and b >= 6:
            # CONTROL: early momentum says nothing. All tokens bleed, except an unpredictable burst.
            drift, vol = -0.006, 0.04
            if fate == "runner" and burst0 <= b < burst0 + 10:
                drift = 0.14
            elif fate == "pump_fade" and burst0 <= b < burst0 + 6:
                drift = 0.16
        elif b < 6:
            drift, vol = 0.015, 0.06
        elif fate == "bleed":
            drift, vol = -0.006, 0.04
        elif fate == "rug":
            drift, vol = 0.004, 0.05
        elif fate == "honeypot":
            drift, vol = (0.003, 0.04) if b < hp_len else (-0.01, 0.04)
        elif fate == "pump_fade":
            drift, vol = (0.04, 0.06) if b < 6 + pump_len else (-0.025, 0.05)
        else:
            drift, vol = (0.025, 0.06) if b < 6 + run_len else (-0.01, 0.05)
        ret = rng.gauss(drift, vol)
        if fate == "rug" and b == rug_bar:
            ret, liq, rugged = math.log(0.03), liq * 0.03, True
        elif rugged:
            ret = rng.gauss(0, 0.02)
        else:
            liq *= math.exp(0.3 * ret)
        price = max(price * math.exp(ret), 1e-9)
        hist.append(price)
        vol5 = liq * (0.08 + 2.5 * abs(ret)) * rng.uniform(0.5, 1.5) * (0.1 if rugged else 1.0)
        ntx = max(2, int(vol5 / 120))
        share = min(0.9, max(0.1, 0.5 + ret * 4 + rng.gauss(0, 0.05)))
        buys = int(ntx * share)
        h12 = hist[-13] if len(hist) > 12 else hist[0]
        bars.append((price, liq, vol5, buys, ntx - buys, math.exp(ret) - 1, price / h12 - 1))
    t = Token()
    t.addr, t.sym, t.launch, t.fate, t.bars = f"T{idx}", f"MEME{idx}", launch, fate, bars
    t.honeypot = fate == "honeypot"
    bad = fate in ("rug", "honeypot")
    t.safety = Safety(
        mint_revoked=rng.random() < (0.5 if fate == "rug" else 0.85),
        freeze_revoked=rng.random() < (0.6 if fate == "rug" else 0.9),
        top10_pct=min(95, max(5, rng.gauss(45 if fate == "rug" else 20, 12 if fate == "rug" else 8))),
        lp_locked_pct=100.0 if rng.random() < (0.3 if fate == "rug" else 0.7) else rng.uniform(0, 60),
        sell_sim_ok=not (t.honeypot and rng.random() < 0.85),  # detector misses 15% of honeypots
    )
    return t


class World:
    def __init__(self, steps, seed=1, rate=0.5, runner_rate=None, nbars=288, step_seconds=300, t0=1_700_000_000, informative=True):
        self.rng = random.Random(seed)
        self.steps, self.step_seconds, self.t0 = steps, step_seconds, t0
        fates = _fates_with_runner(runner_rate) if runner_rate is not None else FATES
        names, weights = list(fates), list(fates.values())
        self.tokens, self.by_step = {}, defaultdict(list)
        idx = 0
        for step in range(steps):
            for _ in range(self._poisson(rate)):
                tok = _gen(self.rng, idx, step, self.rng.choices(names, weights)[0], nbars, informative)
                self.tokens[tok.addr] = tok
                for b in range(nbars):
                    self.by_step[step + b].append((tok, b))
                idx += 1

    def _poisson(self, lam):
        l, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= self.rng.random()
            if p <= l:
                return k
            k += 1

    def ts(self, step):
        return self.t0 + step * self.step_seconds

    def snaps(self, step):
        out = {}
        for tok, b in self.by_step.get(step, ()):
            pr, liq, v, bu, se, c5, c1 = tok.bars[b]
            out[tok.addr] = Snap(self.ts(step), tok.addr, tok.sym, pr, liq, v, bu, se, c5, c1,
                                 b * self.step_seconds / 60)
        return out

    def safety(self, addr):
        return self.tokens[addr].safety

    def can_sell(self, addr):
        return not self.tokens[addr].honeypot

    def fate(self, addr):
        return self.tokens[addr].fate
