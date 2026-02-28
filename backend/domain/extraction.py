from __future__ import annotations

import re

from domain.schemas import (
    CitationItem,
    DocBundle,
    DocChunk,
    DocRecord,
    ExtractionResult,
    QuoteItem,
    Span,
)
from domain.text import citation_to_key, chunk_by_paragraph, span_around

MOTION_ID = "motion_for_summary_judgment"

LEGAL_CITATION_PATTERN = re.compile(
    r"([A-Z][A-Za-z&'\-\.]*?(?:\s+[A-Z][A-Za-z0-9&'\-\.]*)*\s+v\.\s+"
    r"[A-Z][A-Za-z0-9&'\-\.]*?(?:\s+[A-Z][A-Za-z0-9&'\-\.]*)*,\s*"
    r"[^;\n\)]*\((?:[^\)]*?\d{4})\))"
)
DIRECT_QUOTE_PATTERN = re.compile(r'"([^"\n]{6,600})"')


def link_quote_to_citation(
    citations: list[CitationItem], quote_pos: int, motion_text: str
) -> str | None:
    if not citations:
        return None
    best_id: str | None = None
    best_dist: int | None = None
    for c in citations:
        idx = motion_text.find(c.raw_citation)
        if idx == -1:
            continue
        dist = abs(quote_pos - idx)
        if idx <= quote_pos:
            dist -= 2
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_id = c.id
    return best_id


def build_bundle(docs: dict[str, str]) -> DocBundle:
    records: list[DocRecord] = []
    for name in sorted(docs.keys()):
        raw = docs[name].replace("\r\n", "\n").strip()
        chunks: list[DocChunk] = []
        for i, (start, end, chunk_text) in enumerate(
            chunk_by_paragraph(raw, name), start=1
        ):
            sp = Span(
                document_id=name,
                start=start,
                end=end,
                excerpt=chunk_text[:500],
            )
            chunks.append(
                DocChunk(id=f"{name}_chunk_{i:03d}", span=sp, text=chunk_text)
            )
        records.append(DocRecord(id=name, name=name, text=raw, chunks=chunks))
    if not records:
        raise ValueError("No documents loaded")
    if not any(r.id == MOTION_ID for r in records):
        raise ValueError(f"Missing motion document: {MOTION_ID}")
    return DocBundle(documents=records, motion_document_id=MOTION_ID)


def _extract_citations(motion_id: str, text: str) -> list[CitationItem]:
    out: list[CitationItem] = []
    for i, m in enumerate(LEGAL_CITATION_PATTERN.finditer(text), start=1):
        raw = m.group(1).strip()
        sp = span_around(text, m.start(1), m.end(1), motion_id)
        out.append(
            CitationItem(
                id=f"citation_{i:03d}",
                raw_citation=raw,
                normalized_citation=citation_to_key(raw),
                proposition_text=sp.excerpt or raw,
                motion_span=sp,
                needs_review=False,
            )
        )
    return out


def _extract_quotes(
    motion_id: str, text: str, citations: list[CitationItem]
) -> list[QuoteItem]:
    out: list[QuoteItem] = []
    q_idx = 0
    for m in DIRECT_QUOTE_PATTERN.finditer(text):
        quote_text = m.group(1).strip()
        if len(quote_text.split()) < 6 or len(quote_text) < 35:
            continue
        q_idx += 1
        sp = span_around(text, m.start(1), m.end(1), motion_id)
        cid = link_quote_to_citation(citations, m.start(1), text)
        out.append(
            QuoteItem(
                id=f"quote_{q_idx:03d}",
                quote_text=quote_text,
                citation_id=cid,
                proposition_text=sp.excerpt or quote_text,
                motion_span=sp,
            )
        )
    return out


def run(bundle: DocBundle) -> ExtractionResult:
    motion = next(d for d in bundle.documents if d.id == bundle.motion_document_id)
    text = motion.text
    citations = _extract_citations(motion.id, text)
    quotes = _extract_quotes(motion.id, text, citations)
    return ExtractionResult(citations=citations, quotes=quotes)
