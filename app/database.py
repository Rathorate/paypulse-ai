"""SQLite persistence and a deterministic, clearly labeled demo dataset."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import DB_PATH


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    db_path = Path(path or DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection(path: Path | str | None = None):
    db = connect(path)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db(path: Path | str | None = None, seed: bool = True) -> None:
    with connection(path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            payer_email TEXT NOT NULL,
            payer_name TEXT NOT NULL DEFAULT '',
            timestamp TEXT NOT NULL,
            gross_amount REAL NOT NULL,
            fee_amount REAL NOT NULL DEFAULT 0,
            net_amount REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            status TEXT NOT NULL DEFAULT 'SUCCESS',
            country_code TEXT NOT NULL DEFAULT 'US',
            payment_method TEXT NOT NULL DEFAULT 'PAYPAL_ACCOUNT',
            source TEXT NOT NULL DEFAULT 'demo',
            raw_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_transactions_time ON transactions(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_transactions_payer ON transactions(payer_email, timestamp DESC);
        """)
        count = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        if seed and count == 0:
            _seed(db)


def _seed(db: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    customers = [
        ("amara@example.test", "Amara Okafor", 0),
        ("james@example.test", "James Carter", 2),
        ("mei@example.test", "Mei Tan", 6),
        ("lucas@example.test", "Lucas Silva", 25),
        ("noah@example.test", "Noah Wilson", 40),
        ("fatima@example.test", "Fatima Bello", 70),
        ("olivia@example.test", "Olivia Martin", 100),
        ("ethan@example.test", "Ethan Brown", 150),
    ]
    rows: list[tuple[Any, ...]] = []
    amounts = [42.00, 76.50, 33.25, 58.00, 119.99, 24.00, 85.00, 39.50,
               52.00, 64.00, 47.75, 92.00, 28.00, 72.00, 36.00, 55.00,
               109.00, 44.00, 60.00, 31.00, 48.50, 82.00, 67.00, 51.00,
               73.00, 29.00, 46.00, 63.00, 95.00, 54.00]
    for i, amount in enumerate(amounts):
        payer, name, age_bias = customers[i % len(customers)]
        # Concentrate ordinary activity in recent weeks while retaining old customers.
        days_ago = min(150, (i * 3 + (i % 5) * 2) + age_bias)
        when = now - timedelta(days=days_ago, hours=(i * 7) % 24)
        if payer == "amara@example.test" and i in (0, 8, 16):
            when = now - timedelta(minutes=10 + i)
        fee = round(amount * 0.029 + 0.30, 2)
        rows.append((f"DEMO-{i+1:04d}", payer, name, when.isoformat(), amount, fee,
                     round(amount-fee, 2), "USD", "SUCCESS", "US", "PAYPAL_ACCOUNT", "demo", "{}"))
    # Intentional, explainable outliers for the visual and scoring demo.
    specials = [
        ("DEMO-ANOM-001", "amara@example.test", "Amara Okafor", now-timedelta(minutes=3), 1299.00, 0.30, "US"),
        ("DEMO-ANOM-002", "amara@example.test", "Amara Okafor", now-timedelta(minutes=2), 1190.00, 87.50, "US"),
        ("DEMO-ANOM-003", "suspicious@example.test", "Unrecognized Buyer", now-timedelta(minutes=1), 725.00, 21.33, "NG"),
    ]
    for tid, email, name, when, amount, fee, country in specials:
        rows.append((tid, email, name, when.isoformat(), amount, fee, round(amount-fee, 2),
                     "USD", "SUCCESS", country, "PAYPAL_ACCOUNT", "demo", "{}"))
    db.executemany("""INSERT OR IGNORE INTO transactions
        (transaction_id,payer_email,payer_name,timestamp,gross_amount,fee_amount,net_amount,
         currency,status,country_code,payment_method,source,raw_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)


def upsert_transactions(rows: list[dict[str, Any]], path: Path | str | None = None) -> int:
    sql = """INSERT INTO transactions
        (transaction_id,payer_email,payer_name,timestamp,gross_amount,fee_amount,net_amount,
         currency,status,country_code,payment_method,source,raw_json)
        VALUES (:transaction_id,:payer_email,:payer_name,:timestamp,:gross_amount,:fee_amount,:net_amount,
         :currency,:status,:country_code,:payment_method,:source,:raw_json)
        ON CONFLICT(transaction_id) DO UPDATE SET payer_email=excluded.payer_email,
        payer_name=excluded.payer_name,timestamp=excluded.timestamp,gross_amount=excluded.gross_amount,
        fee_amount=excluded.fee_amount,net_amount=excluded.net_amount,currency=excluded.currency,
        status=excluded.status,country_code=excluded.country_code,payment_method=excluded.payment_method,
        source=excluded.source,raw_json=excluded.raw_json"""
    with connection(path) as db:
        before = db.total_changes
        db.executemany(sql, [{**row, "raw_json": json.dumps(row.get("raw_json", {})) if not isinstance(row.get("raw_json", "{}"), str) else row.get("raw_json", "{}")} for row in rows])
        return db.total_changes - before


def read_all(path: Path | str | None = None) -> list[dict[str, Any]]:
    with connection(path) as db:
        return [dict(row) for row in db.execute("SELECT * FROM transactions ORDER BY timestamp DESC")]
