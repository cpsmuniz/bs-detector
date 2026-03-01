from application.evaluation_helpers import (
    claim_id_from,
    cross_label_from,
    default_reason,
    find_cross_assessment,
    float_in_01,
    quote_label_from,
    support_label_from,
)
from domain.enums import CrossDocLabel, QuoteLabel, SupportLabel
from infrastructure.prompt_loader import get_contract


def test_support_label_from_valid_returns_enum():
    assert support_label_from("supports") == SupportLabel.SUPPORTS
    assert support_label_from("could_not_verify") == SupportLabel.COULD_NOT_VERIFY


def test_support_label_from_invalid_returns_could_not_verify():
    assert support_label_from("invalid") == SupportLabel.COULD_NOT_VERIFY


def test_quote_label_from_valid_returns_enum():
    assert quote_label_from("exact") == QuoteLabel.EXACT
    assert quote_label_from("could_not_verify") == QuoteLabel.COULD_NOT_VERIFY


def test_quote_label_from_invalid_returns_could_not_verify():
    assert quote_label_from("x") == QuoteLabel.COULD_NOT_VERIFY


def test_cross_label_from_valid_returns_enum():
    assert cross_label_from("supported") == CrossDocLabel.SUPPORTED
    assert cross_label_from("could_not_verify") == CrossDocLabel.COULD_NOT_VERIFY


def test_cross_label_from_invalid_returns_could_not_verify():
    assert cross_label_from("x") == CrossDocLabel.COULD_NOT_VERIFY


def test_float_in_01_none_returns_default():
    assert float_in_01(None) == 0.2


def test_float_in_01_valid_clamped():
    assert float_in_01(0.5) == 0.5
    assert float_in_01(1.5) == 1.0
    assert float_in_01(-0.1) == 0.0


def test_float_in_01_invalid_returns_default():
    assert float_in_01("x") == 0.2


def test_default_reason_empty():
    assert default_reason("") == "No reason given."


def test_default_reason_non_empty():
    assert default_reason("Ok.") == "Ok."


def test_claim_id_from_missing_returns_indexed():
    contract = get_contract()
    assert claim_id_from({}, contract, 0) == "claim_001"
    assert claim_id_from({"claim_text": "x"}, contract, 2) == "claim_003"


def test_claim_id_from_present_returns_id():
    contract = get_contract()
    assert claim_id_from({"id": "my_id"}, contract, 0) == "my_id"


def test_find_cross_assessment_missing_returns_none():
    contract = get_contract()
    assert find_cross_assessment({}, "c1", contract) is None
    assert find_cross_assessment({"assessments": []}, "c1", contract) is None


def test_find_cross_assessment_match_returns_assessment():
    contract = get_contract()
    out = find_cross_assessment(
        {"assessments": [{"claim_id": "c1", "label": "supported", "confidence": 0.8, "reason": "Yes."}]},
        "c1",
        contract,
    )
    assert out is not None
    assert out.claim_id == "c1"
    assert out.label == CrossDocLabel.SUPPORTED
