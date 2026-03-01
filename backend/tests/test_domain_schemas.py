from domain.schemas import (
    CitationItem,
    DocBundle,
    DocChunk,
    DocRecord,
    ExtractionResult,
    QuoteItem,
    RetrievalStatus,
    SourceRecord,
    Span,
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
