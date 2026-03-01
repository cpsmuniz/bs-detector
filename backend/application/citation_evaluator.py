from __future__ import annotations

import json

from domain.enums import QuoteLabel, RetrievalStatus, SupportLabel
from domain.schemas import (
    ExtractionResult,
    QuoteAssessment,
    SourceRecord,
    SupportAssessment,
)
from infrastructure import llm as llm_module
from infrastructure.prompt_loader import get_contract, render

from application.evaluation_helpers import (
    default_reason,
    float_in_01,
    quote_label_from,
    support_label_from,
)


def evaluate_citations_and_quotes(
    extraction: ExtractionResult,
    sources: list[SourceRecord],
) -> tuple[list[SupportAssessment], list[QuoteAssessment]]:
    contract = get_contract()
    schemas = contract.get("_schemas") or {}
    by_citation = {s.citation_id: s for s in sources}
    # One slot per citation/quote; None = "not decided yet", we fill or fallback later
    support_out: list[SupportAssessment | None] = []
    quote_out: list[QuoteAssessment | None] = []

    # Pre-fill COULD_NOT_VERIFY for citations that have no usable authority
    for c in extraction.citations:
        src = by_citation.get(c.id)
        if not src or src.retrieval_status != RetrievalStatus.FOUND or not (src.authority_text or "").strip():
            support_out.append(
                SupportAssessment(
                    citation_id=c.id,
                    label=SupportLabel.COULD_NOT_VERIFY,
                    confidence=0.2,
                    reason="Authority text unavailable.",
                    uncertainty_reason=src.error if src else "Missing source",
                )
            )
        else:
            support_out.append(None)

    # Same for quotes: no authority for the cited source → COULD_NOT_VERIFY
    for q in extraction.quotes:
        src = by_citation.get(q.citation_id or "") if q.citation_id else None
        if not src or src.retrieval_status != RetrievalStatus.FOUND or not (src.authority_text or "").strip():
            quote_out.append(
                QuoteAssessment(
                    quote_id=q.id,
                    label=QuoteLabel.COULD_NOT_VERIFY,
                    confidence=0.2,
                    reason="Quote source text unavailable.",
                    uncertainty_reason="Missing or unavailable authority",
                )
            )
        else:
            quote_out.append(None)

    # Only ask the LLM for citations/quotes we haven't already marked COULD_NOT_VERIFY
    need_support = [(i, extraction.citations[i], by_citation[extraction.citations[i].id]) for i in range(len(extraction.citations)) if support_out[i] is None]
    need_quote = [(i, q, by_citation[q.citation_id]) for i, q in enumerate(extraction.quotes) if quote_out[i] is None and q.citation_id and by_citation.get(q.citation_id)]

    if (need_support or need_quote) and llm_module.is_llm_available():
        # Build one user message: all citation blocks then all quote blocks (from templates)
        user_parts = []
        if need_support:
            for _idx, c, src in need_support:
                user_parts.append(render(
                    "citation_evaluator_citation_block",
                    citation_id=c.id,
                    proposition=(c.proposition_text or "")[:800],
                    authority=(src.authority_text or "")[:4000],
                ))
        if need_quote:
            for _idx, q, src in need_quote:
                user_parts.append(render(
                    "citation_evaluator_quote_block",
                    quote_id=q.id,
                    quote_text=q.quote_text[:1000],
                    authority=(src.authority_text or "")[:4000],
                ))
        try:
            # One LLM call for all pending support + quote assessments; contract keys come from contract.yaml
            context_phase_a = {
                "key_support": contract["support_assessments"],
                "key_quote": contract["quote_assessments"],
                "support_schema": schemas.get("support", ""),
                "quote_schema": schemas.get("quote", ""),
                "support_labels": ", ".join(s.value for s in SupportLabel),
                "quote_labels": ", ".join(q.value for q in QuoteLabel),
                "items": "\n\n---\n\n".join(user_parts),
            }
            system_content = render("citation_evaluator_system", **{k: v for k, v in context_phase_a.items() if k != "items"})
            user_content = render("citation_evaluator_user", **context_phase_a)
            payload = llm_module.call_llm_json([
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ])
            if not isinstance(payload, dict):
                payload = {}
            # Match each support assessment back to the right citation by citation_id and fill that slot
            for sa in payload.get(contract["support_assessments"]) or []:
                cid = sa.get(contract["citation_id"])
                if not cid:
                    continue
                for i, c in enumerate(extraction.citations):
                    if c.id == cid and support_out[i] is None:
                        reason = default_reason(str(sa.get(contract["reason"], "")))
                        support_out[i] = SupportAssessment(
                            citation_id=cid,
                            label=support_label_from(str(sa.get(contract["label"], ""))),
                            confidence=float_in_01(sa.get(contract["confidence"])),
                            reason=reason,
                        )
                        break
            # Same idea for quote assessments: match by quote_id and fill the slot
            for qa in payload.get(contract["quote_assessments"]) or []:
                qid = qa.get(contract["quote_id"])
                if not qid:
                    continue
                for i, q in enumerate(extraction.quotes):
                    if q.id == qid and quote_out[i] is None:
                        quote_out[i] = QuoteAssessment(
                            quote_id=qid,
                            label=quote_label_from(str(qa.get(contract["label"], ""))),
                            confidence=float_in_01(qa.get(contract["confidence"])),
                            reason=default_reason(str(qa.get(contract["reason"], ""))),
                        )
                        break
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

    # Any slot still None (LLM didn't return it or we never called LLM) → safe fallback
    for i in range(len(support_out)):
        if support_out[i] is None:
            support_out[i] = SupportAssessment(
                citation_id=extraction.citations[i].id,
                label=SupportLabel.COULD_NOT_VERIFY,
                confidence=0.2,
                reason="Verification unavailable.",
            )
    for i in range(len(quote_out)):
        if quote_out[i] is None:
            quote_out[i] = QuoteAssessment(
                quote_id=extraction.quotes[i].id,
                label=QuoteLabel.COULD_NOT_VERIFY,
                confidence=0.2,
                reason="Verification unavailable.",
            )

    return (
        [s for s in support_out if s is not None],
        [q for q in quote_out if q is not None],
    )
