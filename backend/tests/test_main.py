from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_returns_200():
    r = client.get("/health")
    assert r.status_code == 200


def test_health_returns_ok():
    r = client.get("/health")
    assert r.json() == {"status": "ok"}


def test_analyze_returns_200():
    r = client.post("/analyze")
    assert r.status_code == 200


def test_analyze_returns_report_key():
    r = client.post("/analyze")
    data = r.json()
    assert "report" in data
    assert data["report"] is None
