"""Orchestrator + paper executor. Signals are computed on a closed bar and the
order fills at the NEXT bar's open, with fees and slippage. No real orders, no keys."""
from dataclasses import dataclass

from . import data as datamod
from . import safety, signals
from .indicators import atr
from .ledger import Ledger
from .risk import RiskManager


@dataclass
class Position:
    symbol: str
    qty: float
    entry_price: float
    entry_ts: int
    stop: float
    notional: float
    risk_amount: float
    entry_fee: float
    highest_close: float


class Engine:
    WINDOW = 1000   # bars fed to indicators; plenty for the 200-EMA and 500-bar vol rank

    def __init__(self, cfg, ledger=None):
        self.cfg = cfg
        self.ledger = ledger or Ledger()
        self.risk = RiskManager(cfg)
        self.cash = cfg.start_equity
        self.positions = {}
        self.pending = []          # signals to fill at next open
        self.cooldown = {}         # symbol -> ts until which re-entry is blocked
        self.history = {}          # symbol -> list of closed candles
        self.prev_close = {}
        self.bad_data = False
        self.flatten = False

    # --- accounting ------------------------------------------------------------
    def equity(self, closes):
        return self.cash + sum(p.qty * closes.get(p.symbol, p.entry_price)
                               for p in self.positions.values())

    def _sell(self, pos, px, ts, reason):
        cfg = self.cfg
        fill = px * (1 - cfg.slip)
        gross = pos.qty * fill
        fee = gross * cfg.fee
        self.cash += gross - fee
        fees = pos.entry_fee + fee
        net = (gross - fee) - pos.notional - pos.entry_fee
        r = net / pos.risk_amount if pos.risk_amount else 0.0
        self.ledger.trade(pos.symbol, pos.entry_ts, ts, pos.entry_price, fill,
                          pos.notional, fees, net, r, reason)
        self.risk.on_trade_closed(ts, net)
        if reason == "stop":
            self.cooldown[pos.symbol] = ts + self.cfg.cooldown_bars * self.cfg.interval_seconds
        del self.positions[pos.symbol]

    def _buy(self, sig, candle, ts, equity):
        cfg = self.cfg
        fill = candle.o * (1 + cfg.slip)
        notional, why = self.risk.approve(sig, fill, ts, equity, self.cash, self.positions)
        if notional <= 0:
            self.ledger.decision(ts, sig.symbol, "veto", why)
            return
        fee = notional * cfg.fee
        stop_pct = (fill - sig.stop) / fill
        self.cash -= notional + fee
        self.positions[sig.symbol] = Position(
            sig.symbol, notional / fill, fill, ts, sig.stop, notional,
            notional * stop_pct, fee, fill)
        self.risk.note_entry()
        self.ledger.decision(ts, sig.symbol, "entry",
                             f"notional {notional:.2f} fill {fill:.4f} stop {sig.stop:.4f}")

    # --- one closed bar for all symbols ----------------------------------------
    def on_bar(self, ts, candles):
        cfg = self.cfg
        step = cfg.interval_seconds

        # 0. data sanity
        for s, c in candles.items():
            if not safety.bar_is_sane(self.prev_close.get(s), c, cfg):
                self.bad_data = True
                self.ledger.decision(ts, s, "halt", "insane bar, skipping entries this bar")
        sane = not self.bad_data
        self.bad_data = False

        closes_prev = {s: self.prev_close.get(s, c.o) for s, c in candles.items()}

        # 1. flatten if the kill switch fired last bar
        if self.flatten:
            for pos in list(self.positions.values()):
                self._sell(pos, candles[pos.symbol].o, ts, "kill switch")
            self.flatten = False

        # 2. fill pending entries at this bar's open
        eq_open = self.equity({s: c.o for s, c in candles.items()})
        pend, self.pending = self.pending, []
        if sane:
            for sig in pend:
                self._buy(sig, candles[sig.symbol], ts, eq_open)

        # 3. stops against this bar (stop checked before trailing update)
        for pos in list(self.positions.values()):
            c = candles[pos.symbol]
            if c.l <= pos.stop:
                self._sell(pos, min(pos.stop, c.o), ts, "stop")

        # 4. mark to market, update history, trailing stops
        closes = {s: c.c for s, c in candles.items()}
        for s, c in candles.items():
            self.history.setdefault(s, []).append(c)
            self.prev_close[s] = c.c
        for pos in self.positions.values():
            hist = self.history[pos.symbol]
            pos.highest_close = max(pos.highest_close, closes[pos.symbol])
            a = atr(hist[-60:], cfg.atr_period)[-1]
            pos.stop = max(pos.stop, pos.highest_close - cfg.atr_stop_mult * a)
        eq = self.equity(closes)
        self.risk.on_bar(ts, eq)
        self.ledger.equity(ts, eq, self.cash, len(self.positions))
        if self.risk.killed and self.positions:
            self.flatten = True

        # 5. look for new signals; they fill at next open
        nxt = ts + step
        if sane and not self.risk.halted:
            for s in cfg.symbols:
                if s in self.positions or s not in self.history:
                    continue
                if self.cooldown.get(s, 0) > nxt:
                    continue
                ok, why = safety.entry_allowed(s, nxt, cfg)
                sig, reason = signals.evaluate(s, self.history[s][-self.WINDOW:], cfg)
                if sig is None:
                    if reason.startswith("move too small"):
                        self.ledger.decision(ts, s, "skip", reason)
                    continue
                if not ok:
                    self.ledger.decision(ts, s, "skip", f"signal but {why}")
                    continue
                self.ledger.decision(ts, s, "signal", sig.reason)
                self.pending.append(sig)
        return eq

    # --- run over data ----------------------------------------------------------
    def run(self, series):
        order, by = datamod.align({s: series[s] for s in self.cfg.symbols})
        for ts in order:
            self.on_bar(ts, {s: by[s][ts] for s in self.cfg.symbols})
        # mark any still-open position to market in the report (not force-closed)
        return report(self, series, order)


def report(engine, series, order):
    cfg = engine.cfg
    trades = engine.ledger.trades()
    curve = engine.ledger.equity_curve()
    final = curve[-1][1] if curve else cfg.start_equity
    peak, max_dd = cfg.start_equity, 0.0
    for _, e in curve:
        peak = max(peak, e)
        max_dd = max(max_dd, 1 - e / peak)
    wins = [t for t in trades if t[7] > 0]
    losses = [t for t in trades if t[7] <= 0]
    gross_win = sum(t[7] for t in wins)
    gross_loss = -sum(t[7] for t in losses)
    n = len(trades)
    out = {
        "start_equity": cfg.start_equity,
        "final_equity": final,
        "return_pct": (final / cfg.start_equity - 1) * 100,
        "max_drawdown_pct": max_dd * 100,
        "trades": n,
        "win_rate_pct": (len(wins) / n * 100) if n else 0.0,
        "avg_R": (sum(t[8] for t in trades) / n) if n else 0.0,
        "profit_factor": (gross_win / gross_loss) if gross_loss else float("inf") if gross_win else 0.0,
        "fees_paid": sum(t[6] for t in trades),
        "open_positions": len(engine.positions),
        "halted": engine.risk.halted,
    }
    if order and cfg.symbols:
        s0 = cfg.symbols[0]
        cs = {c.ts: c for c in series[s0]}
        out["buy_hold_first_symbol_pct"] = (cs[order[-1]].c / cs[order[0]].o - 1) * 100
    out["edge_status"] = (
        "UNPROVEN: fewer than %d closed trades" % cfg.min_trades_for_edge
        if n < cfg.min_trades_for_edge else
        ("net-positive after costs" if out["avg_R"] > 0 else "NO EDGE after costs"))
    return out


def format_report(r):
    lines = [
        f"Start equity      : {r['start_equity']:.2f}",
        f"Final equity      : {r['final_equity']:.2f}  ({r['return_pct']:+.2f}%)",
        f"Max drawdown      : {r['max_drawdown_pct']:.2f}%",
        f"Closed trades     : {r['trades']}   win rate {r['win_rate_pct']:.1f}%",
        f"Avg R per trade   : {r['avg_R']:+.3f}   profit factor {r['profit_factor']:.2f}",
        f"Fees+slippage paid: {r['fees_paid']:.2f}",
        f"Open positions    : {r['open_positions']}",
    ]
    if "buy_hold_first_symbol_pct" in r:
        lines.append(f"Buy & hold (first symbol): {r['buy_hold_first_symbol_pct']:+.2f}%")
    if r["halted"]:
        lines.append(f"HALTED            : {r['halted']}")
    lines.append(f"Edge status       : {r['edge_status']}")
    return "\n".join(lines)
