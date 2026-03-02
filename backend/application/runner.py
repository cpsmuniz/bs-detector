from __future__ import annotations

import time
from pathlib import Path

from domain.schemas import VerificationReport

from application import memo as memo_module
from application import report as report_module
from application import verifier as verifier_module
from infrastructure import doc_loader as doc_loader_module
from infrastructure import source_lookup as source_lookup_module
from domain.extraction import build_bundle, run


def _step_load_docs(ctx: dict) -> dict[str, str] | None:
    docs = doc_loader_module.load_case_docs(docs_dir=ctx.get("_docs_dir"))
    ctx["load_docs"] = docs
    return docs


def _step_extract(ctx: dict) -> None:
    docs = ctx.get("load_docs")
    if docs is None:
        ctx["bundle"] = None
        ctx["extraction"] = None
        return None
    bundle = build_bundle(docs)
    extraction = run(bundle)
    ctx["bundle"] = bundle
    ctx["extraction"] = extraction
    return extraction


def _step_sources(ctx: dict) -> list:
    extraction = ctx.get("extraction")
    if extraction is None:
        ctx["sources"] = []
        return []
    sources = source_lookup_module.fetch_sources(
        extraction.citations, ctx.get("_use_web_retrieval", False)
    )
    ctx["sources"] = sources
    return sources


def _step_phase_a(ctx: dict) -> tuple:
    extraction = ctx.get("extraction")
    sources = ctx.get("sources")
    if extraction is None or sources is None:
        ctx["phase_a"] = ([], [])
        return ([], [])
    out = verifier_module.run_phase_a(extraction, sources)
    ctx["phase_a"] = out
    return out


def _step_phase_b(ctx: dict) -> tuple:
    bundle = ctx.get("bundle")
    if bundle is None:
        ctx["phase_b"] = ([], [])
        return ([], [])
    out = verifier_module.run_phase_b(bundle)
    ctx["phase_b"] = out
    return out


def _step_report(ctx: dict) -> VerificationReport:
    extraction = ctx.get("extraction")
    if extraction is None:
        report = VerificationReport(
            errors=ctx["errors"],
            timings_ms=dict(ctx["timings_ms"]),
        )
        ctx["report"] = report
        return report
    phase_a = ctx.get("phase_a") or ([], [])
    phase_b = ctx.get("phase_b") or ([], [])
    sources = ctx.get("sources") or []
    report = report_module.build_report(
        extraction,
        sources,
        phase_a[0],
        phase_a[1],
        phase_b[0],
        phase_b[1],
        errors=ctx["errors"],
        timings_ms=ctx["timings_ms"],
    )
    ctx["report"] = report
    return report


def _step_memo(ctx: dict) -> None:
    report = ctx.get("report")
    if report is None:
        return None
    if report.findings:
        memo = memo_module.build_memo(report.findings)
        report.judicial_memo = memo.text
    return None


def run_pipeline(
    *,
    docs_dir: Path | None = None,
    use_web_retrieval: bool = False,
) -> VerificationReport:
    ctx: dict = {
        "errors": [],
        "timings_ms": {},
        "_docs_dir": docs_dir,
        "_use_web_retrieval": use_web_retrieval,
    }
    steps = [
        ("load_docs", _step_load_docs),
        ("extract", _step_extract),
        ("sources", _step_sources),
        ("phase_a", _step_phase_a),
        ("phase_b", _step_phase_b),
        ("report", _step_report),
        ("memo", _step_memo),
    ]
    for name, fn in steps:
        t0 = time.perf_counter()
        try:
            fn(ctx)
            ctx["timings_ms"][name] = (time.perf_counter() - t0) * 1000
        except Exception as e:
            ctx["errors"].append(f"{name}: {e}")
            ctx[name] = None
            ctx["timings_ms"][name] = (time.perf_counter() - t0) * 1000
    if ctx.get("report") is not None:
        ctx["report"].timings_ms = dict(ctx["timings_ms"])
        return ctx["report"]
    return VerificationReport(
        errors=ctx["errors"],
        timings_ms=dict(ctx["timings_ms"]),
    )
