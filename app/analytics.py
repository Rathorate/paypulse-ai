"""Offline-first merchant analytics and risk scoring."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

from app.database import read_all


def _dt(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


def scored_transactions(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = rows if rows is not None else read_all()
    amounts = [float(r["gross_amount"]) for r in rows]
    center = median(amounts) if amounts else 0
    deviations = [abs(x-center) for x in amounts]
    mad = median(deviations) if deviations else 0
    by_payer_hour: Counter[tuple[str, str]] = Counter()
    for row in rows:
        key = (row["payer_email"], _dt(row["timestamp"]).strftime("%Y-%m-%dT%H"))
        by_payer_hour[key] += 1
    result = []
    for row in rows:
        amount = float(row["gross_amount"])
        fee_ratio = float(row["fee_amount"]) / max(amount, 0.01)
        key = (row["payer_email"], _dt(row["timestamp"]).strftime("%Y-%m-%dT%H"))
        score = min(1.0, abs(amount-center) / max(6 * mad, center * .9, 1))
        reasons = []
        if amount > center + max(4 * mad, center * 1.5):
            reasons.append("Amount is unusually high for this payment history")
            score = max(score, .84)
        if fee_ratio > .08:
            reasons.append("Processing fee exceeds 8% of the payment")
            score = max(score, min(.99, .66 + fee_ratio))
        if by_payer_hour[key] >= 3:
            reasons.append("Multiple payments from this customer within one hour")
            score = max(score, .76)
        is_anomaly = bool(reasons)
        result.append({**row, "anomaly_score": round(score, 3), "is_anomaly": is_anomaly,
                       "risk_level": "CRITICAL" if score >= .9 else "HIGH" if is_anomaly else "LOW",
                       "reasons": reasons})
    return result


def churn_customers(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = rows if rows is not None else read_all()
    customers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["status"] == "SUCCESS":
            customers[row["payer_email"]].append(row)
    now = datetime.now(timezone.utc)
    results = []
    for email, activity in customers.items():
        activity.sort(key=lambda x: x["timestamp"])
        last = _dt(activity[-1]["timestamp"])
        days = max(0, (now-last).days)
        gaps = [(_dt(b["timestamp"])-_dt(a["timestamp"])).total_seconds()/86400
                for a,b in zip(activity, activity[1:])]
        typical_gap = median(gaps) if gaps else 30
        recency = min(1, days / max(typical_gap * 2.5, 45))
        frequency = 1 / (1 + len(activity) / 3)
        risk = min(1, .78 * recency + .22 * frequency)
        results.append({"payer_email": email, "payer_name": activity[-1].get("payer_name") or email,
                        "last_purchase_date": activity[-1]["timestamp"], "days_since_last_purchase": days,
                        "total_lifetime_transactions": len(activity),
                        "total_spend": round(sum(float(x["gross_amount"]) for x in activity), 2),
                        "predicted_churn_probability": round(risk, 3),
                        "churn_status": "CHURNED" if days > max(typical_gap*4, 90) else "AT_RISK" if risk >= .58 else "ACTIVE"})
    return sorted(results, key=lambda x:x["predicted_churn_probability"], reverse=True)


def summary(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else read_all()
    successful = [r for r in rows if r["status"] == "SUCCESS"]
    now = datetime.now(timezone.utc)
    last7 = [r for r in successful if _dt(r["timestamp"]) >= now-timedelta(days=7)]
    scores = scored_transactions(rows)
    daily: dict[str, float] = defaultdict(float)
    for r in last7:
        daily[_dt(r["timestamp"]).strftime("%Y-%m-%d")] += float(r["gross_amount"])
    churn = churn_customers(rows)
    return {"total_volume": round(sum(float(r["gross_amount"]) for r in successful), 2),
            "transaction_count": len(successful), "average_order_value": round(sum(float(r["gross_amount"]) for r in successful)/max(1,len(successful)), 2),
            "anomalies_detected": sum(1 for r in scores if r["is_anomaly"]),
            "at_risk_customers": sum(1 for c in churn if c["churn_status"] != "ACTIVE"),
            "volume_7d": round(sum(float(r["gross_amount"]) for r in last7), 2),
            "daily_volume": [{"date": k, "amount": round(v,2)} for k,v in sorted(daily.items())],
            "sources": sorted({r["source"] for r in rows})}
