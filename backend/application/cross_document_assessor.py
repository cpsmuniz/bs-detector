"""
Cross-document assessment: for each fact claim from the motion, we ask the LLM whether
the other case documents (opposition, reply, etc.) support, contradict, or leave the claim unverified.

In short:
- Input: the full bundle (motion + other docs) and the list of fact claims we just extracted.
- For each claim we build a small context from the non-motion documents (first 3 docs, first 3000 chars each).
- We send one LLM request per claim: system prompt describes the task and schema, user prompt gives the claim text + that context.
- The LLM returns an "assessments" list; we look for the entry that matches this claim_id (via find_cross_assessment).
- If we find it, we turn it into a CrossDocAssessment (label, confidence, reason). If not, or on any error, we append COULD_NOT_VERIFY so every claim gets exactly one assessment.

Result: one CrossDocAssessment per fact claim, in the same order as fact_claims.
"""
from __future__ import annotations

from domain.enums import CrossDocLabel
from domain.schemas import CrossDocAssessment, DocBundle, FactClaim
from infrastructure import llm as llm_module
from infrastructure.prompt_loader import get_contract, render

from application.evaluation_helpers import find_cross_assessment


def assess_claims_against_documents(bundle: DocBundle, fact_claims: list[FactClaim]) -> list[CrossDocAssessment]:
    contract = get_contract()
    schemas = contract.get("_schemas") or {}
    # Only assess against non-motion docs (opposition, reply, etc.)
    other_docs = [d for d in bundle.documents if d.id != bundle.motion_document_id]
    cross_out: list[CrossDocAssessment] = []

    for fc in fact_claims:
        if llm_module.is_llm_available() and other_docs:
            try:
                # Limit context size: up to 3 docs, 3000 chars each, so the prompt stays manageable
                context = "\n\n".join(d.text[:3000] for d in other_docs[:3])
                cross_ctx = {
                    "key_assessments": contract["assessments"],
                    "assessment_schema": schemas.get("assessment", ""),
                    "field_claim_id": contract["claim_id"],
                    "claim_text": fc.claim_text,
                    "context": context,
                    "claim_id": fc.id,
                }
                system_content = render("cross_document_assessor_system", key_assessments=cross_ctx["key_assessments"], assessment_schema=cross_ctx["assessment_schema"], cross_labels=", ".join(c.value for c in CrossDocLabel))
                user_content = render("cross_document_assessor_user", **cross_ctx)
                payload = llm_module.call_llm_json([
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                ])
                # Pull out the assessment that matches this claim; normalize label/confidence via find_cross_assessment
                matched = find_cross_assessment(payload, fc.id, contract)
                if matched:
                    cross_out.append(matched)
                else:
                    cross_out.append(CrossDocAssessment(claim_id=fc.id, label=CrossDocLabel.COULD_NOT_VERIFY, confidence=0.2, reason="No assessment returned."))
            except (KeyError, TypeError, ValueError):
                cross_out.append(CrossDocAssessment(claim_id=fc.id, label=CrossDocLabel.COULD_NOT_VERIFY, confidence=0.2, reason="Verification failed."))
        else:
            cross_out.append(CrossDocAssessment(claim_id=fc.id, label=CrossDocLabel.COULD_NOT_VERIFY, confidence=0.2, reason="LLM or documents unavailable."))

    return cross_out
