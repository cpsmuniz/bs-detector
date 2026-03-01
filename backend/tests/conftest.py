import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


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
