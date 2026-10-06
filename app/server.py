"""Small dependency-free JSON API and static web server for PayPulse AI."""
from __future__ import annotations

import json
import mimetypes
import base64
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from app import config
from app.analytics import churn_customers, scored_transactions, summary
from app.assistant import answer
from app.database import init_db, read_all, upsert_transactions
from app.paypal import PayPalError, configured, fetch_transactions

WEB = Path(__file__).resolve().parents[1] / "web"


class Handler(BaseHTTPRequestHandler):
    server_version = "PayPulseAI/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def _send(self, status: int, payload: object, content_type: str = "application/json; charset=utf-8") -> None:
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store" if content_type.startswith("application/json") else "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 16_384:
            raise ValueError("Request body is too large.")
        raw = self.rfile.read(length)
        data = json.loads(raw or b"{}")
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object.")
        return data

    def _authorized(self) -> bool:
        # Keep the non-sensitive health probe public for Render's deployment checks.
        if self.path.split("?", 1)[0] == "/api/health" or not config.ACCESS_PASSWORD:
            return True
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            credentials = base64.b64decode(header[6:], validate=True).decode("utf-8")
            _, password = credentials.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return False
        return hmac.compare_digest(password, config.ACCESS_PASSWORD)

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="PayPulse AI", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if not self._require_auth():
            return
        if path == "/api/health":
            return self._send(200, {"status": "ok", "paypal_configured": configured(), "mode": "paypal_sandbox" if configured() else "demo"})
        if path == "/api/summary":
            return self._send(200, summary())
        if path == "/api/transactions":
            query = parse_qs(parsed.query)
            rows = scored_transactions()
            search = query.get("search", [""])[0].strip().lower()
            status = query.get("status", [""])[0].strip().upper()
            risk = query.get("risk", [""])[0].strip().upper()
            if search:
                rows = [r for r in rows if search in (r["transaction_id"]+r["payer_email"]+r["payer_name"]).lower()]
            if status:
                rows = [r for r in rows if r["status"] == status]
            if risk == "ANOMALY":
                rows = [r for r in rows if r["is_anomaly"]]
            return self._send(200, {"items": rows[:500], "total": len(rows)})
        if path == "/api/anomalies":
            rows = [r for r in scored_transactions() if r["is_anomaly"]]
            return self._send(200, {"items": sorted(rows,key=lambda r:r["anomaly_score"],reverse=True), "total": len(rows)})
        if path == "/api/churn":
            items = churn_customers()
            return self._send(200, {"items": items, "total": len(items)})
        if path == "/" or path == "/index.html":
            return self._static("index.html")
        if path.startswith("/assets/"):
            return self._static(path.lstrip("/"))
        return self._send(404, {"error": "Not found"})

    def _static(self, relative: str) -> None:
        target = (WEB / relative).resolve()
        if WEB.resolve() not in target.parents or not target.is_file():
            return self._send(404, {"error": "Not found"})
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self._send(200, target.read_bytes(), content_type + ("; charset=utf-8" if content_type.startswith(("text/", "application/javascript")) else ""))

    def do_POST(self) -> None:
        if not self._require_auth():
            return
        if self.path == "/api/chat":
            try:
                message = str(self._json_body().get("message", ""))
                if len(message) > 1000:
                    raise ValueError("Question must be 1,000 characters or fewer.")
                return self._send(200, answer(message))
            except (ValueError, json.JSONDecodeError) as exc:
                return self._send(400, {"error": str(exc)})
        if self.path == "/api/sync":
            try:
                imported = fetch_transactions()
                count = upsert_transactions(imported)
                return self._send(200, {"ok": True, "fetched": len(imported), "upserted": count, "source": "paypal_sandbox"})
            except PayPalError as exc:
                code = 503 if not configured() else 502
                return self._send(code, {"ok": False, "error": str(exc)})
        return self._send(404, {"error": "Not found"})


def main() -> None:
    if configured() and not config.ACCESS_PASSWORD:
        raise SystemExit("Refusing to start with PayPal credentials but no PAYPULSE_ACCESS_PASSWORD. Set a strong password to protect the merchant data and sync endpoint.")
    init_db()
    server = ThreadingHTTPServer((config.HOST, config.PORT), Handler)
    print(f"PayPulse AI running at http://{config.HOST}:{config.PORT} ({'PayPal sandbox ready' if configured() else 'demo mode'})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping PayPulse AI")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
