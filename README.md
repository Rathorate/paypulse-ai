# PayPulse AI 🚀
*Merchant Intelligence Dashboard & Risk Monitoring Platform for the PayPal AI Hackathon 2026*

## 💡 Inspiration
Modern merchants struggle to synthesize large volumes of transaction data, risk anomalies, and customer churn signals in real time. **PayPulse AI** bridges this gap by combining PayPal payment analytics with intelligent automated monitoring, instant anomaly detection, and an interactive AI assistant designed to protect merchant revenue and prevent fraud.

## ✨ Key Features
- **Real-Time Financial Dashboard:** Tracks total payment volume, transaction counts, and 7-day volume trends instantly.
- **AI Risk & Anomaly Detection:** Flags suspicious transactions automatically with explainable risk scores and specific trigger reasons.
- **Customer Churn Intelligence:** Monitors buyer inactivity and highlights high-risk retention signals to protect recurring revenue.
- **PayPulse Assistant:** An embedded conversational AI that answers natural language queries about transactions, risk, and cash flow.
- **PayPal Sandbox Sync:** Seamlessly simulates real-time data ingestion and synchronization with payment gateways.

## 🛠️ Tech Stack
- **Frontend:** HTML5, Tailwind CSS, Modern JavaScript (Vanilla ES6), FontAwesome icons.
- **Backend:** FastAPI (Python 3.12), Pydantic, Uvicorn, CORS Middleware.
- **Environment:** Containerized REST architecture supporting local development and secure API endpoints.

## 🚀 Getting Started

### 1. Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pydantic
```

### 2. Run the Backend API
```bash
uvicorn app.main:app --reload --port 8001
```

### 3. Run the Frontend Static Server
In a separate terminal window:
```bash
cd web
python3 -m http.server 3000
```
Open **`http://localhost:3000`** in your browser to view the dashboard!
