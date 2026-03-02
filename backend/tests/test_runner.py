"""Tests for application.runner.run_pipeline."""

from pathlib import Path

import pytest

from application.runner import (
    _step_memo,
    _step_phase_a,
    _step_phase_b,
    run_pipeline,
)
from domain.schemas import VerificationReport


def test_run_pipeline_returns_verification_report():
    report = run_pipeline(use_web_retrieval=False)
    assert isinstance(report, VerificationReport)
    assert hasattr(report, "citation_findings")
    assert hasattr(report, "quote_findings")
    assert hasattr(report, "cross_document_findings")
    assert hasattr(report, "findings")
    assert hasattr(report, "judicial_memo")
    assert hasattr(report, "errors")
    assert hasattr(report, "timings_ms")


def test_run_pipeline_timings_populated():
    report = run_pipeline(use_web_retrieval=False)
    assert isinstance(report.timings_ms, dict)
    assert "load_docs" in report.timings_ms
    assert "extract" in report.timings_ms
    assert "sources" in report.timings_ms
    assert "report" in report.timings_ms
    assert "memo" in report.timings_ms


def test_run_pipeline_judicial_memo_set_when_findings():
    report = run_pipeline(use_web_retrieval=False)
    assert isinstance(report.judicial_memo, str)
    if report.findings:
        assert len(report.judicial_memo) > 0


def test_run_pipeline_empty_docs_dir_returns_report_with_errors(tmp_path):
    report = run_pipeline(docs_dir=tmp_path, use_web_retrieval=False)
    assert isinstance(report, VerificationReport)
    assert report.citation_findings == []
    assert report.quote_findings == []
    assert report.cross_document_findings == []
    assert report.findings == []
    assert report.judicial_memo == ""
    assert len(report.errors) > 0
    assert "load_docs" in report.timings_ms or "extract" in report.timings_ms


def test_run_pipeline_missing_motion_returns_report_with_errors(tmp_path):
    (tmp_path / "other_doc.txt").write_text("Some text.")
    report = run_pipeline(docs_dir=tmp_path, use_web_retrieval=False)
    assert isinstance(report, VerificationReport)
    assert len(report.errors) > 0
    assert report.findings == []


def test_run_pipeline_extract_failure_recorded_in_errors():
    report = run_pipeline(docs_dir=Path("/nonexistent_empty_dir"), use_web_retrieval=False)
    assert isinstance(report, VerificationReport)
    assert len(report.errors) >= 1
    assert report.findings == []
    assert report.timings_ms.get("load_docs") is not None


def test_run_pipeline_report_step_failure_returns_minimal_report(monkeypatch):
    from application import report as report_module

    def build_report_raise(*a, **k):
        raise RuntimeError("build_report failed")

    monkeypatch.setattr(report_module, "build_report", build_report_raise)
    report = run_pipeline(use_web_retrieval=False)
    assert isinstance(report, VerificationReport)
    assert any("report" in e for e in report.errors)
    assert report.citation_findings == []
    assert report.findings == []
    assert report.judicial_memo == ""


def test_run_pipeline_load_docs_failure_propagates_none_through_steps(monkeypatch):
    from infrastructure import doc_loader as doc_loader_module

    def load_raise(*a, **k):
        raise OSError("load failed")

    monkeypatch.setattr(doc_loader_module, "load_case_docs", load_raise)
    report = run_pipeline(use_web_retrieval=False)
    assert isinstance(report, VerificationReport)
    assert any("load_docs" in e for e in report.errors)
    assert report.findings == []
    assert report.judicial_memo == ""
    assert "report" in report.timings_ms
    assert "memo" in report.timings_ms


def test_step_phase_a_with_none_extraction_stores_empty_tuple():
    """Covers phase_a branch when extraction or sources is None."""
    ctx = {"extraction": None, "sources": []}
    _step_phase_a(ctx)
    assert ctx["phase_a"] == ([], [])


def test_step_phase_a_with_none_sources_stores_empty_tuple():
    """Covers phase_a branch when sources is None."""
    from domain.schemas import ExtractionResult

    ctx = {"extraction": ExtractionResult(), "sources": None}
    _step_phase_a(ctx)
    assert ctx["phase_a"] == ([], [])


def test_step_phase_b_with_none_bundle_stores_empty_tuple():
    """Covers phase_b branch when bundle is None."""
    ctx = {"bundle": None}
    _step_phase_b(ctx)
    assert ctx["phase_b"] == ([], [])


def test_step_memo_with_empty_findings_skips_build_memo():
    """Covers memo branch when report has no findings."""
    report = VerificationReport(errors=[], timings_ms={})
    assert report.findings == []
    ctx = {"report": report}
    _step_memo(ctx)
    assert report.judicial_memo == ""


def test_step_phase_a_with_extraction_and_sources_calls_verifier(monkeypatch):
    """Covers phase_a success path (lines 58-59): run_phase_a called and result stored."""
    from domain.schemas import ExtractionResult

    out = ([], [])
    def fake_run_phase_a(*a, **k):
        return out

    from application import verifier as verifier_module
    monkeypatch.setattr(verifier_module, "run_phase_a", fake_run_phase_a)
    ctx = {"extraction": ExtractionResult(), "sources": []}
    _step_phase_a(ctx)
    assert ctx["phase_a"] == out


def test_step_phase_b_with_bundle_calls_verifier(monkeypatch):
    """Covers phase_b success path (lines 67-69): run_phase_b called and result stored."""
    from domain.schemas import DocBundle, DocRecord

    out = ([], [])
    def fake_run_phase_b(*a, **k):
        return out

    from application import verifier as verifier_module
    monkeypatch.setattr(verifier_module, "run_phase_b", fake_run_phase_b)
    rec = DocRecord(id="m", name="m", text="x")
    bundle = DocBundle(documents=[rec], motion_document_id="m")
    ctx = {"bundle": bundle}
    _step_phase_b(ctx)
    assert ctx["phase_b"] == out


def test_step_memo_with_findings_builds_memo(monkeypatch):
    """Covers memo success path (lines 103-104): build_memo called and judicial_memo set."""
    from domain.enums import FindingKind
    from domain.schemas import Finding

    class FakeMemo:
        text = "fake memo"

    def fake_build_memo(*a, **k):
        return FakeMemo()

    from application import memo as memo_module
    monkeypatch.setattr(memo_module, "build_memo", fake_build_memo)
    finding = Finding(
        id="f1",
        kind=FindingKind.CITATION_SUPPORT,
        reference_id="c1",
        status="supported",
        confidence=0.9,
        confidence_reason="x",
    )
    report = VerificationReport(errors=[], timings_ms={}, findings=[finding])
    ctx = {"report": report}
    _step_memo(ctx)
    assert report.judicial_memo == "fake memo"
