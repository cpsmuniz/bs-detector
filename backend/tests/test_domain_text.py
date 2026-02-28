import pytest

from domain.schemas import Span
from domain.text import (
    citation_to_key,
    chunk_by_paragraph,
    collapse_whitespace,
    span_around,
)


def test_collapse_whitespace():
    assert collapse_whitespace("  a  b  \n  c  ") == "a b c"
    assert collapse_whitespace("x") == "x"
    assert collapse_whitespace("") == ""


def test_citation_to_key():
    assert citation_to_key("  Foo v. Bar , 123 (2020).  ") == "Foo v. Bar , 123 (2020)"
    assert citation_to_key("x;") == "x"


def test_span_around_single_sentence():
    text = "One. Two. Three."
    s = span_around(text, 5, 8, "doc1")
    assert s.document_id == "doc1"
    assert s.start <= 5 and s.end >= 8
    assert "Two" in (s.excerpt or "")


def test_span_around_at_start():
    text = "First. Second."
    s = span_around(text, 0, 5, "d")
    assert s.start == 0
    assert s.end >= 5


def test_span_around_no_period_uses_newline():
    text = "Line one\nLine two\n"
    s = span_around(text, 0, 7, "d")
    assert s.document_id == "d"
    assert s.excerpt


def test_span_around_empty_excerpt_falls_back():
    text = "x"
    s = span_around(text, 0, 1, "d")
    assert s.excerpt == "x" or s.excerpt


def test_span_around_excerpt_capped_500():
    text = "a" * 600 + ". End."
    s = span_around(text, 0, 600, "d")
    assert s.excerpt is None or len(s.excerpt) <= 500


def test_chunk_by_paragraph_empty():
    assert chunk_by_paragraph("", "doc") == []


def test_chunk_by_paragraph_single_short():
    out = chunk_by_paragraph("Hello world.", "d")
    assert len(out) == 1
    start, end, raw = out[0]
    assert raw == "Hello world."
    assert start >= 0
    assert end == start + len("Hello world.")


def test_chunk_by_paragraph_skips_blank():
    text = "A.\n\n\n\nB."
    out = chunk_by_paragraph(text, "d")
    assert len(out) >= 1


def test_chunk_by_paragraph_long_splits():
    raw = "x" * 1000
    text = raw + "\n\n"
    out = chunk_by_paragraph(text, "d", max_len=100)
    assert len(out) >= 2
    for start, end, piece in out:
        assert len(piece) <= 100


def test_chunk_by_paragraph_multiple():
    text = "P1.\n\nP2.\n\nP3."
    out = chunk_by_paragraph(text, "d")
    assert len(out) == 3


def test_span_around_empty_excerpt_uses_slice():
    text = "  \n  ab  \n  "
    s = span_around(text, 4, 6, "d")
    assert s.excerpt is not None
    assert "ab" in s.excerpt or s.excerpt.strip() == "ab"


def test_span_around_whitespace_sentence_uses_fallback():
    text = ".\n   \n."
    s = span_around(text, 2, 3, "d")
    assert s.document_id == "d"
    assert s.excerpt == ""


def test_chunk_by_paragraph_find_fallback():
    text = "a\r\n\r\nb"
    out = chunk_by_paragraph(text, "d")
    assert len(out) >= 1


def test_chunk_by_paragraph_paragraph_not_found_uses_offset():
    text = "x\r\n\r\ny"
    out = chunk_by_paragraph(text, "d")
    assert len(out) >= 1
    for start, end, piece in out:
        assert start >= 0
        assert end <= len(text)
