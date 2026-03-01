"""
Report assembly: map verifier outputs to a single VerificationReport

Pure function build_report takes extraction, sources, and the outputs of run_phase_a
and run_phase_b, and produces citation_findings, quote_findings, cross_document_findings,
and a unified findings list. Confidence rules are applied here (could_not_verify → low;
supports/exact/supported → use assessment confidence; negative outcomes → high confidence)
"""
from __future__ import annotations

from domain.enums import CrossDocLabel, FindingKind, QuoteLabel, SupportLabel
from domain.schemas import (
    CrossDocAssessment,
    ExtractionResult,
    FactClaim,
    Finding,
    QuoteAssessment,
    SourceRecord,
    SupportAssessment,
    VerificationReport,
)


def _confidence_for_support(a: SupportAssessment) -> tuple[float, str]:
    if a.label == SupportLabel.COULD_NOT_VERIFY:
        return 0.2, "Could not verify."
    if a.label == SupportLabel.DOES_NOT_SUPPORT:
        return max(a.confidence, 0.8), a.reason or "Citation not supported."
    return a.confidence, a.reason or "No reason given."


def _confidence_for_quote(a: QuoteAssessment) -> tuple[float, str]:
    if a.label == QuoteLabel.COULD_NOT_VERIFY:
        return 0.2, "Could not verify."
    if a.label == QuoteLabel.MATERIAL_DIFFERENCE:
        return max(a.confidence, 0.8), a.reason or "Material difference."
    return a.confidence, a.reason or "No reason given."


def _confidence_for_cross(a: CrossDocAssessment) -> tuple[float, str]:
    if a.label == CrossDocLabel.COULD_NOT_VERIFY:
        return 0.2, "Could not verify."
    if a.label == CrossDocLabel.CONTRADICTED:
        return max(a.confidence, 0.8), a.reason or "Claim contradicted."
    return a.confidence, a.reason or "No reason given."


def build_report(
    extraction: ExtractionResult,
    sources: list[SourceRecord],
    support_assessments: list[SupportAssessment],
    quote_assessments: list[QuoteAssessment],
    fact_claims: list[FactClaim],
    cross_doc_assessments: list[CrossDocAssessment],
    *,
    errors: list[str] | None = None,
    timings_ms: dict[str, float] | None = None,
) -> VerificationReport:
    citation_findings: list[Finding] = []
    for a in support_assessments:
        conf, reason = _confidence_for_support(a)
        citation_findings.append(
            Finding(
                id=f"citation_{a.citation_id}",
                kind=FindingKind.CITATION_SUPPORT,
                reference_id=a.citation_id,
                status=a.label.value,
                confidence=conf,
                confidence_reason=reason,
                evidence_spans=a.evidence_spans,
            )
        )

    quote_findings: list[Finding] = []
    for a in quote_assessments:
        conf, reason = _confidence_for_quote(a)
        quote_findings.append(
            Finding(
                id=f"quote_{a.quote_id}",
                kind=FindingKind.QUOTE_ACCURACY,
                reference_id=a.quote_id,
                status=a.label.value,
                confidence=conf,
                confidence_reason=reason,
                evidence_spans=a.evidence_spans,
            )
        )

    cross_document_findings: list[Finding] = []
    for a in cross_doc_assessments:
        conf, reason = _confidence_for_cross(a)
        cross_document_findings.append(
            Finding(
                id=f"cross_{a.claim_id}",
                kind=FindingKind.CROSS_DOCUMENT_CONSISTENCY,
                reference_id=a.claim_id,
                status=a.label.value,
                confidence=conf,
                confidence_reason=reason,
                evidence_spans=a.evidence_spans,
            )
        )

    findings = citation_findings + quote_findings + cross_document_findings

    return VerificationReport(
        citation_findings=citation_findings,
        quote_findings=quote_findings,
        cross_document_findings=cross_document_findings,
        findings=findings,
        judicial_memo="",
        errors=errors if errors is not None else [],
        timings_ms=timings_ms if timings_ms is not None else {},
    )
