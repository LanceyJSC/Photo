"""Command line. Fake money only: there is no code path that places a real order."""
import argparse
import sys
import time
from datetime import datetime, timezone

from . import data as datamod
from .config import Config
from .engine import Engine, format_report
from .ledger import Ledger


def _load_live(cfg, start_ts, end_ts):
    return {s: datamod.fetch_binance(s, cfg.interval, start_ts, end_ts) for s in cfg.symbols}


def main(argv=None):
    p = argparse.ArgumentParser(prog="papertrader", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("backtest", help="replay history through the full system")
    b.add_argument("--synthetic", action="store_true", help="fake data, tests code only")
    b.add_argument("--days", type=int, default=180)
    b.add_argument("--seed", type=int, default=1)
    b.add_argument("--db", default=":memory:")

    f = sub.add_parser("paper", help="forward paper trading from a start date on live data")
    f.add_argument("--since", required=True, help="UTC start date, e.g. 2026-11-09")
    f.add_argument("--loop", type=int, default=0, help="re-run every N seconds (0 = once)")
    f.add_argument("--db", default="paper.sqlite")

    m = sub.add_parser("meme-backtest", help="memecoin strategy on SYNTHETIC market (tests code only)")
    m.add_argument("--days", type=int, default=7)
    m.add_argument("--seed", type=int, default=1)
    m.add_argument("--control", action="store_true", help="early momentum carries NO information")
    m.add_argument("--runner-rate", type=float, default=None, help="share of launches that become real runners")
    sw = sub.add_parser("meme-sweep", help="how final equity depends on the ASSUMED runner rate")
    sw.add_argument("--days", type=int, default=7)
    sw.add_argument("--seeds", type=int, default=5)
    lv = sub.add_parser("meme-paper", help="forward paper trading memecoins on live data")
    lv.add_argument("--poll", type=int, default=300)
    lv.add_argument("--db", default="meme_paper.sqlite")
    sub.add_parser("meme-check", help="print what the live APIs return, to verify the parsers")

    a = p.parse_args(argv)
    if a.cmd.startswith("meme"):
        return _meme(a)
    cfg = Config()

    if a.cmd == "backtest":
        if a.synthetic:
            series = datamod.synthetic(cfg.symbols, a.days * 24, seed=a.seed)
            print("NOTE: synthetic data. This only exercises the code; it says nothing about real markets.\n")
        else:
            end = int(time.time())
            series = _load_live(cfg, end - a.days * 86400, end)
        eng = Engine(cfg, Ledger(a.db))
        print(format_report(eng.run(series)))
        return 0

    start = int(datetime.strptime(a.since, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    warm = start - 20 * 86400   # warmup history so indicators are ready on day one
    while True:
        end = int(time.time())
        series = _load_live(cfg, warm, end)
        eng = Engine(cfg, Ledger(":memory:"))
        r = eng.run(series)
        print(time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
        print(format_report(r), flush=True)
        if not a.loop:
            return 0
        time.sleep(a.loop)


def _run_sim(days, seed, runner_rate, informative=True):
    from .meme import report, sim
    from .meme.config import MemeConfig
    from .meme.engine import MemeEngine
    cfg = MemeConfig()
    steps = days * 288
    w = sim.World(steps + 288, seed=seed, runner_rate=runner_rate, informative=informative)
    eng = MemeEngine(cfg, Ledger())
    for k in range(steps):
        eng.on_step(w.ts(k), w.snaps(k), w.safety, w.can_sell)
    return eng, cfg, w, report.summarize(eng, cfg)


def _meme(a):
    from .meme import report
    if a.cmd == "meme-backtest":
        print("NOTE: SYNTHETIC market built on my own assumptions. It tests the code; it says nothing about real memecoins.\n")
        eng, cfg, w, r = _run_sim(a.days, a.seed, a.runner_rate, not a.control)
        print(report.fmt(r))
        return 0
    if a.cmd == "meme-sweep":
        print("Mean final equity (start 100) vs the ASSUMED share of launches that become real runners.")
        print("'informative' = early momentum predicts later gains (I built that in). 'control' = it does not.")
        print("The real-world answers to both are UNKNOWN: that is the whole question.\n")
        print("runner rate | informative: mean final, runs<100 | control: mean final, runs<100")
        for rate in (0.0, 0.02, 0.04, 0.08, 0.12):
            row = []
            for inf in (True, False):
                fin, below = [], 0
                for sd in range(1, a.seeds + 1):
                    _, _, _, r = _run_sim(a.days, sd, rate, inf)
                    fin.append(r["final"]); below += r["final"] < 100
                row.append(f"{sum(fin)/len(fin):8.1f}, {below}/{a.seeds}")
            print(f"   {rate:5.0%}    |      {row[0]}        |      {row[1]}")
        return 0
    from .meme.config import MemeConfig
    from .meme.engine import MemeEngine
    from .meme.live import LiveFeed
    feed = LiveFeed()
    if a.cmd == "meme-check":
        feed.discover()
        print("tracked tokens:", len(feed.tracked))
        sn = feed.snaps()
        print("snapshots parsed:", len(sn))
        for s in list(sn.values())[:3]:
            print(s, "\n  safety:", feed.safety(s.addr))
        return 0
    cfg = MemeConfig()
    eng = MemeEngine(cfg, Ledger(a.db))
    n = 0
    while True:
        if n % 3 == 0:
            feed.discover()
        sn = feed.snaps()
        eng.on_step(int(time.time()), sn, feed.safety)
        print(time.strftime("%H:%M:%S"), f"tracked {len(feed.tracked)} equity {eng.equity():.2f} open {len(eng.pos)}", flush=True)
        eng.ledger.db.commit()
        n += 1
        time.sleep(a.poll)


if __name__ == "__main__":
    sys.exit(main())
