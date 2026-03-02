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


def test_analyze_returns_report_with_expected_keys():
    r = client.post("/analyze")
    data = r.json()
    assert "report" in data
    report = data["report"]
    assert report is not None
    assert "citation_findings" in report
    assert "quote_findings" in report
    assert "cross_document_findings" in report
    assert "findings" in report
    assert "judicial_memo" in report
    assert "errors" in report
    assert "timings_ms" in report


def test_analyze_accepts_use_web_retrieval_false():
    r = client.post("/analyze", json={"use_web_retrieval": False})
    assert r.status_code == 200
    assert "report" in r.json()


def test_analyze_accepts_use_web_retrieval_true():
    r = client.post("/analyze", json={"use_web_retrieval": True})
    assert r.status_code == 200
    assert "report" in r.json()


def test_analyze_accepts_empty_body():
    r = client.post("/analyze", json={})
    assert r.status_code == 200
    assert "report" in r.json()
