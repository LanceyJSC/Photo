from dataclasses import dataclass


@dataclass
class MemeConfig:
    start_equity: float = 100.0
    step_seconds: int = 300

    # costs per side (deliberately pessimistic)
    fee: float = 0.0085          # Phantom swap fee
    slip_base: float = 0.015     # latency / MEV / thin books
    impact_k: float = 2.0        # extra slippage = impact_k * size / liquidity
    gas: float = 0.08            # flat network+priority fee per transaction

    # entry filter
    min_age_min: int = 10
    max_age_min: int = 360
    min_liq: float = 20_000
    min_vol5m: float = 3_000
    min_txns: int = 30
    min_buy_sell: float = 1.3
    min_chg1h: float = 0.10
    max_chg1h: float = 0.80          # do not chase the top
    max_run_vs_signal: float = 0.15  # skip if price ran >15% before our fill

    # safety (all must pass; None fails)
    max_top10_pct: float = 35.0
    min_lp_locked_pct: float = 80.0

    # sizing / limits: assume a position can go to zero, so size small
    pos_frac: float = 0.05
    max_positions: int = 4
    max_exposure: float = 0.20
    max_entries_per_day: int = 12
    daily_loss_limit: float = 0.10
    dd_halve: float = 0.10
    dd_stop: float = 0.20
    dd_kill: float = 0.30
    max_consec_losses: int = 5
    pause_hours: int = 24

    # exits
    stop_loss: float = 0.25          # sell if price <= entry * (1 - stop_loss)
    liq_exit_frac: float = 0.50      # sell if liquidity < 50% of entry liquidity
    take_profit_mult: float = 2.0    # sell half at 2x
    trail_arm_mult: float = 1.5      # trailing stop arms once peak >= 1.5x
    trail_frac: float = 0.30
    time_stop_bars: int = 48         # 4h
    time_stop_min_gain: float = 0.20

    min_trades_for_edge: int = 100
