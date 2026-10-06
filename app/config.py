"""Configuration loaded from environment and a local .env file."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()
DB_PATH = Path(os.environ.get("PAYPULSE_DB_PATH", str(ROOT / "data" / "paypulse.db")))
if not DB_PATH.is_absolute():
    DB_PATH = ROOT / DB_PATH
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_BASE_URL = os.environ.get("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com").rstrip("/")
PAYPAL_START_DATE = os.environ.get("PAYPAL_START_DATE", "")
ACCESS_PASSWORD = os.environ.get("PAYPULSE_ACCESS_PASSWORD", "")
HOST = os.environ.get("PAYPULSE_HOST", "127.0.0.1")
PORT = int(os.environ.get("PAYPULSE_PORT", os.environ.get("PORT", "8000")))
