import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

if "DOCS_DIR" not in os.environ:
    os.environ["DOCS_DIR"] = str(BACKEND.parent / "documents")
if "SOURCE_OVERRIDES_PATH" not in os.environ:
    os.environ["SOURCE_OVERRIDES_PATH"] = str(BACKEND / "evals" / "fixtures" / "source_overrides.json")
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "sk-test"
if "OPENAI_MODEL" not in os.environ:
    os.environ["OPENAI_MODEL"] = "gpt-4o"
if "OPENAI_TEMPERATURE" not in os.environ:
    os.environ["OPENAI_TEMPERATURE"] = "0.2"


@pytest.fixture
def make_citation():
    from domain.schemas import CitationItem, Span

    def _make(citation_id: str, normalized_citation: str):
        return CitationItem(
            id=citation_id,
            raw_citation=normalized_citation,
            normalized_citation=normalized_citation,
            proposition_text="p",
            motion_span=Span(document_id="m", start=0, end=1),
        )

    return _make
