import tempfile
from pathlib import Path

import pytest

from infrastructure.doc_loader import DOCS_DIR, load_case_docs


def test_docs_dir_is_project_root_documents():
    assert DOCS_DIR.name == "documents"
    assert DOCS_DIR.exists()


def test_load_case_docs_returns_four_docs():
    docs = load_case_docs()
    assert len(docs) == 4
    assert "motion_for_summary_judgment" in docs
    assert "police_report" in docs
    assert "medical_records_excerpt" in docs
    assert "witness_statement" in docs


def test_load_case_docs_content_non_empty():
    docs = load_case_docs()
    for k, v in docs.items():
        assert isinstance(v, str)
        assert len(v) > 0


def test_load_case_docs_custom_dir_empty():
    with tempfile.TemporaryDirectory() as tmp:
        out = load_case_docs(docs_dir=Path(tmp))
        assert out == {}


def test_load_case_docs_custom_dir_with_one_file():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "a.txt"
        p.write_text("hello")
        out = load_case_docs(docs_dir=Path(tmp))
        assert out == {"a": "hello"}
