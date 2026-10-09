import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200

def test_get_summary():
    response = client.get("/api/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_volume" in data or "volume" in data

def test_get_anomalies():
    response = client.get("/api/anomalies")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_churn():
    response = client.get("/api/churn")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_ai_chat():
    response = client.post("/api/chat", json={"message": "Summarize my volume"})
    assert response.status_code == 200
    assert "response" in response.json() or "reply" in response.json() or "message" in response.json()

