"""Logger agent: SQLite audit trail of every decision, trade and equity point."""
import sqlite3


class Ledger:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS decisions(ts INTEGER, symbol TEXT, kind TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS trades(symbol TEXT, entry_ts INTEGER, exit_ts INTEGER,
            entry_price REAL, exit_price REAL, notional REAL, fees REAL, net_pnl REAL,
            r_multiple REAL, exit_reason TEXT);
        CREATE TABLE IF NOT EXISTS equity(ts INTEGER, equity REAL, cash REAL, open_positions INTEGER);
        """)

    def decision(self, ts, symbol, kind, detail):
        self.db.execute("INSERT INTO decisions VALUES (?,?,?,?)", (ts, symbol, kind, detail))

    def trade(self, *row):
        self.db.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?)", row)

    def equity(self, ts, eq, cash, n):
        self.db.execute("INSERT INTO equity VALUES (?,?,?,?)", (ts, eq, cash, n))

    def trades(self):
        return self.db.execute("SELECT * FROM trades ORDER BY exit_ts").fetchall()

    def equity_curve(self):
        return self.db.execute("SELECT ts, equity FROM equity ORDER BY ts").fetchall()

    def decisions(self, kind=None):
        q = "SELECT ts, symbol, kind, detail FROM decisions"
        if kind:
            return self.db.execute(q + " WHERE kind=? ORDER BY ts", (kind,)).fetchall()
        return self.db.execute(q + " ORDER BY ts").fetchall()
