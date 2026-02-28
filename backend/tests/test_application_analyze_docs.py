from application.analyze_docs import analyze_documents


def test_analyze_documents_returns_report_key():
    out = analyze_documents()
    assert isinstance(out, dict)
    assert "report" in out
    assert out["report"] is None
