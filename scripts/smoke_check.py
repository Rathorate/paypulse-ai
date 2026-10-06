"""HTTP smoke check; start `python -m app.server` first."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000"


def get(path):
    with urlopen(BASE + path, timeout=5) as response:
        return json.loads(response.read())


health = get("/api/health")
assert health["status"] == "ok", health
summary = get("/api/summary")
assert summary["transaction_count"] >= 30, summary
txns = get("/api/transactions")
assert txns["total"] >= summary["transaction_count"], txns
chat_req = Request(BASE + "/api/chat", data=json.dumps({"message":"Show high-risk payments over $200"}).encode(), headers={"Content-Type":"application/json"}, method="POST")
with urlopen(chat_req, timeout=5) as response:
    chat = json.loads(response.read())
assert chat["intent"] == "anomaly_review" and chat["transactions"], chat
try:
    urlopen(Request(BASE + "/api/sync", data=b"{}", headers={"Content-Type":"application/json"}, method="POST"), timeout=5)
    raise AssertionError("Sync must explain that credentials are needed in demo mode")
except HTTPError as exc:
    sync_error = json.loads(exc.read())
    assert exc.code == 503 and "PAYPAL_CLIENT_ID" in sync_error["error"], sync_error
with urlopen(BASE + "/", timeout=5) as response:
    assert b"PayPulse AI" in response.read()
print("HTTP smoke check passed: UI, health, seeded SQLite, analytics, assistant, and missing-key PayPal guidance.")
