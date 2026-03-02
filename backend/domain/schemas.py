from __future__ import annotations

from pydantic import BaseModel, Field

from domain.enums import CrossDocLabel, FindingKind, QuoteLabel, RetrievalStatus, SupportLabel


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


class SourceRecord(BaseModel):
    citation_id: str
    normalized_citation: str
    retrieval_status: RetrievalStatus
    source_url: str | None = None
    authority_text: str | None = None
    error: str | None = None


class SupportAssessment(BaseModel):
    citation_id: str
    label: SupportLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence_spans: list[Span] = Field(default_factory=list)
    uncertainty_reason: str | None = None


class QuoteAssessment(BaseModel):
    quote_id: str
    label: QuoteLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence_spans: list[Span] = Field(default_factory=list)
    uncertainty_reason: str | None = None


class FactClaim(BaseModel):
    id: str
    claim_text: str
    claim_type: str
    motion_span: Span
    source_section: str


class CrossDocAssessment(BaseModel):
    claim_id: str
    label: CrossDocLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence_spans: list[Span] = Field(default_factory=list)
    uncertainty_reason: str | None = None


class Finding(BaseModel):
    id: str
    kind: FindingKind
    reference_id: str
    status: str
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_reason: str
    evidence_spans: list[Span] = Field(default_factory=list)


class JudicialMemo(BaseModel):
    text: str
    supporting_finding_ids: list[str] = Field(default_factory=list)


class VerificationReport(BaseModel):
    citation_findings: list[Finding] = Field(default_factory=list)
    quote_findings: list[Finding] = Field(default_factory=list)
    cross_document_findings: list[Finding] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    judicial_memo: str = ""
    errors: list[str] = Field(default_factory=list)
    timings_ms: dict[str, float] = Field(default_factory=dict)
