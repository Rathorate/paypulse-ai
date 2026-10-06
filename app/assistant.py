"""A transparent natural-language interface over fixed, read-only analytics."""
from __future__ import annotations

import re
from typing import Any

from app.analytics import churn_customers, scored_transactions
from app.database import read_all


def answer(message: str, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not message.strip():
        raise ValueError("Enter a question to ask the assistant.")
    rows = rows if rows is not None else read_all()
    normalized = message.lower()
    amount_match = re.search(r"(?:over|above|greater than|more than)\s*\$?\s*(\d+(?:\.\d+)?)", normalized)
    threshold = float(amount_match.group(1)) if amount_match else None
    if any(word in normalized for word in ("churn", "retention", "at risk customer", "customers at risk")):
        customers = churn_customers(rows)
        matches = [c for c in customers if c["churn_status"] != "ACTIVE"][:8]
        return {"intent": "customer_churn", "answer": f"I found {len(matches)} customers at risk or churned. Prioritize {matches[0]['payer_name']} ({matches[0]['days_since_last_purchase']} days since their last purchase) first." if matches else "No customers are currently flagged as at risk.", "customers": matches, "transactions": []}
    if any(word in normalized for word in ("anomal", "suspicious", "high-risk", "high risk", "unusual", "fee")):
        matches = [r for r in scored_transactions(rows) if r["is_anomaly"]]
        if threshold is not None:
            matches = [r for r in matches if float(r["gross_amount"]) > threshold]
        matches.sort(key=lambda r:r["anomaly_score"], reverse=True)
        return {"intent": "anomaly_review", "answer": f"Found {len(matches)} flagged payment{'s' if len(matches)!=1 else ''}" + (f" over ${threshold:,.2f}." if threshold is not None else ".") + " These are review signals, not proof of fraud.", "transactions": matches[:12], "customers": []}
    matches = rows
    if threshold is not None:
        matches = [r for r in matches if float(r["gross_amount"]) > threshold]
    if "refund" in normalized or "revers" in normalized:
        matches = [r for r in matches if r["status"] == "REVERSED"]
    matches.sort(key=lambda r:r["timestamp"], reverse=True)
    return {"intent": "transaction_search", "answer": f"Found {len(matches)} matching transactions" + (f" over ${threshold:,.2f}." if threshold is not None else "."), "transactions": matches[:12], "customers": []}
