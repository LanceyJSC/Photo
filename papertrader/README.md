# papertrader: paper-trading system (fake money only)

There is **no code path that places a real order or reads a wallet key**. It simulates
a £100 account on BTC, ETH and SOL spot using the rules from the research phase.

## Run (stdlib only, Python 3.10+)

    python3 -m papertrader backtest --synthetic --days 180   # tests the code, proves nothing
    python3 -m papertrader backtest --days 365                # real history (Binance public data)
    python3 -m papertrader paper --since 2026-11-09 --loop 3600   # forward paper trading
    python3 -m unittest papertrader.tests.test_papertrader

Live data comes from Binance's public market-data endpoint (no account, no key).
It is blocked in some sandboxes; run it on your own machine.

## The agents (modules)

| Module | Role |
|---|---|
| `data.py` | Data agent: candles (live Binance or synthetic for tests) |
| `signals.py` | Signal agent: slow trend + 48-bar breakout + volatility-percentile filter, long-only |
| `safety.py` | Safety agent: bad-data check, US-hours entry window, event/unlock blackouts |
| `risk.py` | Risk manager: sizes every trade and can veto anything |
| `engine.py` | Paper executor: fills at the NEXT bar's open with 0.85% fee + 0.10% slippage per side |
| `ledger.py` | Logger: SQLite audit trail of every signal, veto, trade and equity point |

## Rules enforced (all in `config.py`)

- Risk <= 1% of equity per trade, sized on stop distance **plus** round-trip costs; every trade has a stop
- Notional <= 33% of equity, open risk <= 3%, <= 3 positions, <= 2 entries/day, no leverage, no shorting
- A trade is skipped unless 2x its risk is >= 3x the round-trip cost (the move must be worth the fees)
- Daily loss limit 3%, weekly 6%; drawdown from peak: -10% halves size, -20% halts, -30% kill switch (flatten)
- 4 losses in a row pauses 24h; 24-bar cooldown after a stop-out; trailing ATR stop lets winners run
- Never averages down or widens a stop

## How to read the result

The report says **UNPROVEN** until 100+ closed trades. Treat any strategy as unreal
unless it is net-positive per trade after costs, survives doubling `fee_bps`, and holds on
data it was not tuned on. Do not tune the parameters on the same history you judge them on.
This is not financial advice, and it makes no promise of profit.

## Going live (not implemented, on purpose)

Real trading would need: a fresh dedicated wallet with only money you can lose, a key kept
outside git, Jupiter swap integration, and your explicit sign-off after the paper results.
Nothing here does that.
