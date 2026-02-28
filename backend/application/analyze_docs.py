from __future__ import annotations

from infrastructure.doc_loader import load_case_docs

from domain.extraction import build_bundle, run


def analyze_documents(docs_dir=None) -> dict:
    docs = load_case_docs(docs_dir=docs_dir)
    bundle = build_bundle(docs)
    _ = run(bundle)
    return {"report": None}
