# PayPulse AI

PayPulse AI is a merchant intelligence dashboard that turns PayPal payment activity into anomaly alerts, customer retention signals, and plain-language answers. It includes a working local demo that needs no credentials and a PayPal sandbox reporting integration activated with credentials.

## Run it

Requirements: Python 3.10 or newer. No package installation is required.

```powershell
python -m app.server
```

Open <http://127.0.0.1:8000>. The first run creates `data/paypulse.db` and inserts clearly labeled demo payments. Use **Sync PayPal** after adding sandbox credentials to `.env` (see below). The demo dataset remains available without external services.

## PayPal sandbox setup

1. Create a PayPal Developer account and a sandbox REST app.
2. Copy `.env.example` to `.env` and set `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` from the sandbox app. Also set a strong `PAYPULSE_ACCESS_PASSWORD`; the app refuses to start with PayPal credentials unless dashboard access is protected. Keep `.env` private; it is ignored by Git.
3. Restart PayPulse AI and choose **Sync PayPal**. The backend obtains an OAuth token and requests completed transactions from PayPal's sandbox reporting API. Your credentials never reach the browser.
4. A successful sync imports/updates matching transactions. With no keys, the dashboard stays in demo mode and the Sync button explains how to enable PayPal.

`PAYPAL_BASE_URL` defaults to `https://api-m.sandbox.paypal.com`; do not switch it to production for a hackathon demo. `PAYPAL_START_DATE` (optional) sets an RFC3339 lower bound; otherwise the last 30 days are requested.

If `PAYPULSE_ACCESS_PASSWORD` is set, the browser asks for HTTP Basic Authentication before showing the dashboard or data APIs. The username can be any value; use the configured password. `/api/health` stays public for deployment health checks and reports no transaction information. Do not deploy real merchant data without setting this password and using HTTPS.

## Run on Ubuntu / WSL

The application is portable Python and SQLite; WSL uses the same source and commands.

1. Install WSL and Ubuntu from an elevated Windows PowerShell if they are not installed: `wsl --install -d Ubuntu`. Restart if Windows requests it, then launch Ubuntu and create your Linux username.
2. In Ubuntu, install Git and Python: `sudo apt update && sudo apt install -y python3 git`.
3. Open the project from its Windows-mounted path (adjust the Windows username if needed):

   ```bash
   cd "/mnt/c/Users/l2e/Documents/Codex/2026-10-06/https-paypalaihackathon-devpost-com-https-paypalaihackathon"
   ```

4. Start the app with `python3 -m app.server`, then open <http://127.0.0.1:8000> in Windows. WSL 2 forwards localhost ports to Windows.
5. In another Ubuntu terminal, run `python3 -m unittest discover -s tests -v`.

For best Linux filesystem performance, you can clone the GitHub repository into your Ubuntu home directory instead of running from `/mnt/c`; either location works.

## Publish the code to GitHub

1. Sign in to GitHub and create a **new empty public repository** named `paypulse-ai`. Do not initialize it with a README, license, or `.gitignore`; these files are already in this project.
2. In Ubuntu/WSL, go to the project folder and run:

   ```bash
   git init -b main
   git add .
   git status
   git commit -m "Build PayPulse AI merchant intelligence app"
   git remote add origin https://github.com/YOUR_GITHUB_USERNAME/paypulse-ai.git
   git push -u origin main
   ```

3. Replace `YOUR_GITHUB_USERNAME` with your account name. Authenticate when Git prompts you; GitHub requires browser-based authentication, GitHub CLI, or a credential manager rather than your account password. Never paste a personal access token into a command or commit it.
4. Verify the repository is public and that `README.md`, `LICENSE`, `render.yaml`, `app/`, `web/`, `tests/`, and `scripts/` appear on GitHub. `.env` and the local database are excluded by `.gitignore`.

For later updates, use `git add .`, `git commit -m "Describe the change"`, and `git push`.

## Deploy to Render

This repository includes [`render.yaml`](render.yaml) for a Render Blueprint. It configures a Python web service, health check, sandbox-only PayPal base URL, and a persistent disk for SQLite. Render web services need to listen on `0.0.0.0` and their assigned `PORT`; the app reads both settings. A persistent disk requires a paid web service plan, and disk-backed services have some deploy limitations; see Render's current plan and disk documentation before creating the service.

1. Push the project to GitHub using the steps above.
2. Create/sign in to a Render account, choose **New → Blueprint**, and connect the public `paypulse-ai` GitHub repository.
3. Review the `render.yaml` plan and persistent-disk cost in Render's confirmation screen, then create the Blueprint. The deployment may take a few minutes.
4. Set a strong `PAYPULSE_ACCESS_PASSWORD` when Render prompts for the secret. After the first deploy, open the service's **Environment** settings and enter the PayPal sandbox `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`. Do not put credentials or the access password in `render.yaml` or GitHub. The service already points at PayPal's sandbox endpoint.
5. Wait for deploy to finish, then open the generated `https://paypulse-ai.onrender.com` URL. Confirm `/api/health` reports `paypal_sandbox` after credentials are set, and press **Sync PayPal** in the dashboard.
6. If testing without PayPal keys, leave the secret variables unset; demo mode still works. Keep the persistent disk if you need locally imported PayPal records to survive redeploys.

For each code update, push to `main` and Render will deploy the new commit if auto-deploy is enabled. Check the Render deploy log and `/api/health` after each deploy.

## AI and data behavior

Anomaly detection uses robust median/MAD amount scoring, fee ratio, and recent payer velocity, so the core AI workflow works offline and can be tested with deterministic data. Churn risk combines recency and purchase frequency. The assistant maps common merchant questions to validated database queries and returns explanations plus matching transactions; it does not execute generated SQL or move money. No LLM key is needed. This keeps the demo reproducible while preserving an explicit, inspectable AI decision path.

## Verification

Run all backend and database checks:

```powershell
python -m unittest discover -s tests -v
```

Run the live HTTP smoke check:

```powershell
python -m app.server
# in another terminal
python scripts/smoke_check.py
```

Tests use temporary SQLite databases and a mocked PayPal HTTP response; they never need real credentials or make real network requests.

## API

- `GET /api/health` service and PayPal configuration status
- `GET /api/summary` KPIs and daily payment totals
- `GET /api/transactions?search=&status=&risk=` filtered payment log
- `GET /api/anomalies` scored anomalies and reasons
- `GET /api/churn` customer retention risk
- `POST /api/chat` `{ "message": "Show me high-risk payments over $200" }`
- `POST /api/sync` fetch sandbox transactions or explain missing credentials

## Demo walkthrough

1. Open the dashboard and review the seeded payment activity and risk cards.
2. Select **Anomalies** and inspect the highlighted high-value or unusual-fee rows and their reasons.
3. Open **AI assistant** and ask “Show me high-risk payments over $200” or “Which customers may churn?”.
4. Show that answers cite matching records and that queries are read-only.
5. Add sandbox credentials and press **Sync PayPal** to demonstrate a real PayPal API round trip.

## Submission checklist

The Devpost submission separately needs a public source repository, a license, project description/tools, and a public YouTube demo video under three minutes. This repository includes an MIT license. Publish it publicly and record/upload the walkthrough before submitting.

## Safety

PayPulse AI only reads transaction reports and stores local merchant analytics. It does not initiate, refund, or reverse payments. Keep secrets out of source control and use sandbox credentials only.
