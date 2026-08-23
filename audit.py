import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "audit.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER NOT NULL,
    mandate_id TEXT NOT NULL,
    agent_id TEXT,
    instruction TEXT,
    product_name TEXT,
    claimed_category TEXT,
    derived_category TEXT,
    confidence REAL,
    amount_paise INTEGER,
    merchant_id TEXT,
    decision TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    detail TEXT,
    order_id TEXT
);
"""


class AuditLog:
    def __init__(self, path=DB_PATH, fresh=False):
        self.path = Path(path)
        if fresh and self.path.exists():
            self.path.unlink()
        self.conn = sqlite3.connect(self.path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def record(self, **row):
        row.setdefault("ts", int(time.time()))
        columns = ", ".join(row)
        placeholders = ", ".join("?" for _ in row)
        self.conn.execute(
            f"INSERT INTO decisions ({columns}) VALUES ({placeholders})",
            tuple(row.values()),
        )
        self.conn.commit()

    def all_rows(self):
        cur = self.conn.execute("SELECT * FROM decisions ORDER BY id")
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    def summary(self):
        cur = self.conn.execute(
            "SELECT decision, reason_code, COUNT(*) FROM decisions "
            "GROUP BY decision, reason_code ORDER BY COUNT(*) DESC"
        )
        return cur.fetchall()

    def close(self):
        self.conn.close()