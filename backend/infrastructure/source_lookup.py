from __future__ import annotations

import json
from pathlib import Path

from domain.schemas import CitationItem, RetrievalStatus, SourceRecord
from infrastructure.env_loader import require_path


def get_overrides_path() -> Path:
    return require_path("SOURCE_OVERRIDES_PATH")


def load_override_fixture(path: Path | None = None) -> dict[str, dict]:
    target = path if path is not None else get_overrides_path()
    if not target.exists():
        return {}
    data = json.loads(target.read_text())
    return data if isinstance(data, dict) else {}


def fetch_sources(
    citations: list[CitationItem],
    use_web_retrieval: bool,
    overrides: dict[str, dict] | None = None,
) -> list[SourceRecord]:
    if overrides is None:
        overrides = load_override_fixture()
    out: list[SourceRecord] = []
    for c in citations:
        key = c.normalized_citation
        ov = overrides.get(key)
        if ov is not None:
            out.append(_record_from_override(c, ov))
            continue
        if not use_web_retrieval:
            out.append(
                SourceRecord(
                    citation_id=c.id,
                    normalized_citation=c.normalized_citation,
                    retrieval_status=RetrievalStatus.DISABLED,
                    error="Web retrieval disabled",
                )
            )
            continue
        out.append(
            SourceRecord(
                citation_id=c.id,
                normalized_citation=c.normalized_citation,
                retrieval_status=RetrievalStatus.NOT_FOUND,
                error="Web retrieval not implemented",
            )
        )
    return out


def _record_from_override(citation: CitationItem, ov: dict) -> SourceRecord:
    raw = ov.get("retrieval_status", "found")
    try:
        status = RetrievalStatus(raw)
    except ValueError:
        status = RetrievalStatus.FOUND
    return SourceRecord(
        citation_id=citation.id,
        normalized_citation=citation.normalized_citation,
        retrieval_status=status,
        source_url=ov.get("source_url"),
        authority_text=ov.get("authority_text"),
        error=ov.get("error"),
    )
