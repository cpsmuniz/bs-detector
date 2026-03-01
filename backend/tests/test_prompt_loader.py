import pytest

from infrastructure.prompt_loader import get_contract, render

EXPECTED_J2_TEMPLATES = [
    "citation_evaluator_system",
    "citation_evaluator_user",
    "citation_evaluator_citation_block",
    "citation_evaluator_quote_block",
    "claim_extractor_system",
    "claim_extractor_user",
    "cross_document_assessor_system",
    "cross_document_assessor_user",
]

# Minimal context so each template renders without UndefinedError
MINIMAL_RENDER_CONTEXT = {
    "citation_evaluator_system": {
        "key_support": "support_assessments",
        "key_quote": "quote_assessments",
        "support_schema": "{}",
        "quote_schema": "{}",
        "support_labels": "s",
        "quote_labels": "q",
    },
    "citation_evaluator_user": {"key_support": "s", "key_quote": "q", "items": ""},
    "citation_evaluator_citation_block": {"citation_id": "c1", "proposition": "P", "authority": "A"},
    "citation_evaluator_quote_block": {"quote_id": "q1", "quote_text": "T", "authority": "A"},
    "claim_extractor_system": {"key_claims": "claims", "claim_schema": "{}", "motion_span_fields": "id"},
    "claim_extractor_user": {"motion_excerpt": "M", "key_claims": "claims", "claim_schema": "{}"},
    "cross_document_assessor_system": {"key_assessments": "a", "assessment_schema": "{}", "cross_labels": "l"},
    "cross_document_assessor_user": {
        "claim_text": "C",
        "context": "D",
        "key_assessments": "a",
        "assessment_schema": "{}",
        "field_claim_id": "claim_id",
        "claim_id": "c1",
    },
}


def test_get_contract_returns_flat_dict_with_keys_and_fields():
    c = get_contract()
    assert c["support_assessments"] == "support_assessments"
    assert c["quote_assessments"] == "quote_assessments"
    assert c["claims"] == "claims"
    assert c["assessments"] == "assessments"
    assert c["citation_id"] == "citation_id"
    assert c["claim_id"] == "claim_id"
    assert c["id"] == "id"


def test_get_contract_includes_schemas():
    c = get_contract()
    schemas = c.get("_schemas") or {}
    assert "support" in schemas
    assert "quote" in schemas
    assert "claim" in schemas
    assert "assessment" in schemas


def test_render_citation_evaluator_system_substitutes_variables():
    out = render(
        "citation_evaluator_system",
        key_support="support_assessments",
        key_quote="quote_assessments",
        support_schema="{citation_id, label, confidence, reason}",
        quote_schema="{quote_id, label, confidence, reason}",
        support_labels="supports, partially_supports, could_not_verify",
        quote_labels="exact, minor_difference, could_not_verify",
    )
    assert "support_assessments" in out
    assert "quote_assessments" in out
    assert "supports" in out
    assert "exact" in out


def test_render_citation_evaluator_user_substitutes_items():
    out = render("citation_evaluator_user", key_support="support_assessments", key_quote="quote_assessments", items="[CITATION c1] Proposition: P\nAuthority: A")
    assert "[CITATION c1]" in out
    assert "support_assessments" in out
    assert "quote_assessments" in out


def test_render_citation_evaluator_citation_block():
    out = render("citation_evaluator_citation_block", citation_id="c1", proposition="The law says X.", authority="Source text.")
    assert "c1" in out
    assert "The law says X." in out
    assert "Source text." in out


def test_render_claim_extractor_user():
    out = render("claim_extractor_user", motion_excerpt="Motion text here.", key_claims="claims", claim_schema="{id, claim_text}")
    assert "Motion text here." in out
    assert "claims" in out
    assert "{id, claim_text}" in out


def test_render_cross_document_assessor_user():
    out = render(
        "cross_document_assessor_user",
        claim_text="Fact.",
        context="Doc text.",
        key_assessments="assessments",
        assessment_schema="{claim_id, label}",
        field_claim_id="claim_id",
        claim_id="claim_001",
    )
    assert "Fact." in out
    assert "Doc text." in out
    assert "claim_001" in out


@pytest.mark.parametrize("template_name", EXPECTED_J2_TEMPLATES)
def test_j2_template_accessible(template_name):
    """Every expected .j2 template exists and can be loaded and rendered."""
    ctx = MINIMAL_RENDER_CONTEXT[template_name]
    out = render(template_name, **ctx)
    assert isinstance(out, str)
