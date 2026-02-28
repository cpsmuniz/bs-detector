from __future__ import annotations

from pydantic import BaseModel, Field


class Span(BaseModel):
    document_id: str
    start: int
    end: int
    excerpt: str | None = None


class DocChunk(BaseModel):
    id: str
    span: Span
    text: str


class DocRecord(BaseModel):
    id: str
    name: str
    text: str
    chunks: list[DocChunk] = Field(default_factory=list)


class DocBundle(BaseModel):
    documents: list[DocRecord]
    motion_document_id: str


class CitationItem(BaseModel):
    id: str
    raw_citation: str
    normalized_citation: str
    proposition_text: str
    motion_span: Span
    needs_review: bool = False


class QuoteItem(BaseModel):
    id: str
    quote_text: str
    citation_id: str | None = None
    proposition_text: str
    motion_span: Span


class ExtractionResult(BaseModel):
    citations: list[CitationItem] = Field(default_factory=list)
    quotes: list[QuoteItem] = Field(default_factory=list)
