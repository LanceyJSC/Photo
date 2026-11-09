import unittest

from papertrader.meme import live, sim, strategy
from papertrader.meme.config import MemeConfig
from papertrader.meme.engine import MemeEngine
from papertrader.meme.model import Safety, Snap

GOOD = Safety(True, True, 15.0, 100.0, True)


def snap(ts, price=1.0, liq=50_000, addr="A", **kw):
    d = dict(vol5m=8000, buys5m=60, sells5m=20, chg5m=0.03, chg1h=0.3, age_min=60)
    d.update(kw)
    return Snap(ts, addr, "TKN", price, liq, d["vol5m"], d["buys5m"], d["sells5m"], d["chg5m"], d["chg1h"], d["age_min"])


def run(prices, safety=GOOD, can_sell=lambda a: True, liqs=None, cfg=None):
    cfg = cfg or MemeConfig()
    eng = MemeEngine(cfg)
    for i, p in enumerate(prices):
        liq = liqs[i] if liqs else 50_000
        eng.on_step(1_000_000 + i * 300, {"A": snap(1_000_000 + i * 300, p, liq)}, lambda a: safety, can_sell)
    return eng


class SafetyTests(unittest.TestCase):
    def test_every_unknown_fails_closed(self):
        cfg = MemeConfig()
        self.assertFalse(strategy.safety_ok(None, cfg)[0])
        for i in range(5):
            f = list(GOOD)
            f[i] = None
            self.assertFalse(strategy.safety_ok(Safety(*f), cfg)[0], f)
        self.assertTrue(strategy.safety_ok(GOOD, cfg)[0])

    def test_unsafe_token_never_bought(self):
        for bad in (Safety(False, True, 15, 100, True), Safety(True, True, 60, 100, True),
                    Safety(True, True, 15, 100, False), Safety(True, True, 15, 10, True)):
            eng = run([1.0] * 5, safety=bad)
            self.assertEqual(eng.ledger.decisions("entry"), [])


class ExecutionTests(unittest.TestCase):
    def test_entry_fills_one_step_after_signal_with_costs(self):
        eng = run([1.0, 1.0, 1.0])
        sig, ent = eng.ledger.decisions("signal"), eng.ledger.decisions("entry")
        self.assertTrue(sig and ent)
        self.assertEqual(ent[0][0], sig[0][0] + 300)
        self.assertGreater(eng.pos["A"].entry_price, 1.0)   # slippage made it worse
        self.assertLess(eng.cash, 100 - 4.9)                # notional + fee + gas taken

    def test_position_size_is_capped(self):
        eng = run([1.0, 1.0])
        self.assertLessEqual(eng.pos["A"].notional, 100 * MemeConfig().pos_frac + 1e-9)

    def test_stop_loss_loses_about_stop_plus_costs(self):
        eng = run([1.0, 1.0, 1.0, 0.7, 0.7, 0.7])
        t = eng.ledger.trades()
        self.assertEqual(t[-1][9], "stop")
        self.assertLess(t[-1][8], -0.25)                    # worse than -25% once costs are in

    def test_rug_is_not_escapable(self):
        """Liquidity and price collapse in one step: exit fills after the collapse."""
        eng = run([1.0, 1.0, 1.0, 0.03, 0.03, 0.03], liqs=[50_000] * 3 + [1_500] * 3)
        t = eng.ledger.trades()[-1]
        self.assertLess(t[8], -0.9)

    def test_undetected_honeypot_is_total_loss(self):
        eng = run([1.0, 1.0, 1.0, 0.6, 0.6], can_sell=lambda a: False)
        t = eng.ledger.trades()
        self.assertTrue(t and t[-1][9] == "honeypot: sell failed")
        self.assertLessEqual(t[-1][8], -0.99)

    def test_take_profit_sells_half_then_trails(self):
        eng = run([1.0, 1.0, 1.0, 2.2, 2.2, 3.0, 3.0, 1.9, 1.9, 1.9])
        reasons = [t[9] for t in eng.ledger.trades()]
        self.assertEqual(reasons[0], "take profit (half)")
        self.assertIn("trailing stop", reasons)
        self.assertGreater(sum(t[7] for t in eng.ledger.trades()), 0)

    def test_no_reentry_after_exit(self):
        eng = run([1.0, 1.0, 1.0, 0.7, 0.7, 1.0, 1.0, 1.0, 1.0])
        self.assertEqual(len(eng.ledger.decisions("entry")), 1)


class SimInvariantTests(unittest.TestCase):
    def test_full_run_respects_limits(self):
        cfg = MemeConfig()
        w = sim.World(2 * 288 + 288, seed=4)
        eng = MemeEngine(cfg)
        for k in range(2 * 288):
            eng.on_step(w.ts(k), w.snaps(k), w.safety, w.can_sell)
            self.assertLessEqual(len(eng.pos), cfg.max_positions)
            self.assertGreaterEqual(eng.cash, -1e-9)
        for t in eng.ledger.trades():
            self.assertGreaterEqual(t[8], -1.0 - 1e-6)      # can never lose more than 100% of a position

    def test_kill_switch_stops_new_entries(self):
        cfg = MemeConfig()
        eng = MemeEngine(cfg)
        eng.risk.on_step(0, 100.0)
        eng.risk.on_step(0, 60.0)
        self.assertTrue(eng.risk.killed)
        self.assertEqual(eng.risk.size(0, 60.0, 60.0, {})[0], 0.0)


class LiveParserTests(unittest.TestCase):
    # fixture is MY RECOLLECTION of DexScreener's shape; verify with `meme-check`
    PAIR = {"chainId": "solana", "baseToken": {"address": "Mint1", "symbol": "XYZ"}, "priceUsd": "0.0012",
            "liquidity": {"usd": 42000}, "volume": {"m5": 5000}, "txns": {"m5": {"buys": 30, "sells": 12}},
            "priceChange": {"m5": 4.5, "h1": 35.0}, "pairCreatedAt": 1_700_000_000_000}

    def test_parse_pair(self):
        s = live.parse_pair(self.PAIR, 1_700_000_000 + 3600)
        self.assertEqual((s.addr, s.buys5m, s.sells5m), ("Mint1", 30, 12))
        self.assertAlmostEqual(s.chg1h, 0.35)
        self.assertAlmostEqual(s.age_min, 60.0)

    def test_parse_pair_missing_field_returns_none(self):
        bad = dict(self.PAIR)
        del bad["liquidity"]
        self.assertIsNone(live.parse_pair(bad, 0))

    # trimmed from a real RugCheck /report response (2026-11-09)
    REPORT = {"mintAuthority": None, "freezeAuthority": None, "rugged": False, "risks": [],
              "transferFee": {"pct": 0}, "token_extensions": {"transferFeeConfig": None, "nonTransferable": False},
              "knownAccounts": {"POOL": {"type": "AMM"}, "CREATOR1": {"type": "CREATOR"}},
              "topHolders": [{"owner": "POOL", "address": "x", "pct": 80.0}, {"owner": "w1", "address": "a", "pct": 4.0},
                             {"owner": "w2", "address": "b", "pct": 1.0}],
              "markets": [{"lp": {"lpLockedPct": 0, "quoteUSD": 10, "baseUSD": 10}},
                          {"lp": {"lpLockedPct": 100, "quoteUSD": 40000, "baseUSD": 41000}}]}

    def test_rugcheck_real_shape_passes_and_excludes_pools(self):
        sf = live.parse_rugcheck(self.REPORT)
        self.assertEqual((sf.mint_revoked, sf.freeze_revoked, sf.sell_sim_ok), (True, True, True))
        self.assertAlmostEqual(sf.top10_pct, 5.0)       # the 80% AMM pool is not a whale
        self.assertEqual(sf.lp_locked_pct, 100)         # uses the biggest market, not the tiny one
        self.assertTrue(strategy.safety_ok(sf, MemeConfig())[0])

    def test_rugcheck_unknown_or_dangerous_fails_closed(self):
        cfg = MemeConfig()
        self.assertFalse(strategy.safety_ok(live.parse_rugcheck({}), cfg)[0])
        self.assertFalse(strategy.safety_ok(live.parse_rugcheck(None), cfg)[0])
        for change in ({"mintAuthority": "SomeKey"}, {"freezeAuthority": "SomeKey"}, {"rugged": True},
                       {"risks": [{"name": "x", "level": "danger"}]}, {"transferFee": {"pct": 5}},
                       {"token_extensions": {"permanentDelegate": "Key"}}):
            rep = dict(self.REPORT, **change)
            self.assertFalse(strategy.safety_ok(live.parse_rugcheck(rep), cfg)[0], change)
        for key in ("mintAuthority", "risks"):
            rep = {k: v for k, v in self.REPORT.items() if k != key}
            self.assertFalse(strategy.safety_ok(live.parse_rugcheck(rep), cfg)[0], key)


if __name__ == "__main__":
    unittest.main()
