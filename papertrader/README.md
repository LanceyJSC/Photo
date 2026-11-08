# papertrader: paper-trading system (fake money only)

There is **no code path that places a real order or reads a wallet key**.

## Memecoins (primary strategy) - `papertrader/meme/`

    python3 -m papertrader meme-check                 # FIRST: verify the live parsers on your machine
    python3 -m papertrader meme-paper --poll 300      # forward paper trading on live Solana data
    python3 -m papertrader meme-backtest --days 7     # synthetic market: tests the code only
    python3 -m papertrader meme-backtest --control    # same, but momentum carries no information
    python3 -m papertrader meme-sweep --days 7        # sensitivity table (about 1 minute)

**Rules.** Young tokens (10 min to 6 h old) with >= 20k liquidity, real volume, buys > 1.3x sells and a
+10% to +80% one-hour move (no chasing the top). Safety must pass on every check or the token is rejected,
and *unknown counts as fail*: mint and freeze authority revoked, top-10 holders <= 35%, liquidity >= 80%
locked, sell simulation ok. Positions are 5% of equity (assumed able to go to zero), max 4 open, max 20%
exposure at cost, 12 entries/day, 10% daily loss limit, drawdown halves/halts/kills at 10/20/30%.
Exits: -25% stop, liquidity collapse, sell half at 2x, 30% trailing stop once +50%, 4h time stop.
Orders decided on one step fill on the next step with 0.85% fee, 1.5% slippage plus size impact, and gas.

**What the simulator tells you (and does not).** The synthetic market is built from MY assumptions
(49% of launches bleed, 22% rug, 8% honeypots, 17% pump-and-fade, 4% runners). Sweep, 6 seeds x 7 days:

| runner share | momentum predicts (my build) | momentum uninformative (control) |
|---|---|---|
| 0% | 83 (6/6 runs lose) | 79 (6/6 lose) |
| 4% | 124 (4/6 lose) | 82 (6/6 lose) |
| 8% | 197 (0/6 lose) | 81 (6/6 lose) |

Profit appears only if BOTH are true in the real market: enough launches become real runners AND early
momentum predicts them. If momentum is uninformative the strategy loses about 20% a week in every run.
Nobody knows the real values; only a live forward test can estimate them. Don't read the synthetic
profits as evidence.

**Known weaknesses.** Live APIs untested from the build sandbox (verify with `meme-check`); the
live sell check is only RugCheck's "no danger flags", not a real sell simulation; the paper fills
are guesses at real slippage; `meme-paper` keeps its state in memory, so stopping it loses open
positions (the trade log is saved to SQLite); 100+ trades are needed before any result means anything.

## BTC/ETH/SOL system (secondary)

It simulates
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
