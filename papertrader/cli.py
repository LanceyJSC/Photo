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

    a = p.parse_args(argv)
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


if __name__ == "__main__":
    sys.exit(main())
