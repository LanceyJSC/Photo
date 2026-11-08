"""All tunable rules in one place. Defaults come from the research round."""
from dataclasses import dataclass, field


@dataclass
class Config:
    # account
    start_equity: float = 100.0          # GBP-equivalent, fake money
    symbols: tuple = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    interval: str = "1h"
    interval_seconds: int = 3600

    # costs (per side). Phantom swap fee ~0.85% + assumed slippage.
    fee_bps: float = 85.0
    slippage_bps: float = 10.0

    # signal (slow trend + volatility, long-only spot, no leverage)
    ema_fast: int = 50
    ema_slow: int = 200
    slope_lookback: int = 24
    donchian: int = 48
    atr_period: int = 14
    atr_stop_mult: float = 2.5
    vol_lookback: int = 500
    vol_pct_low: float = 0.20            # skip dead markets
    vol_pct_high: float = 0.97           # skip chaotic markets
    cooldown_bars: int = 24              # after a stop-out on that symbol

    # economics gate: target move must be >= cost_multiple * round-trip cost
    cost_multiple: float = 3.0
    min_rr: float = 2.0

    # risk
    risk_per_trade: float = 0.01
    max_notional_frac: float = 0.33
    max_open_risk: float = 0.03
    max_positions: int = 3
    max_trades_per_day: int = 2
    daily_loss_limit: float = 0.03
    weekly_loss_limit: float = 0.06
    dd_halve: float = 0.10
    dd_stop: float = 0.20
    dd_kill: float = 0.30
    max_consec_losses: int = 4
    pause_hours: int = 24

    # safety filters (UTC)
    entry_hours: tuple = (12, 22)        # US-hours liquidity; entry hour in [12,22)
    # (symbol or "*", start_ts, end_ts) in epoch seconds: CPI/FOMC/unlocks
    blackouts: list = field(default_factory=list)
    max_bar_move: float = 0.25           # >25% in one bar = bad data, halt entries

    # edge gate: report says "unproven" until this many closed trades
    min_trades_for_edge: int = 100

    @property
    def fee(self) -> float:
        return self.fee_bps / 10000.0

    @property
    def slip(self) -> float:
        return self.slippage_bps / 10000.0

    @property
    def round_trip_cost(self) -> float:
        """Approximate fraction of notional lost to fees+slippage in and out."""
        return 2 * (self.fee + self.slip)
