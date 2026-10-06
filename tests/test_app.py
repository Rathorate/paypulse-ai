import json
import base64
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app import config
from app.analytics import churn_customers, scored_transactions, summary
from app.assistant import answer
from app.database import init_db, read_all, upsert_transactions
from app.paypal import fetch_transactions
from app.server import Handler


class DatabaseAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "test.db"
        init_db(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_seed_has_readable_demo_data_and_detectable_outliers(self):
        rows = read_all(self.db)
        self.assertGreaterEqual(len(rows), 30)
        scores = scored_transactions(rows)
        flagged = [x for x in scores if x["is_anomaly"]]
        self.assertGreaterEqual(len(flagged), 3)
        self.assertTrue(any("unusually high" in reason for x in flagged for reason in x["reasons"]))
        self.assertEqual(summary(rows)["transaction_count"], len(rows))

    def test_upsert_is_idempotent(self):
        row = {"transaction_id":"T-1", "payer_email":"a@example.test", "payer_name":"A",
               "timestamp":datetime.now(timezone.utc).isoformat(), "gross_amount":20, "fee_amount":1,
               "net_amount":19, "currency":"USD", "status":"SUCCESS", "country_code":"US",
               "payment_method":"PAYPAL_ACCOUNT", "source":"paypal_sandbox", "raw_json":{"id":"T-1"}}
        self.assertEqual(upsert_transactions([row], self.db), 1)
        self.assertEqual(upsert_transactions([row], self.db), 1)
        found = [r for r in read_all(self.db) if r["transaction_id"] == "T-1"]
        self.assertEqual(len(found), 1)
        self.assertEqual(json.loads(found[0]["raw_json"])["id"], "T-1")

    def test_assistant_returns_filtered_records_and_churn(self):
        rows = read_all(self.db)
        result = answer("Show me high-risk transactions over $200", rows)
        self.assertEqual(result["intent"], "anomaly_review")
        self.assertTrue(all(r["gross_amount"] > 200 and r["is_anomaly"] for r in result["transactions"]))
        retention = answer("Which customers may churn?", rows)
        self.assertEqual(retention["intent"], "customer_churn")
        self.assertTrue(all("predicted_churn_probability" in c for c in retention["customers"]))

    def test_empty_question_is_rejected(self):
        with self.assertRaises(ValueError):
            answer("   ", [])


class PayPalTests(unittest.TestCase):
    def test_configured_access_password_protects_dashboard_and_data(self):
        handler = object.__new__(Handler)
        handler.path = "/api/transactions"
        handler.headers = {}
        with patch.object(config, "ACCESS_PASSWORD", "test-password"):
            self.assertFalse(handler._authorized())
            handler.headers = {"Authorization": "Basic " + base64.b64encode(b"user:test-password").decode()}
            self.assertTrue(handler._authorized())
            handler.headers = {"Authorization": "Basic " + base64.b64encode(b"user:wrong").decode()}
            self.assertFalse(handler._authorized())
            handler.path = "/api/health"
            handler.headers = {}
            self.assertTrue(handler._authorized())

    def test_oauth_then_reporting_normalizes_sandbox_transaction(self):
        class Response:
            def __init__(self, body): self.body = body
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return json.dumps(self.body).encode()
        bodies = [
            {"access_token":"sandbox-token"},
            {"transaction_details":[{"transaction_info":{"transaction_id":"PP-123","transaction_status":"S",
              "transaction_initiation_date":"2026-10-01T10:00:00Z","transaction_amount":{"value":"25.00","currency_code":"USD"},
              "fee_amount":{"value":"1.25","currency_code":"USD"}},"payer_info":{"email_address":"buyer@example.test",
              "payer_name":{"alternate_full_name":"Buyer One"}}}]}
        ]
        calls=[]
        def fake_open(req, timeout):
            calls.append(req)
            return Response(bodies.pop(0))
        with patch.object(config, "PAYPAL_CLIENT_ID", "client"), patch.object(config, "PAYPAL_CLIENT_SECRET", "secret"), patch("app.paypal.urlopen", fake_open):
            rows=fetch_transactions()
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[0].full_url, "https://api-m.sandbox.paypal.com/v1/oauth2/token")
        self.assertEqual(rows[0]["transaction_id"], "PP-123")
        self.assertEqual(rows[0]["net_amount"], 23.75)
        self.assertEqual(rows[0]["source"], "paypal_sandbox")


if __name__ == "__main__":
    unittest.main()
