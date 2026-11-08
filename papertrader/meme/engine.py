"""Memecoin paper engine. Decisions on step t fill at step t+1 with worse prices.
Assumes any position can go to zero, so positions are small and exposure is capped."""
from collections import Counter
from dataclasses import dataclass

from ..ledger import Ledger
from . import strategy


@dataclass
class Pos:
    addr: str
    sym: str
    qty: float
    qty0: float
    entry_price: float
    entry_ts: int
    notional: float
    fee_in: float
    entry_liq: float
    peak: float
    bars: int = 0
    half_sold: bool = False
    pnl: float = 0.0


class MemeRisk:
    def __init__(self, cfg):
        self.cfg = cfg
        self.peak = cfg.start_equity
        self.day = None
        self.day_start = cfg.start_equity
        self.entries_today = 0
        self.consec = 0
        self.pause_until = 0
        self.halted = None
        self.killed = False

    def on_step(self, ts, eq):
        day = ts // 86400
        if day != self.day:
            self.day, self.day_start, self.entries_today = day, eq, 0
        self.peak = max(self.peak, eq)
        dd = 1 - eq / self.peak
        if dd >= self.cfg.dd_kill and not self.killed:
            self.killed, self.halted = True, f"KILL SWITCH: drawdown {dd:.1%}"
        elif dd >= self.cfg.dd_stop and not self.halted:
            self.halted = f"HALT: drawdown {dd:.1%}, needs review"

    def closed(self, ts, pnl):
        if pnl < 0:
            self.consec += 1
            if self.consec >= self.cfg.max_consec_losses:
                self.pause_until, self.consec = ts + self.cfg.pause_hours * 3600, 0
        else:
            self.consec = 0

    def size(self, ts, eq, cash, positions):
        c = self.cfg
        if self.halted:
            return 0.0, self.halted
        if ts < self.pause_until:
            return 0.0, "paused after losses"
        if len(positions) >= c.max_positions:
            return 0.0, "max positions"
        if self.entries_today >= c.max_entries_per_day:
            return 0.0, "max entries per day"
        if eq / self.day_start - 1 <= -c.daily_loss_limit:
            return 0.0, "daily loss limit"
        mult = 0.5 if 1 - eq / self.peak >= c.dd_halve else 1.0
        n = eq * c.pos_frac * mult
        exposure = sum(p.notional * p.qty / p.qty0 for p in positions.values())
        n = min(n, eq * c.max_exposure - exposure, cash / (1 + c.fee) - c.gas)
        return (n, "ok") if n >= 1.0 else (0.0, "exposure cap / too small")


class MemeEngine:
    def __init__(self, cfg, ledger=None):
        self.cfg, self.ledger = cfg, ledger or Ledger()
        self.risk = MemeRisk(cfg)
        self.cash = cfg.start_equity
        self.pos, self.orders, self.last, self.traded = {}, [], {}, set()
        self.stats = Counter()
        self.max_exposure_seen = 0.0

    def _slip(self, size, liq):
        return self.cfg.slip_base + self.cfg.impact_k * size / max(liq, 1.0)

    def equity(self):
        return self.cash + sum(p.qty * self.last[p.addr].price for p in self.pos.values())

    def _record(self, p, ts, qty, fill, fee, reason):
        frac = qty / p.qty0
        gross = qty * fill
        net = (gross - fee) - p.notional * frac - p.fee_in * frac
        self.ledger.trade(p.sym, p.entry_ts, ts, p.entry_price, fill, p.notional * frac,
                          p.fee_in * frac + fee, net, net / (p.notional * frac), reason)
        p.pnl += net
        return net

    def _sell(self, p, qty, ts, snap, can_sell, reason):
        qty = min(qty, p.qty)
        if not can_sell(p.addr):                       # honeypot: cannot exit, total loss
            self.stats["honeypot_stuck"] += 1
            net = self._record(p, ts, qty, 0.0, 0.0, "honeypot: sell failed")
            p.qty -= qty
        else:
            fill = snap.price * (1 - self._slip(qty * snap.price, snap.liq))
            fee = qty * fill * self.cfg.fee + self.cfg.gas
            self.cash += qty * fill - fee
            net = self._record(p, ts, qty, fill, fee, reason)
            p.qty -= qty
        if p.qty <= 1e-12:
            self.risk.closed(ts, p.pnl)
            del self.pos[p.addr]

    def on_step(self, ts, snaps, safety_fn, can_sell=lambda a: True):
        cfg = self.cfg
        # 1. fill orders queued last step
        queued, self.orders = self.orders, []
        for kind, addr, arg in queued:
            snap = snaps.get(addr) or self.last.get(addr)
            if snap is None:
                continue
            if kind == "sell" and addr in self.pos:
                qty = self.pos[addr].qty * arg
                self._sell(self.pos[addr], qty, ts, snap, can_sell, self._why.get(addr, "exit"))
            elif kind == "buy" and addr in snaps:
                self._fill_buy(addr, snaps[addr], arg, ts)
        self._why = {}

        # 2. update marks
        for a, s in snaps.items():
            self.last[a] = s
        for p in self.pos.values():
            p.bars += 1
            p.peak = max(p.peak, self.last[p.addr].price)
        eq = self.equity()
        self.risk.on_step(ts, eq)
        exposure = sum(p.qty * self.last[p.addr].price for p in self.pos.values()) / max(eq, 1e-9)
        self.max_exposure_seen = max(self.max_exposure_seen, exposure)
        self.ledger.equity(ts, eq, self.cash, len(self.pos))
        self._why = {}

        # 3. exits (fill next step)
        for p in list(self.pos.values()):
            s = self.last[p.addr]
            frac, why = 0.0, None
            if self.risk.killed:
                frac, why = 1.0, "kill switch"
            elif s.liq < cfg.liq_exit_frac * p.entry_liq:
                frac, why = 1.0, "liquidity collapse"
            elif s.price <= p.entry_price * (1 - cfg.stop_loss):
                frac, why = 1.0, "stop"
            elif p.peak >= p.entry_price * cfg.trail_arm_mult and s.price <= p.peak * (1 - cfg.trail_frac):
                frac, why = 1.0, "trailing stop"
            elif not p.half_sold and s.price >= p.entry_price * cfg.take_profit_mult:
                frac, why, p.half_sold = 0.5, "take profit (half)", True
            elif p.bars >= cfg.time_stop_bars and s.price < p.entry_price * (1 + cfg.time_stop_min_gain):
                frac, why = 1.0, "time stop"
            if why:
                self.orders.append(("sell", p.addr, frac))
                self._why[p.addr] = why

        # 4. new entries (fill next step)
        if self.risk.halted:
            return eq
        for a, s in snaps.items():
            if a in self.pos or a in self.traded:
                continue
            ok, why = strategy.entry_ok(s, cfg)
            if not ok:
                continue
            sf_ok, sf_why = strategy.safety_ok(safety_fn(a), cfg)
            if not sf_ok:
                self.stats["rejected: " + sf_why] += 1
                continue
            self.ledger.decision(ts, s.sym, "signal", f"price {s.price:.6g} liq {s.liq:.0f}")
            self.stats["signals"] += 1
            self.orders.append(("buy", a, s.price))
        return eq

    def _fill_buy(self, addr, snap, signal_price, ts):
        cfg = self.cfg
        if snap.price > signal_price * (1 + cfg.max_run_vs_signal):
            self.stats["skipped: ran away"] += 1
            return
        n, why = self.risk.size(ts, self.equity(), self.cash, self.pos)
        if n <= 0:
            self.stats["vetoed: " + why] += 1
            self.ledger.decision(ts, snap.sym, "veto", why)
            return
        fill = snap.price * (1 + self._slip(n, snap.liq))
        fee = n * cfg.fee + cfg.gas
        self.cash -= n + fee
        self.pos[addr] = Pos(addr, snap.sym, n / fill, n / fill, fill, ts, n, fee, snap.liq, snap.price)
        self.traded.add(addr)
        self.risk.entries_today += 1
        self.ledger.decision(ts, snap.sym, "entry", f"notional {n:.2f} fill {fill:.6g}")
