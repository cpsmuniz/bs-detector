"""
Extract atomic fact claims from the motion document

We send the motion text (truncated) to the LLM with a schema that asks for claims with
id, claim_text, claim_type, source_section, and motion_span (document_id, start, end, excerpt)
We then normalize each item: stable claim_id (from LLM or claim_001, claim_002, …), and
a motion_span — either from the LLM's span object or a default span using the claim text as excerpt
If the LLM isn't available or parsing fails, we return an empty list
"""
from __future__ import annotations

from domain.schemas import DocBundle, FactClaim, Span
from infrastructure import llm as llm_module
from infrastructure.prompt_loader import get_contract, render

from application.evaluation_helpers import claim_id_from


def extract_fact_claims(bundle: DocBundle) -> list[FactClaim]:
    contract = get_contract()
    schemas = contract.get("_schemas") or {}
    motion = next((d for d in bundle.documents if d.id == bundle.motion_document_id), None)
    if not motion:
        return []

    fact_claims: list[FactClaim] = []
    if not llm_module.is_llm_available():
        return []

    try:
        # Prompt tells the LLM to return a list of claims; we use contract keys to read it
        context_claims = {
            "key_claims": contract["claims"],
            "claim_schema": schemas.get("claim", ""),
            "motion_span_fields": schemas.get("motion_span_fields", ""),
            "motion_excerpt": motion.text[:12000],
        }
        system_content = render("claim_extractor_system", key_claims=context_claims["key_claims"], claim_schema=context_claims["claim_schema"], motion_span_fields=context_claims["motion_span_fields"])
        user_content = render("claim_extractor_user", **context_claims)
        payload = llm_module.call_llm_json([
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ])
        for j, cl in enumerate(payload.get(contract["claims"]) or []):
            if not isinstance(cl, dict):
                continue
            cid = claim_id_from(cl, contract, j)
            # motion_span can be a proper {document_id, start, end, excerpt} or missing → we build a default
            ms = cl.get(contract["motion_span"])
            if isinstance(ms, dict) and contract["document_id"] in ms:
                span = Span(
                    document_id=str(ms.get(contract["document_id"], motion.id)),
                    start=int(ms.get(contract["start"], 0)),
                    end=int(ms.get(contract["end"], 0)),
                    excerpt=ms.get(contract["excerpt"]),
                )
            else:
                span = Span(
                    document_id=motion.id,
                    start=0,
                    end=0,
                    excerpt=cl.get(contract["claim_text"], "")[:500],
                )
            fact_claims.append(FactClaim(
                id=cid,
                claim_text=str(cl.get(contract["claim_text"], "")),
                claim_type=str(cl.get(contract["claim_type"], "fact")),
                motion_span=span,
                source_section=str(cl.get(contract["source_section"], "")),
            ))
    except (KeyError, TypeError, ValueError):
        pass

    return fact_claims
