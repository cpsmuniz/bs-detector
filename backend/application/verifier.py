"""
Verifier facade
"""
from __future__ import annotations

from infrastructure import llm as llm_module

from domain.schemas import (
    CrossDocAssessment,
    DocBundle,
    ExtractionResult,
    FactClaim,
    QuoteAssessment,
    SourceRecord,
    SupportAssessment,
)

from application.citation_evaluator import evaluate_citations_and_quotes
from application.claim_extractor import extract_fact_claims
from application.cross_document_assessor import assess_claims_against_documents


def run_phase_a(
    extraction: ExtractionResult,
    sources: list[SourceRecord],
) -> tuple[list[SupportAssessment], list[QuoteAssessment]]:
    """Evaluate every citation and quote against retrieved authority text; returns support + quote assessments."""
    return evaluate_citations_and_quotes(extraction, sources)


def run_phase_b(bundle: DocBundle) -> tuple[list[FactClaim], list[CrossDocAssessment]]:
    """First extract fact claims from the motion, then assess each claim against the other case documents."""
    claims = extract_fact_claims(bundle)
    cross = assess_claims_against_documents(bundle, claims)
    return claims, cross
