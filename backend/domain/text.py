from __future__ import annotations

import re

from domain.schemas import Span


def collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def citation_to_key(citation: str) -> str:
    s = collapse_whitespace(citation)
    return s.rstrip(".;")


def span_around(text: str, idx_start: int, idx_end: int, document_id: str) -> Span:
    start = text.rfind(".", 0, idx_start)
    alt = text.rfind("\n", 0, idx_start)
    start = max(start, alt)
    start = 0 if start == -1 else start + 1
    end_period = text.find(".", idx_end)
    end_newline = text.find("\n", idx_end)
    candidates = [x for x in [end_period, end_newline] if x != -1]
    end = min(candidates) if candidates else len(text)
    excerpt = text[start:end].strip()
    if not excerpt:
        excerpt = text[idx_start:idx_end].strip()
    return Span(document_id=document_id, start=start, end=end, excerpt=excerpt[:500])


def chunk_by_paragraph(
    text: str, document_id: str, max_len: int = 900
) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    offset = 0
    for paragraph in text.split("\n\n"):
        raw = paragraph.strip()
        if not raw:
            offset += len(paragraph) + 2
            continue
        paragraph_start = text.find(paragraph, offset)
        if paragraph_start == -1:
            paragraph_start = offset
        if len(raw) <= max_len:
            out.append((paragraph_start, paragraph_start + len(paragraph), raw))
        else:
            running = 0
            while running < len(raw):
                piece = raw[running : running + max_len]
                start = paragraph_start + running
                end = start + len(piece)
                out.append((start, end, piece))
                running += max_len
        offset = paragraph_start + len(paragraph) + 2
    return out
