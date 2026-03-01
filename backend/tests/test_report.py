from domain.enums import CrossDocLabel, FindingKind, QuoteLabel, SupportLabel
from domain.schemas import (
    CrossDocAssessment,
    ExtractionResult,
    QuoteAssessment,
    SourceRecord,
    Span,
    SupportAssessment,
    VerificationReport,
)
from application.report import build_report


def _minimal_extraction() -> ExtractionResult:
    return ExtractionResult(citations=[], quotes=[])


def _minimal_sources() -> list[SourceRecord]:
    return []


def test_build_report_returns_verification_report():
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [],
        [],
        [],
        [],
    )
    assert isinstance(report, VerificationReport)
    assert report.citation_findings == []
    assert report.quote_findings == []
    assert report.cross_document_findings == []
    assert report.findings == []
    assert report.judicial_memo == ""
    assert report.errors == []
    assert report.timings_ms == {}


def test_build_report_includes_errors_and_timings():
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [],
        [],
        [],
        [],
        errors=["e1"],
        timings_ms={"step_a": 100.0},
    )
    assert report.errors == ["e1"]
    assert report.timings_ms == {"step_a": 100.0}


def test_build_report_support_assessment_becomes_citation_finding():
    support = SupportAssessment(
        citation_id="c1",
        label=SupportLabel.SUPPORTS,
        confidence=0.9,
        reason="Fits.",
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [support],
        [],
        [],
        [],
    )
    assert len(report.citation_findings) == 1
    f = report.citation_findings[0]
    assert f.id == "citation_c1"
    assert f.kind == FindingKind.CITATION_SUPPORT
    assert f.reference_id == "c1"
    assert f.status == "supports"
    assert f.confidence == 0.9
    assert f.confidence_reason == "Fits."
    assert len(report.findings) == 1
    assert report.findings[0] == f


def test_build_report_could_not_verify_support_gets_low_confidence():
    support = SupportAssessment(
        citation_id="c2",
        label=SupportLabel.COULD_NOT_VERIFY,
        confidence=0.5,
        reason="Missing.",
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [support],
        [],
        [],
        [],
    )
    assert report.citation_findings[0].confidence == 0.2
    assert "Could not verify" in report.citation_findings[0].confidence_reason


def test_build_report_does_not_support_gets_high_confidence():
    support = SupportAssessment(
        citation_id="c3",
        label=SupportLabel.DOES_NOT_SUPPORT,
        confidence=0.3,
        reason="Contradicted.",
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [support],
        [],
        [],
        [],
    )
    assert report.citation_findings[0].confidence >= 0.8
    assert report.citation_findings[0].confidence_reason == "Contradicted."


def test_build_report_quote_assessment_becomes_quote_finding():
    quote = QuoteAssessment(
        quote_id="q1",
        label=QuoteLabel.EXACT,
        confidence=1.0,
        reason="Match.",
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [],
        [quote],
        [],
        [],
    )
    assert len(report.quote_findings) == 1
    f = report.quote_findings[0]
    assert f.id == "quote_q1"
    assert f.kind == FindingKind.QUOTE_ACCURACY
    assert f.reference_id == "q1"
    assert f.status == "exact"
    assert f.confidence == 1.0


def test_build_report_quote_could_not_verify_low_confidence():
    quote = QuoteAssessment(
        quote_id="q2",
        label=QuoteLabel.COULD_NOT_VERIFY,
        confidence=0.5,
        reason="",
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [],
        [quote],
        [],
        [],
    )
    assert report.quote_findings[0].confidence == 0.2


def test_build_report_quote_material_difference_high_confidence():
    quote = QuoteAssessment(
        quote_id="q3",
        label=QuoteLabel.MATERIAL_DIFFERENCE,
        confidence=0.4,
        reason="Different.",
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [],
        [quote],
        [],
        [],
    )
    assert report.quote_findings[0].confidence >= 0.8


def test_build_report_cross_doc_assessment_becomes_cross_finding():
    span = Span(document_id="d", start=0, end=10, excerpt="x")
    cross = CrossDocAssessment(
        claim_id="claim_001",
        label=CrossDocLabel.SUPPORTED,
        confidence=0.85,
        reason="Doc supports.",
        evidence_spans=[span],
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [],
        [],
        [],
        [cross],
    )
    assert len(report.cross_document_findings) == 1
    f = report.cross_document_findings[0]
    assert f.id == "cross_claim_001"
    assert f.kind == FindingKind.CROSS_DOCUMENT_CONSISTENCY
    assert f.reference_id == "claim_001"
    assert f.status == "supported"
    assert f.confidence == 0.85
    assert len(f.evidence_spans) == 1
    assert f.evidence_spans[0].excerpt == "x"


def test_build_report_cross_could_not_verify_low_confidence():
    cross = CrossDocAssessment(
        claim_id="c1",
        label=CrossDocLabel.COULD_NOT_VERIFY,
        confidence=0.5,
        reason="Unknown.",
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [],
        [],
        [],
        [cross],
    )
    assert report.cross_document_findings[0].confidence == 0.2


def test_build_report_cross_contradicted_high_confidence():
    cross = CrossDocAssessment(
        claim_id="c2",
        label=CrossDocLabel.CONTRADICTED,
        confidence=0.3,
        reason="",
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [],
        [],
        [],
        [cross],
    )
    assert report.cross_document_findings[0].confidence >= 0.8
    assert "contradicted" in report.cross_document_findings[0].confidence_reason.lower()


def test_build_report_findings_is_concatenation_of_three_lists():
    support = SupportAssessment(
        citation_id="c1", label=SupportLabel.SUPPORTS, confidence=0.9, reason="Ok"
    )
    quote = QuoteAssessment(
        quote_id="q1", label=QuoteLabel.EXACT, confidence=1.0, reason="Match"
    )
    cross = CrossDocAssessment(
        claim_id="claim_1", label=CrossDocLabel.SUPPORTED, confidence=0.8, reason="Yes"
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [support],
        [quote],
        [],
        [cross],
    )
    assert len(report.citation_findings) == 1
    assert len(report.quote_findings) == 1
    assert len(report.cross_document_findings) == 1
    assert len(report.findings) == 3
    assert report.findings[0].kind == FindingKind.CITATION_SUPPORT
    assert report.findings[1].kind == FindingKind.QUOTE_ACCURACY
    assert report.findings[2].kind == FindingKind.CROSS_DOCUMENT_CONSISTENCY


def test_build_report_each_finding_has_confidence_in_01_and_reason():
    support = SupportAssessment(
        citation_id="c1", label=SupportLabel.PARTIALLY_SUPPORTS, confidence=0.6, reason="Partial."
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [support],
        [],
        [],
        [],
    )
    f = report.citation_findings[0]
    assert 0 <= f.confidence <= 1
    assert isinstance(f.confidence_reason, str)
    assert len(f.confidence_reason) > 0


def test_build_report_empty_reason_uses_fallback():
    support = SupportAssessment(
        citation_id="c1", label=SupportLabel.SUPPORTS, confidence=0.9, reason=""
    )
    report = build_report(
        _minimal_extraction(),
        _minimal_sources(),
        [support],
        [],
        [],
        [],
    )
    assert report.citation_findings[0].confidence_reason == "No reason given."
