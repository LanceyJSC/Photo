"""Risk manager: the only component allowed to approve an entry and set its size.
Plain deterministic code; it can veto anything."""


class RiskManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.peak = cfg.start_equity
        self.day = None
        self.week = None
        self.day_start_equity = cfg.start_equity
        self.week_start_equity = cfg.start_equity
        self.consec_losses = 0
        self.pause_until = 0
        self.trades_today = 0
        self.halted = None   # None, or reason string (needs human review to clear)
        self.killed = False

    # --- bookkeeping, called once per closed bar -----------------------------
    def on_bar(self, ts, equity):
        cfg = self.cfg
        day, week = ts // 86400, ts // (86400 * 7)
        if day != self.day:
            self.day, self.day_start_equity, self.trades_today = day, equity, 0
        if week != self.week:
            self.week, self.week_start_equity = week, equity
        self.peak = max(self.peak, equity)
        dd = 1 - equity / self.peak
        if dd >= cfg.dd_kill and not self.killed:
            self.killed = True
            self.halted = f"KILL SWITCH: drawdown {dd:.1%} from peak"
        elif dd >= cfg.dd_stop and not self.halted:
            self.halted = f"HALT: drawdown {dd:.1%} from peak, needs review"

    def on_trade_closed(self, ts, net_pnl):
        if net_pnl < 0:
            self.consec_losses += 1
            if self.consec_losses >= self.cfg.max_consec_losses:
                self.pause_until = ts + self.cfg.pause_hours * 3600
                self.consec_losses = 0
        else:
            self.consec_losses = 0

    # --- entry approval ------------------------------------------------------
    def size_multiplier(self, equity):
        dd = 1 - equity / self.peak
        return 0.5 if dd >= self.cfg.dd_halve else 1.0

    def approve(self, sig, fill_price, ts, equity, cash, positions):
        """Return (notional, reason). notional == 0 means vetoed."""
        cfg = self.cfg
        if self.halted:
            return 0.0, self.halted
        if ts < self.pause_until:
            return 0.0, "paused after consecutive losses"
        if sig.symbol in positions:
            return 0.0, "already in position"
        if len(positions) >= cfg.max_positions:
            return 0.0, "max positions"
        if self.trades_today >= cfg.max_trades_per_day:
            return 0.0, "max trades per day"
        if equity / self.day_start_equity - 1 <= -cfg.daily_loss_limit:
            return 0.0, "daily loss limit"
        if equity / self.week_start_equity - 1 <= -cfg.weekly_loss_limit:
            return 0.0, "weekly loss limit"
        if fill_price <= sig.stop:
            return 0.0, "price already through stop"

        stop_pct = (fill_price - sig.stop) / fill_price
        risk_budget = equity * cfg.risk_per_trade * self.size_multiplier(equity)
        # fees+slippage count as risk, so size against stop distance PLUS costs
        notional = risk_budget / (stop_pct + cfg.round_trip_cost)
        notional = min(notional, equity * cfg.max_notional_frac, cash / (1 + cfg.fee))
        if notional < 1.0:
            return 0.0, "size too small"
        open_risk = sum(p.risk_amount for p in positions.values())
        new_risk = notional * stop_pct
        if open_risk + new_risk > equity * cfg.max_open_risk:
            return 0.0, "max open risk"
        return notional, "approved"

    def note_entry(self):
        self.trades_today += 1
