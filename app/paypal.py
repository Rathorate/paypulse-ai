"""PayPal sandbox reporting API client. Read-only: this module never creates payments."""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any

from app import config


class PayPalError(RuntimeError):
    pass


def configured() -> bool:
    return bool(config.PAYPAL_CLIENT_ID and config.PAYPAL_CLIENT_SECRET)


def _request(url: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    try:
        with urlopen(req, timeout=18) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise PayPalError(f"PayPal returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PayPalError(f"Could not reach PayPal sandbox: {exc}") from exc


def _date_range() -> tuple[str, str]:
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = config.PAYPAL_START_DATE.strip()
    if not start:
        start = (end - timedelta(days=30)).isoformat().replace("+00:00", "Z")
    return start, end.isoformat().replace("+00:00", "Z")


def fetch_transactions() -> list[dict[str, Any]]:
    if not configured():
        raise PayPalError("PayPal sandbox is not configured. Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET to .env, then restart the app.")
    token_url = f"{config.PAYPAL_BASE_URL}/v1/oauth2/token"
    basic = base64.b64encode(f"{config.PAYPAL_CLIENT_ID}:{config.PAYPAL_CLIENT_SECRET}".encode()).decode()
    token = _request(token_url, b"grant_type=client_credentials", {"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"})
    access_token = token.get("access_token")
    if not access_token:
        raise PayPalError("PayPal OAuth response did not include an access token.")
    start, end = _date_range()
    query = urlencode({"start_date": start, "end_date": end, "fields": "all", "page_size": "100", "page": "1"})
    report = _request(f"{config.PAYPAL_BASE_URL}/v1/reporting/transactions?{query}", headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"})
    result = []
    for item in report.get("transaction_details", []):
        info = item.get("transaction_info") or {}
        payer = item.get("payer_info") or {}
        amt = info.get("transaction_amount") or {}
        fee = info.get("fee_amount") or {}
        gross = float(amt.get("value", 0))
        fee_value = float(fee.get("value", 0))
        if not info.get("transaction_id"):
            continue
        status_code = str(info.get("transaction_status", "S"))
        status = "SUCCESS" if status_code in ("S", "SUCCESS") else "REVERSED" if status_code in ("V", "D", "REFUNDED") else "PENDING"
        name = (payer.get("payer_name") or {}).get("alternate_full_name", "")
        address = (item.get("shipping_info") or {}).get("address") or {}
        result.append({"transaction_id": info["transaction_id"], "payer_email": payer.get("email_address", "unknown@paypal.invalid"),
                       "payer_name": name, "timestamp": info.get("transaction_initiation_date") or info.get("transaction_updated_date") or end,
                       "gross_amount": gross, "fee_amount": fee_value, "net_amount": round(gross-fee_value, 2),
                       "currency": amt.get("currency_code", "USD"), "status": status,
                       "country_code": address.get("country_code", "US"), "payment_method": "PAYPAL_ACCOUNT",
                       "source": "paypal_sandbox", "raw_json": item})
    return result
