"""
Shared helpers for turning LLM output into our domain types

We never trust the model to return valid enums or numbers — these functions normalize
strings to SupportLabel/QuoteLabel/CrossDocLabel, clamp confidence to [0,1], and
provide stable IDs and fallback reasons. Used by citation_evaluator, claim_extractor,
and cross_document_assessor so they don't duplicate this logic
"""
from __future__ import annotations

from domain.enums import CrossDocLabel, QuoteLabel, SupportLabel
from domain.schemas import CrossDocAssessment


def support_label_from(s: str) -> SupportLabel:
    """Map LLM string to SupportLabel; invalid or unknown → COULD_NOT_VERIFY."""
    try:
        return SupportLabel(s)
    except ValueError:
        return SupportLabel.COULD_NOT_VERIFY


def quote_label_from(s: str) -> QuoteLabel:
    """Map LLM string to QuoteLabel; invalid or unknown → COULD_NOT_VERIFY."""
    try:
        return QuoteLabel(s)
    except ValueError:
        return QuoteLabel.COULD_NOT_VERIFY


def cross_label_from(s: str) -> CrossDocLabel:
    """Map LLM string to CrossDocLabel; invalid or unknown → COULD_NOT_VERIFY."""
    try:
        return CrossDocLabel(s)
    except ValueError:
        return CrossDocLabel.COULD_NOT_VERIFY


def float_in_01(val: float | None) -> float:
    """Confidence must be in [0, 1]; missing or invalid → 0.2 (low confidence)."""
    if val is None:
        return 0.2
    try:
        v = float(val)
        return max(0.0, min(1.0, v))
    except (TypeError, ValueError):
        return 0.2


def default_reason(raw: str) -> str:
    """Empty reason from LLM → 'No reason given.' so we always have something to show."""
    return raw if raw else "No reason given."


def claim_id_from(cl: dict, contract: dict, j: int) -> str:
    """Use claim id from LLM if present, otherwise claim_001, claim_002, … by index."""
    cid = cl.get(contract["id"])
    if not cid:
        return f"claim_{j+1:03d}"
    return str(cid)


def find_cross_assessment(payload: dict, claim_id: str, contract: dict) -> CrossDocAssessment | None:
    """Find the assessment in the LLM payload that matches this claim_id; build one CrossDocAssessment or None."""
    for a in payload.get(contract["assessments"]) or []:
        if isinstance(a, dict) and str(a.get(contract["claim_id"])) == claim_id:
            return CrossDocAssessment(
                claim_id=claim_id,
                label=cross_label_from(str(a.get(contract["label"], ""))),
                confidence=float_in_01(a.get(contract["confidence"])),
                reason=str(a.get(contract["reason"], "")) or "No reason given.",
            )
    return None
