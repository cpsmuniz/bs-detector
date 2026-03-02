"""Build a one-paragraph judicial memo from findings, with optional LLM and deterministic fallback."""

from __future__ import annotations

from typing import Callable

from domain.schemas import Finding, JudicialMemo
from infrastructure.llm import call_llm_json, is_llm_available

_TOP_N_FALLBACK = 5

_SYSTEM_PROMPT = """You are a legal assistant. Given a list of verification findings, write one concise paragraph (judicial memo) summarizing the review outcome. Also list the finding ids that support your summary. Respond only with valid JSON: {{"memo_text": "<one paragraph>", "supporting_finding_ids": ["id1", "id2", ...]}}. Only include finding ids that appear in the provided list."""

_USER_PROMPT_TEMPLATE = """Findings:
{findings_summary}

Respond with JSON: {{"memo_text": "...", "supporting_finding_ids": [...]}}"""


def _findings_summary(findings: list[Finding]) -> str:
    lines = []
    for f in findings:
        lines.append(f"- id: {f.id}, status: {f.status}, confidence: {f.confidence:.2f}, reason: {f.confidence_reason}")
    return "\n".join(lines) if lines else "(none)"


def _build_memo_fallback(findings: list[Finding]) -> JudicialMemo:
    if not findings:
        return JudicialMemo(text="No findings to summarize.", supporting_finding_ids=[])
    sorted_findings = sorted(findings, key=lambda f: f.confidence, reverse=True)
    top = sorted_findings[:_TOP_N_FALLBACK]
    parts = [
        f"Finding {f.id} ({f.status}, confidence {f.confidence:.2f}): {f.confidence_reason}"
        for f in top
    ]
    paragraph = "Based on the review: " + "; ".join(parts) + "."
    return JudicialMemo(
        text=paragraph,
        supporting_finding_ids=[f.id for f in top],
    )


def build_memo(
    findings: list[Finding],
    *,
    _is_llm_available: Callable[[], bool] | None = None,
    _call_llm_json: Callable[..., dict] | None = None,
) -> JudicialMemo:
    if not findings:
        return JudicialMemo(text="No findings to summarize.", supporting_finding_ids=[])

    check_llm = _is_llm_available if _is_llm_available is not None else is_llm_available
    do_llm_json = _call_llm_json if _call_llm_json is not None else call_llm_json
    valid_ids = {f.id for f in findings}

    if check_llm():
        try:
            user_content = _USER_PROMPT_TEMPLATE.format(
                findings_summary=_findings_summary(findings)
            )
            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ]
            raw = do_llm_json(messages)
            memo_text = raw.get("memo_text") or raw.get("text")
            supporting = raw.get("supporting_finding_ids") or []
            if not isinstance(supporting, list):
                supporting = []
            filtered_ids = [sid for sid in supporting if isinstance(sid, str) and sid in valid_ids]
            if memo_text and isinstance(memo_text, str):
                return JudicialMemo(text=memo_text.strip(), supporting_finding_ids=filtered_ids)
        except Exception:
            pass
    return _build_memo_fallback(findings)
