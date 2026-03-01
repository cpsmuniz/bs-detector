import json

import pytest

from application import verifier as verifier_module
from application.evaluation_helpers import claim_id_from, default_reason, find_cross_assessment
from application.verifier import run_phase_a, run_phase_b
from domain.schemas import (
    DocBundle,
    DocRecord,
    ExtractionResult,
    QuoteItem,
    SourceRecord,
    Span,
)
from domain.enums import RetrievalStatus, SupportLabel, QuoteLabel, CrossDocLabel
from infrastructure.prompt_loader import get_contract


def _source(citation_id: str, authority_text: str | None = "Authority snippet."):
    return SourceRecord(
        citation_id=citation_id,
        normalized_citation="X (2020)",
        retrieval_status=RetrievalStatus.FOUND if authority_text else RetrievalStatus.NOT_FOUND,
        authority_text=authority_text,
    )


def test_default_reason_empty_returns_no_reason_given():
    assert default_reason("") == "No reason given."


def test_default_reason_non_empty_returns_raw():
    assert default_reason("Ok.") == "Ok."


def test_claim_id_from_missing_returns_indexed():
    contract = get_contract()
    assert claim_id_from({}, contract, 0) == "claim_001"
    assert claim_id_from({"claim_text": "x"}, contract, 2) == "claim_003"


def test_claim_id_from_present_returns_id():
    contract = get_contract()
    assert claim_id_from({"id": "my_id"}, contract, 0) == "my_id"


def test_find_cross_assessment_missing_returns_none():
    contract = get_contract()
    assert find_cross_assessment({}, "c1", contract) is None
    assert find_cross_assessment({"assessments": []}, "c1", contract) is None
    assert find_cross_assessment({"assessments": [{"claim_id": "other"}]}, "c1", contract) is None


def test_find_cross_assessment_match_returns_assessment():
    from domain.enums import CrossDocLabel
    contract = get_contract()
    out = find_cross_assessment(
        {"assessments": [{"claim_id": "c1", "label": "supported", "confidence": 0.8, "reason": "Yes."}]},
        "c1",
        contract,
    )
    assert out is not None
    assert out.claim_id == "c1"
    assert out.label == CrossDocLabel.SUPPORTED


def test_run_phase_a_empty_extraction_returns_empty_lists():
    ext = ExtractionResult(citations=[], quotes=[])
    sources: list[SourceRecord] = []
    support, quote = run_phase_a(ext, sources)
    assert support == []
    assert quote == []


def test_run_phase_a_no_sources_all_could_not_verify(make_citation):
    c = make_citation("c1", "Foo v. Bar")
    ext = ExtractionResult(citations=[c], quotes=[])
    support, quote = run_phase_a(ext, [])
    assert len(support) == 1
    assert support[0].citation_id == "c1"
    assert support[0].label == SupportLabel.COULD_NOT_VERIFY
    assert support[0].confidence == 0.2
    assert quote == []


def test_run_phase_a_source_without_authority_could_not_verify(make_citation):
    c = make_citation("c1", "Foo")
    ext = ExtractionResult(citations=[c], quotes=[])
    sources = [_source("c1", authority_text=None)]
    sources[0].retrieval_status = RetrievalStatus.FOUND
    sources[0].authority_text = None
    support, _ = run_phase_a(ext, sources)
    assert support[0].label == SupportLabel.COULD_NOT_VERIFY


def test_run_phase_a_source_with_authority_llm_unavailable_fills_fallback(make_citation):
    c = make_citation("c1", "Foo")
    ext = ExtractionResult(citations=[c], quotes=[])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: False)
    try:
        support, _ = run_phase_a(ext, sources)
        assert len(support) == 1
        assert support[0].label == SupportLabel.COULD_NOT_VERIFY
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_support_assessment_without_citation_id_skipped(make_citation):
    c = make_citation("c1", "Foo")
    ext = ExtractionResult(citations=[c], quotes=[])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"label": "supports", "confidence": 0.9, "reason": "Fits."}], "quote_assessments": []},
    )
    try:
        support, _ = run_phase_a(ext, sources)
        assert support[0].label == SupportLabel.COULD_NOT_VERIFY
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_returns_support_assessments(make_citation):
    c = make_citation("c1", "Foo")
    ext = ExtractionResult(citations=[c], quotes=[])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "supports", "confidence": 0.9, "reason": "Fits."}], "quote_assessments": []},
    )
    try:
        support, quote = run_phase_a(ext, sources)
        assert len(support) == 1
        assert support[0].label == SupportLabel.SUPPORTS
        assert support[0].confidence == 0.9
        assert quote == []
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_returns_invalid_quote_label_maps_to_could_not_verify(make_citation):
    c = make_citation("c1", "Foo")
    q = QuoteItem(id="q1", quote_text="Exact.", citation_id="c1", proposition_text="p", motion_span=Span(document_id="m", start=0, end=1))
    ext = ExtractionResult(citations=[c], quotes=[q])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "supports", "confidence": 0.8, "reason": "Ok"}], "quote_assessments": [{"quote_id": "q1", "label": "bad_label", "confidence": 0.5, "reason": "X"}]},
    )
    try:
        _, quote = run_phase_a(ext, sources)
        assert quote[0].label == QuoteLabel.COULD_NOT_VERIFY
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_quote_assessment_without_quote_id_skipped(make_citation):
    c = make_citation("c1", "Foo")
    q = QuoteItem(id="q1", quote_text="X", citation_id="c1", proposition_text="p", motion_span=Span(document_id="m", start=0, end=1))
    ext = ExtractionResult(citations=[c], quotes=[q])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "supports", "confidence": 0.8, "reason": "Ok"}], "quote_assessments": [{"label": "exact", "confidence": 1.0, "reason": "Match."}]},
    )
    try:
        _, quote = run_phase_a(ext, sources)
        assert quote[0].label == QuoteLabel.COULD_NOT_VERIFY
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_returns_quote_assessments(make_citation):
    c = make_citation("c1", "Foo")
    q = QuoteItem(id="q1", quote_text="Exact quote.", citation_id="c1", proposition_text="p", motion_span=Span(document_id="m", start=0, end=1))
    ext = ExtractionResult(citations=[c], quotes=[q])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "supports", "confidence": 0.8, "reason": "Ok"}], "quote_assessments": [{"quote_id": "q1", "label": "exact", "confidence": 1.0, "reason": "Match."}]},
    )
    try:
        support, quote = run_phase_a(ext, sources)
        assert len(quote) == 1
        assert quote[0].quote_id == "q1"
        assert quote[0].label == QuoteLabel.EXACT
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_invalid_json_fallback(make_citation):
    c = make_citation("c1", "Foo")
    ext = ExtractionResult(citations=[c], quotes=[])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(verifier_module.llm_module, "call_llm_json", lambda _: None)
    try:
        support, _ = run_phase_a(ext, sources)
        assert support[0].label == SupportLabel.COULD_NOT_VERIFY
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_raises_fallback(make_citation):
    c = make_citation("c1", "Foo")
    ext = ExtractionResult(citations=[c], quotes=[])
    sources = [_source("c1")]

    def raise_value_error(_):
        raise ValueError("bad")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(verifier_module.llm_module, "call_llm_json", raise_value_error)
    try:
        support, _ = run_phase_a(ext, sources)
        assert support[0].label == SupportLabel.COULD_NOT_VERIFY
    finally:
        monkeypatch.undo()


def test_run_phase_b_no_motion_returns_empty():
    r = DocRecord(id="other", name="other", text="x", chunks=[])
    bundle = DocBundle(documents=[r], motion_document_id="motion_for_summary_judgment")
    claims, cross = run_phase_b(bundle)
    assert claims == []
    assert cross == []


def test_run_phase_b_llm_unavailable_returns_empty_claims():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="The plaintiff stated facts.", chunks=[])
    bundle = DocBundle(documents=[r], motion_document_id="motion_for_summary_judgment")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: False)
    try:
        claims, cross = run_phase_b(bundle)
        assert claims == []
        assert cross == []
    finally:
        monkeypatch.undo()


def test_run_phase_b_llm_claims_non_dict_item_skipped():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="Facts.", chunks=[])
    bundle = DocBundle(documents=[r], motion_document_id="motion_for_summary_judgment")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"claims": ["not a dict", {"id": "c1", "claim_text": "Fact.", "claim_type": "fact", "source_section": "Facts"}]},
    )
    try:
        claims, _ = run_phase_b(bundle)
        assert len(claims) == 1
        assert claims[0].id == "c1"
    finally:
        monkeypatch.undo()


def test_run_phase_b_llm_returns_claims_and_assessments():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="The plaintiff stated facts.", chunks=[])
    other = DocRecord(id="police", name="p", text="Report.", chunks=[])
    bundle = DocBundle(documents=[r, other], motion_document_id="motion_for_summary_judgment")
    call_count = [0]

    def mock_llm(msgs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"claims": [{"id": "claim_001", "claim_text": "A fact.", "claim_type": "fact", "source_section": "Facts", "motion_span": {"document_id": "m", "start": 0, "end": 10, "excerpt": "A fact."}}]}
        return {"assessments": [{"claim_id": "claim_001", "label": "supported", "confidence": 0.85, "reason": "Doc supports."}]}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(verifier_module.llm_module, "call_llm_json", mock_llm)
    try:
        claims, cross = run_phase_b(bundle)
        assert len(claims) == 1
        assert claims[0].id == "claim_001"
        assert claims[0].claim_text == "A fact."
        assert len(cross) == 1
        assert cross[0].claim_id == "claim_001"
        assert cross[0].label == CrossDocLabel.SUPPORTED
    finally:
        monkeypatch.undo()


def test_run_phase_b_llm_claims_no_assessment_returns_could_not_verify():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="Facts.", chunks=[])
    other = DocRecord(id="police", name="police", text="Report.", chunks=[])
    bundle = DocBundle(documents=[r, other], motion_document_id="motion_for_summary_judgment")
    call_count = [0]

    def mock_llm(msgs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"claims": [{"id": "c1", "claim_text": "X", "claim_type": "fact", "source_section": "Facts"}]}
        return {"assessments": []}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(verifier_module.llm_module, "call_llm_json", mock_llm)
    try:
        claims, cross = run_phase_b(bundle)
        assert len(claims) == 1
        assert len(cross) == 1
        assert cross[0].label == CrossDocLabel.COULD_NOT_VERIFY
        assert cross[0].reason == "No assessment returned."
    finally:
        monkeypatch.undo()


def test_run_phase_b_llm_claims_raises_returns_empty_claims():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="Facts.", chunks=[])
    bundle = DocBundle(documents=[r], motion_document_id="motion_for_summary_judgment")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(verifier_module.llm_module, "call_llm_json", lambda _: (_ for _ in ()).throw(json.JSONDecodeError("x", "y", 0)))
    try:
        claims, cross = run_phase_b(bundle)
        assert claims == []
        assert cross == []
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_returns_invalid_label_maps_to_could_not_verify(make_citation):
    c = make_citation("c1", "Foo")
    ext = ExtractionResult(citations=[c], quotes=[])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "invalid_label", "confidence": 0.5, "reason": "X"}], "quote_assessments": []},
    )
    try:
        support, _ = run_phase_a(ext, sources)
        assert support[0].label == SupportLabel.COULD_NOT_VERIFY
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_missing_confidence_uses_default(make_citation):
    c = make_citation("c1", "Foo")
    ext = ExtractionResult(citations=[c], quotes=[])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "supports", "reason": "Ok"}], "quote_assessments": []},
    )
    try:
        support, _ = run_phase_a(ext, sources)
        assert support[0].confidence == 0.2
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_returns_non_numeric_confidence_uses_default(make_citation):
    c = make_citation("c1", "Foo")
    ext = ExtractionResult(citations=[c], quotes=[])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "supports", "confidence": "high", "reason": "X"}], "quote_assessments": []},
    )
    try:
        support, _ = run_phase_a(ext, sources)
        assert support[0].confidence == 0.2
    finally:
        monkeypatch.undo()


def test_run_phase_a_quote_with_source_no_authority_gets_could_not_verify(make_citation):
    c = make_citation("c1", "Foo")
    q = QuoteItem(id="q1", quote_text="A quote.", citation_id="c1", proposition_text="p", motion_span=Span(document_id="m", start=0, end=1))
    ext = ExtractionResult(citations=[c], quotes=[q])
    src = _source("c1", authority_text=None)
    src.retrieval_status = RetrievalStatus.FOUND
    sources = [src]
    _, quote = run_phase_a(ext, sources)
    assert len(quote) == 1
    assert quote[0].label == QuoteLabel.COULD_NOT_VERIFY


def test_run_phase_a_llm_empty_reason_uses_no_reason_given(make_citation):
    c = make_citation("c1", "Foo")
    ext = ExtractionResult(citations=[c], quotes=[])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "supports", "confidence": 0.9, "reason": ""}], "quote_assessments": []},
    )
    try:
        support, _ = run_phase_a(ext, sources)
        assert support[0].reason == "No reason given."
    finally:
        monkeypatch.undo()


def test_run_phase_a_llm_empty_quote_reason_uses_no_reason_given(make_citation):
    c = make_citation("c1", "Foo")
    q = QuoteItem(id="q1", quote_text="Q", citation_id="c1", proposition_text="p", motion_span=Span(document_id="m", start=0, end=1))
    ext = ExtractionResult(citations=[c], quotes=[q])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "supports", "confidence": 0.8, "reason": "Ok"}], "quote_assessments": [{"quote_id": "q1", "label": "exact", "confidence": 1.0, "reason": ""}]},
    )
    try:
        _, quote = run_phase_a(ext, sources)
        assert quote[0].reason == "No reason given."
    finally:
        monkeypatch.undo()


def test_run_phase_a_two_quotes_llm_returns_one_fills_other_fallback(make_citation):
    c = make_citation("c1", "Foo")
    q1 = QuoteItem(id="q1", quote_text="One", citation_id="c1", proposition_text="p", motion_span=Span(document_id="m", start=0, end=1))
    q2 = QuoteItem(id="q2", quote_text="Two", citation_id="c1", proposition_text="p", motion_span=Span(document_id="m", start=2, end=3))
    ext = ExtractionResult(citations=[c], quotes=[q1, q2])
    sources = [_source("c1")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "supports", "confidence": 0.8, "reason": "Ok"}], "quote_assessments": [{"quote_id": "q1", "label": "exact", "confidence": 1.0, "reason": "Match."}]},
    )
    try:
        _, quote = run_phase_a(ext, sources)
        assert len(quote) == 2
        assert quote[0].label == QuoteLabel.EXACT
        assert quote[1].label == QuoteLabel.COULD_NOT_VERIFY
    finally:
        monkeypatch.undo()


def test_run_phase_a_two_citations_llm_returns_one_fills_other_fallback(make_citation):
    c1 = make_citation("c1", "Foo")
    c2 = make_citation("c2", "Bar")
    ext = ExtractionResult(citations=[c1, c2], quotes=[])
    sources = [_source("c1"), _source("c2")]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"support_assessments": [{"citation_id": "c1", "label": "supports", "confidence": 0.9, "reason": "Ok"}], "quote_assessments": []},
    )
    try:
        support, _ = run_phase_a(ext, sources)
        assert len(support) == 2
        assert support[0].label == SupportLabel.SUPPORTS
        assert support[1].label == SupportLabel.COULD_NOT_VERIFY
    finally:
        monkeypatch.undo()


def test_run_phase_b_claim_without_id_uses_index():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="Facts.", chunks=[])
    bundle = DocBundle(documents=[r], motion_document_id="motion_for_summary_judgment")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"claims": [{"claim_text": "Fact.", "claim_type": "fact", "source_section": "Facts"}]},
    )
    try:
        claims, _ = run_phase_b(bundle)
        assert len(claims) == 1
        assert claims[0].id == "claim_001"
    finally:
        monkeypatch.undo()


def test_run_phase_b_cross_doc_llm_raises_gets_verification_failed():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="Facts.", chunks=[])
    other = DocRecord(id="p", name="p", text="Doc.", chunks=[])
    bundle = DocBundle(documents=[r, other], motion_document_id="motion_for_summary_judgment")
    call_count = [0]

    def mock_llm(msgs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"claims": [{"id": "c1", "claim_text": "X", "claim_type": "fact", "source_section": "Facts"}]}
        raise ValueError("LLM error")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(verifier_module.llm_module, "call_llm_json", mock_llm)
    try:
        claims, cross = run_phase_b(bundle)
        assert len(cross) == 1
        assert cross[0].reason == "Verification failed."
    finally:
        monkeypatch.undo()


def test_run_phase_b_cross_doc_no_matching_assessment_gets_could_not_verify():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="Facts.", chunks=[])
    other = DocRecord(id="p", name="p", text="Doc.", chunks=[])
    bundle = DocBundle(documents=[r, other], motion_document_id="motion_for_summary_judgment")
    call_count = [0]

    def mock_llm(msgs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"claims": [{"id": "claim_001", "claim_text": "X", "claim_type": "fact", "source_section": "Facts"}]}
        return {"assessments": [{"claim_id": "wrong_id", "label": "supported", "confidence": 0.9, "reason": "Y"}]}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(verifier_module.llm_module, "call_llm_json", mock_llm)
    try:
        claims, cross = run_phase_b(bundle)
        assert len(cross) == 1
        assert cross[0].label == CrossDocLabel.COULD_NOT_VERIFY
        assert cross[0].reason == "No assessment returned."
    finally:
        monkeypatch.undo()


def test_run_phase_b_cross_doc_invalid_label_maps_to_could_not_verify():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="Facts.", chunks=[])
    other = DocRecord(id="p", name="p", text="Doc.", chunks=[])
    bundle = DocBundle(documents=[r, other], motion_document_id="motion_for_summary_judgment")
    call_count = [0]

    def mock_llm(msgs):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"claims": [{"id": "c1", "claim_text": "X", "claim_type": "fact", "source_section": "Facts"}]}
        return {"assessments": [{"claim_id": "c1", "label": "invalid", "confidence": 0.5, "reason": "Y"}]}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(verifier_module.llm_module, "call_llm_json", mock_llm)
    try:
        claims, cross = run_phase_b(bundle)
        assert len(cross) == 1
        assert cross[0].label == CrossDocLabel.COULD_NOT_VERIFY
    finally:
        monkeypatch.undo()


def test_run_phase_b_claim_with_explicit_id():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="Facts.", chunks=[])
    bundle = DocBundle(documents=[r], motion_document_id="motion_for_summary_judgment")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"claims": [{"id": "my_custom_id", "claim_text": "Fact.", "claim_type": "fact", "source_section": "Facts"}]},
    )
    try:
        claims, _ = run_phase_b(bundle)
        assert len(claims) == 1
        assert claims[0].id == "my_custom_id"
    finally:
        monkeypatch.undo()


def test_run_phase_b_claim_without_motion_span_uses_default_span():
    r = DocRecord(id="motion_for_summary_judgment", name="m", text="Facts.", chunks=[])
    bundle = DocBundle(documents=[r], motion_document_id="motion_for_summary_judgment")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(verifier_module.llm_module, "is_llm_available", lambda: True)
    monkeypatch.setattr(
        verifier_module.llm_module,
        "call_llm_json",
        lambda _: {"claims": [{"id": "c1", "claim_text": "Something.", "claim_type": "fact", "source_section": "Facts"}]},
    )
    try:
        claims, _ = run_phase_b(bundle)
        assert len(claims) == 1
        assert claims[0].motion_span.document_id == "motion_for_summary_judgment"
        assert claims[0].motion_span.excerpt == "Something."[:500]
    finally:
        monkeypatch.undo()
