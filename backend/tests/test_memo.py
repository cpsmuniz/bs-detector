"""Tests for application.memo.build_memo."""

import pytest

from application.memo import _build_memo_fallback, build_memo
from domain.enums import FindingKind
from domain.schemas import Finding, JudicialMemo


def _finding(fid: str, confidence: float = 0.8, status: str = "supports", reason: str = "Evidence.") -> Finding:
    return Finding(
        id=fid,
        kind=FindingKind.CITATION_SUPPORT,
        reference_id=fid,
        status=status,
        confidence=confidence,
        confidence_reason=reason,
    )


def test_memo_has_text_and_supporting_finding_ids_subset():
    findings = [_finding("f1"), _finding("f2"), _finding("f3")]
    valid_ids = {f.id for f in findings}
    result = build_memo(
        findings,
        _is_llm_available=lambda: True,
        _call_llm_json=lambda _: {"memo_text": "A paragraph.", "supporting_finding_ids": ["f1", "f2"]},
    )
    assert result.text == "A paragraph."
    assert set(result.supporting_finding_ids) <= valid_ids
    assert result.supporting_finding_ids == ["f1", "f2"]


def test_invalid_supporting_finding_ids_are_filtered():
    findings = [_finding("f1"), _finding("f2")]
    result = build_memo(
        findings,
        _is_llm_available=lambda: True,
        _call_llm_json=lambda _: {"memo_text": "Summary.", "supporting_finding_ids": ["f1", "hallucinated_id", "f2"]},
    )
    assert result.text == "Summary."
    assert "hallucinated_id" not in result.supporting_finding_ids
    assert result.supporting_finding_ids == ["f1", "f2"]


def test_llm_fails_or_unavailable_uses_template_fallback():
    findings = [_finding("f1", 0.9), _finding("f2", 0.5)]
    result = build_memo(findings, _is_llm_available=lambda: False)
    assert result.text
    assert "Based on the review" in result.text
    assert set(result.supporting_finding_ids) <= {f.id for f in findings}


def test_llm_raises_uses_template_fallback():
    def raise_value_error(*a, **k):
        raise ValueError("LLM error")

    result = build_memo(
        [_finding("f1"), _finding("f2")],
        _is_llm_available=lambda: True,
        _call_llm_json=raise_value_error,
    )
    assert result.text
    assert "Based on the review" in result.text
    assert set(result.supporting_finding_ids) <= {"f1", "f2"}


def test_empty_findings():
    result = build_memo([])
    assert result.text == "No findings to summarize."
    assert result.supporting_finding_ids == []


def test_fallback_uses_top_findings_by_confidence():
    findings = [
        _finding("low", confidence=0.2, reason="Low."),
        _finding("high", confidence=0.95, reason="High."),
        _finding("mid", confidence=0.5, reason="Mid."),
    ]
    result = build_memo(findings, _is_llm_available=lambda: False)
    assert "Based on the review" in result.text
    assert "high" in result.supporting_finding_ids
    assert result.supporting_finding_ids[0] == "high"
    assert set(result.supporting_finding_ids) <= {f.id for f in findings}


def test_llm_returns_missing_memo_text_uses_fallback():
    result = build_memo(
        [_finding("f1")],
        _is_llm_available=lambda: True,
        _call_llm_json=lambda _: {"supporting_finding_ids": ["f1"]},
    )
    assert "Based on the review" in result.text
    assert result.supporting_finding_ids == ["f1"]


def test_llm_returns_alternative_text_key():
    result = build_memo(
        [_finding("f1")],
        _is_llm_available=lambda: True,
        _call_llm_json=lambda _: {"text": "Alternative key paragraph.", "supporting_finding_ids": ["f1"]},
    )
    assert result.text == "Alternative key paragraph."
    assert result.supporting_finding_ids == ["f1"]


def test_llm_returns_memo_text_without_supporting_finding_ids():
    result = build_memo(
        [_finding("f1")],
        _is_llm_available=lambda: True,
        _call_llm_json=lambda _: {"memo_text": "Summary with no ids."},
    )
    assert result.text == "Summary with no ids."
    assert result.supporting_finding_ids == []


def test_llm_returns_supporting_finding_ids_not_list_normalized():
    result = build_memo(
        [_finding("f1")],
        _is_llm_available=lambda: True,
        _call_llm_json=lambda _: {"memo_text": "Ok.", "supporting_finding_ids": "not-a-list"},
    )
    assert result.text == "Ok."
    assert result.supporting_finding_ids == []


def test_judicial_memo_domain_type():
    memo = JudicialMemo(text="Test.", supporting_finding_ids=["a", "b"])
    assert memo.text == "Test."
    assert memo.supporting_finding_ids == ["a", "b"]


def test_build_memo_fallback_empty_findings():
    result = _build_memo_fallback([])
    assert result.text == "No findings to summarize."
    assert result.supporting_finding_ids == []
