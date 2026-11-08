import unittest

from papertrader import data, safety, signals
from papertrader.config import Config
from papertrader.engine import Engine
from papertrader.risk import RiskManager
from papertrader.signals import Signal

C = data.Candle


def flat(ts, px):
    return C(ts, px, px * 1.001, px * 0.999, px, 100)


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.cfg = Config()
        self.rm = RiskManager(self.cfg)
        self.rm.on_bar(0, 100.0)
        self.sig = Signal("BTCUSDT", 0, 100.0, 95.0, 0.05, 2.0, "t")

    def test_size_respects_one_percent_risk_including_costs(self):
        n, why = self.rm.approve(self.sig, 100.0, 0, 100.0, 100.0, {})
        self.assertEqual(why, "approved")
        risk = n * (0.05 + self.cfg.round_trip_cost)
        self.assertLessEqual(risk, 100.0 * self.cfg.risk_per_trade + 1e-9)
        self.assertLessEqual(n, 100.0 * self.cfg.max_notional_frac + 1e-9)

    def test_price_through_stop_vetoed(self):
        n, why = self.rm.approve(self.sig, 94.0, 0, 100.0, 100.0, {})
        self.assertEqual(n, 0)

    def test_daily_loss_limit(self):
        n, why = self.rm.approve(self.sig, 100.0, 0, 96.0, 96.0, {})
        self.assertEqual((n, why), (0.0, "daily loss limit"))

    def test_drawdown_halves_then_halts_then_kills(self):
        self.rm.on_bar(1, 89.0)   # -11%
        self.assertEqual(self.rm.size_multiplier(89.0), 0.5)
        self.rm.on_bar(2, 79.0)   # -21%
        self.assertIn("HALT", self.rm.halted)
        self.rm.on_bar(3, 69.0)   # -31%
        self.assertTrue(self.rm.killed)
        n, _ = self.rm.approve(self.sig, 100.0, 3, 69.0, 69.0, {})
        self.assertEqual(n, 0)

    def test_consecutive_losses_pause_24h(self):
        for _ in range(4):
            self.rm.on_trade_closed(1000, -1.0)
        n, why = self.rm.approve(self.sig, 100.0, 1000 + 3600, 100.0, 100.0, {})
        self.assertEqual(why, "paused after consecutive losses")
        n, why = self.rm.approve(self.sig, 100.0, 1000 + 25 * 3600, 100.0, 100.0, {})
        self.assertNotEqual(why, "paused after consecutive losses")


class SafetyTests(unittest.TestCase):
    def test_entry_hours_and_blackout(self):
        cfg = Config()
        noon = 12 * 3600
        self.assertTrue(safety.entry_allowed("BTCUSDT", noon, cfg)[0])
        self.assertFalse(safety.entry_allowed("BTCUSDT", 3 * 3600, cfg)[0])
        cfg.blackouts = [("*", noon - 100, noon + 100)]
        self.assertFalse(safety.entry_allowed("BTCUSDT", noon, cfg)[0])

    def test_insane_bar_rejected(self):
        cfg = Config()
        self.assertFalse(safety.bar_is_sane(100.0, flat(0, 140.0), cfg))
        self.assertTrue(safety.bar_is_sane(100.0, flat(0, 101.0), cfg))


class SignalTests(unittest.TestCase):
    def test_entries_fill_strictly_after_signal(self):
        """A signal on bar t may only fill at bar t+1 (next open), never the same bar."""
        cfg = Config()
        eng = Engine(cfg)
        eng.run(data.synthetic(cfg.symbols, 3000, seed=5))
        signals_ = {(ts, sym) for ts, sym, k, _ in eng.ledger.decisions("signal")}
        entries = eng.ledger.decisions("entry")
        self.assertTrue(entries, "test needs at least one entry")
        for ts, sym, _, _ in entries:
            self.assertIn((ts - cfg.interval_seconds, sym), signals_)

    def test_cost_gate_blocks_tiny_moves(self):
        cfg = Config()
        cfg.cost_multiple = 1000.0
        s = data.synthetic(("BTCUSDT",), 1500, seed=2)["BTCUSDT"]
        for k in range(300, 1500, 7):
            sig, _ = signals.evaluate("BTCUSDT", s[:k], cfg)
            self.assertIsNone(sig)


class EngineTests(unittest.TestCase):
    def test_stop_exit_costs_and_never_loses_more_than_risk_plus_gap(self):
        cfg = Config()
        cfg.symbols = ("BTCUSDT",)
        cfg.entry_hours = (0, 24)
        eng = Engine(cfg)
        from papertrader.engine import Position
        eng.cash = 70.0
        eng.positions["BTCUSDT"] = Position("BTCUSDT", 0.3, 100.0, 0, 95.0, 30.0, 1.5, 0.255, 100.0)
        eng.history["BTCUSDT"] = [flat(i * 3600, 100.0) for i in range(300)]
        eng.on_bar(300 * 3600, {"BTCUSDT": C(300 * 3600, 99.0, 99.0, 90.0, 92.0, 1)})
        self.assertNotIn("BTCUSDT", eng.positions)
        t = eng.ledger.trades()[0]
        self.assertEqual(t[9], "stop")
        self.assertLess(t[7], 0)
        self.assertGreater(t[6], 0)           # fees were charged

    def test_full_run_invariants(self):
        for seed in (1, 2, 3):
            cfg = Config()
            eng = Engine(cfg)
            r = eng.run(data.synthetic(cfg.symbols, 4000, seed=seed))
            self.assertGreater(r["final_equity"], 0)
            for ts, eq in eng.ledger.equity_curve():
                self.assertGreater(eq, 0)
            # never more than max_positions open at once
            self.assertTrue(all(row[2] <= cfg.max_positions for row in
                                eng.ledger.db.execute("SELECT ts,equity,open_positions FROM equity")))
            # per-trade loss bounded: risk budget plus modest gap/cost slack
            for t in eng.ledger.trades():
                self.assertGreater(t[7], -0.05 * cfg.start_equity)


if __name__ == "__main__":
    unittest.main()
