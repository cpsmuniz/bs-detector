from domain.enums import CrossDocLabel, QuoteLabel, SupportLabel
from domain.schemas import (
    CitationItem,
    CrossDocAssessment,
    DocBundle,
    DocChunk,
    DocRecord,
    ExtractionResult,
    FactClaim,
    QuoteAssessment,
    QuoteItem,
    RetrievalStatus,
    SourceRecord,
    Span,
    SupportAssessment,
)


def test_span():
    s = Span(document_id="d", start=0, end=5, excerpt="hi")
    assert s.document_id == "d"
    assert s.excerpt == "hi"


def test_span_excerpt_optional():
    s = Span(document_id="d", start=0, end=5)
    assert s.excerpt is None


def test_doc_chunk():
    sp = Span(document_id="d", start=0, end=3, excerpt="ab")
    c = DocChunk(id="c1", span=sp, text="ab")
    assert c.id == "c1"
    assert c.span.excerpt == "ab"


def test_doc_record():
    r = DocRecord(id="r1", name="r1", text="t", chunks=[])
    assert r.chunks == []


def test_doc_bundle():
    r = DocRecord(id="motion", name="m", text="x", chunks=[])
    b = DocBundle(documents=[r], motion_document_id="motion")
    assert b.motion_document_id == "motion"


def test_citation_item():
    sp = Span(document_id="m", start=0, end=1)
    c = CitationItem(
        id="c1",
        raw_citation="Foo v. Bar",
        normalized_citation="Foo v. Bar",
        proposition_text="p",
        motion_span=sp,
    )
    assert c.needs_review is False


def test_quote_item():
    sp = Span(document_id="m", start=0, end=1)
    q = QuoteItem(id="q1", quote_text="x", proposition_text="p", motion_span=sp)
    assert q.citation_id is None


def test_extraction_result_defaults():
    e = ExtractionResult()
    assert e.citations == []
    assert e.quotes == []


def test_retrieval_status_enum_values():
    assert RetrievalStatus.FOUND.value == "found"
    assert RetrievalStatus.NOT_FOUND.value == "not_found"
    assert RetrievalStatus.ERROR.value == "error"
    assert RetrievalStatus.DISABLED.value == "disabled"


def test_source_record_with_enum():
    r = SourceRecord(
        citation_id="c1",
        normalized_citation="X (2020)",
        retrieval_status=RetrievalStatus.FOUND,
        authority_text="snippet",
    )
    assert r.retrieval_status == RetrievalStatus.FOUND
    assert r.retrieval_status.value == "found"


def test_support_label_enum():
    assert SupportLabel.SUPPORTS.value == "supports"
    assert SupportLabel.COULD_NOT_VERIFY.value == "could_not_verify"


def test_quote_label_enum():
    assert QuoteLabel.EXACT.value == "exact"
    assert QuoteLabel.MATERIAL_DIFFERENCE.value == "material_difference"


def test_cross_doc_label_enum():
    assert CrossDocLabel.SUPPORTED.value == "supported"
    assert CrossDocLabel.CONTRADICTED.value == "contradicted"


def test_support_assessment():
    sp = Span(document_id="d", start=0, end=1)
    a = SupportAssessment(citation_id="c1", label=SupportLabel.SUPPORTS, confidence=0.9, reason="Fits.")
    assert a.label == SupportLabel.SUPPORTS
    assert a.evidence_spans == []


def test_quote_assessment():
    a = QuoteAssessment(quote_id="q1", label=QuoteLabel.EXACT, confidence=1.0, reason="Match.")
    assert a.quote_id == "q1"
    assert a.label == QuoteLabel.EXACT


def test_fact_claim():
    sp = Span(document_id="m", start=0, end=10, excerpt="A fact.")
    fc = FactClaim(id="claim_001", claim_text="A fact.", claim_type="fact", motion_span=sp, source_section="Facts")
    assert fc.id == "claim_001"
    assert fc.motion_span.excerpt == "A fact."


def test_cross_doc_assessment():
    a = CrossDocAssessment(claim_id="c1", label=CrossDocLabel.SUPPORTED, confidence=0.8, reason="Doc supports.")
    assert a.claim_id == "c1"
    assert a.label == CrossDocLabel.SUPPORTED
