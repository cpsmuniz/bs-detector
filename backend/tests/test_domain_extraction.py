import pytest

from domain.extraction import (
    MOTION_ID,
    build_bundle,
    link_quote_to_citation,
    run,
)
from domain.schemas import DocBundle, DocRecord, Span
from infrastructure.doc_loader import load_case_docs


def test_link_quote_to_citation_empty_returns_none():
    assert link_quote_to_citation([], 10, "some text") is None


def test_link_quote_to_citation_citation_not_in_text_returns_none(make_citation):
    c = make_citation("c1", "Never In Text")
    assert link_quote_to_citation([c], 0, "other text") is None


def test_link_quote_to_citation_returns_nearest_before(make_citation):
    c1 = make_citation("c1", "First")
    c2 = make_citation("c2", "Second")
    text = "First xxx Second"
    assert link_quote_to_citation([c1, c2], 3, text) == "c1"


def test_link_quote_to_citation_returns_nearest_after(make_citation):
    c1 = make_citation("c1", "First")
    c2 = make_citation("c2", "Second")
    text = "First xxx Second"
    assert link_quote_to_citation([c1, c2], 11, text) == "c2"


def test_build_bundle_empty_docs_raises():
    with pytest.raises(ValueError, match="No documents"):
        build_bundle({})


def test_build_bundle_missing_motion_raises():
    with pytest.raises(ValueError, match="Missing motion"):
        build_bundle({"other": "text"})


def test_build_bundle_success():
    docs = load_case_docs()
    bundle = build_bundle(docs)
    assert isinstance(bundle, DocBundle)
    assert bundle.motion_document_id == MOTION_ID
    assert any(d.id == MOTION_ID for d in bundle.documents)
    for r in bundle.documents:
        assert isinstance(r, DocRecord)
        assert r.text
        assert len(r.chunks) >= 0


def test_run_returns_extraction_result():
    docs = load_case_docs()
    bundle = build_bundle(docs)
    result = run(bundle)
    assert len(result.citations) >= 1
    assert len(result.quotes) >= 1


def test_run_citation_has_required_fields():
    docs = load_case_docs()
    bundle = build_bundle(docs)
    result = run(bundle)
    for c in result.citations:
        assert c.id
        assert c.raw_citation
        assert c.normalized_citation
        assert c.motion_span


def test_run_quote_has_required_fields():
    docs = load_case_docs()
    bundle = build_bundle(docs)
    result = run(bundle)
    for q in result.quotes:
        assert q.id
        assert q.quote_text
        assert q.motion_span
