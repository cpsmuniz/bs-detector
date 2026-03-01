import pytest

from domain.schemas import RetrievalStatus
from infrastructure.source_lookup import (
    fetch_sources,
    get_overrides_path,
    load_override_fixture,
)


def test_get_overrides_path_uses_env_when_set(tmp_path, monkeypatch):
    custom = tmp_path / "custom.json"
    custom.write_text("{}")
    monkeypatch.setenv("SOURCE_OVERRIDES_PATH", str(custom))
    assert get_overrides_path() == custom.resolve()


def test_load_override_fixture_missing_file_returns_empty(tmp_path):
    path = tmp_path / "missing.json"
    assert not path.exists()
    assert load_override_fixture(path) == {}


def test_load_override_fixture_loads_from_default_path():
    if not get_overrides_path().exists():
        pytest.skip("default fixture not present")
    data = load_override_fixture()
    assert isinstance(data, dict)
    key = "Privette v. Superior Court, 5 Cal.4th 689, 695 (1993)"
    assert key in data
    assert data[key].get("retrieval_status") == "found"
    assert "authority_text" in data[key]


def test_load_override_fixture_with_explicit_path(tmp_path):
    fixture = tmp_path / "overrides.json"
    fixture.write_text('{"A (2020)": {"retrieval_status": "found", "authority_text": "x"}}')
    data = load_override_fixture(fixture)
    assert data == {"A (2020)": {"retrieval_status": "found", "authority_text": "x"}}


def test_load_override_fixture_non_dict_json_returns_empty(tmp_path):
    fixture = tmp_path / "array.json"
    fixture.write_text("[]")
    assert load_override_fixture(fixture) == {}


def test_fetch_sources_empty_citations_returns_empty_list():
    assert fetch_sources([], True) == []
    assert fetch_sources([], False, {}) == []


def test_fetch_sources_override_present_returns_found_with_authority_text(make_citation):
    key = "Privette v. Superior Court, 5 Cal.4th 689, 695 (1993)"
    citations = [make_citation("c1", key)]
    overrides = {
        key: {
            "retrieval_status": "found",
            "authority_text": "Privette holds.",
            "source_url": "https://example.com",
            "error": None,
        }
    }
    results = fetch_sources(citations, True, overrides)
    assert len(results) == 1
    assert results[0].citation_id == "c1"
    assert results[0].normalized_citation == key
    assert results[0].retrieval_status == RetrievalStatus.FOUND
    assert results[0].authority_text == "Privette holds."
    assert results[0].source_url == "https://example.com"
    assert results[0].error is None


def test_fetch_sources_no_override_use_web_false_returns_disabled(make_citation):
    citations = [make_citation("c1", "Unknown Case (2020)")]
    results = fetch_sources(citations, False, {})
    assert len(results) == 1
    assert results[0].retrieval_status == RetrievalStatus.DISABLED
    assert results[0].error == "Web retrieval disabled"
    assert results[0].authority_text is None


def test_fetch_sources_no_override_use_web_true_returns_not_found(make_citation):
    citations = [make_citation("c1", "Unknown Case (2020)")]
    results = fetch_sources(citations, True, {})
    assert len(results) == 1
    assert results[0].retrieval_status == RetrievalStatus.NOT_FOUND
    assert results[0].error == "Web retrieval not implemented"
    assert results[0].authority_text is None


def test_fetch_sources_uses_fixture_when_overrides_none(make_citation):
    if not get_overrides_path().exists():
        pytest.skip("default fixture not present")
    key = "Privette v. Superior Court, 5 Cal.4th 689, 695 (1993)"
    citations = [make_citation("c1", key)]
    results = fetch_sources(citations, True, None)
    assert len(results) == 1
    assert results[0].retrieval_status == RetrievalStatus.FOUND
    assert results[0].authority_text is not None


@pytest.mark.parametrize(
    "normalized,overrides,expected_status,expected_error,expected_text",
    [
        ("X (2020)", {"retrieval_status": "not_found", "error": "Not in DB"}, RetrievalStatus.NOT_FOUND, "Not in DB", None),
        ("Y (2021)", {"retrieval_status": "error", "error": "Network failed"}, RetrievalStatus.ERROR, "Network failed", None),
        ("Z (2022)", {"retrieval_status": "disabled"}, RetrievalStatus.DISABLED, None, None),
        ("W (2019)", {"retrieval_status": "invalid", "authority_text": "txt"}, RetrievalStatus.FOUND, None, "txt"),
        ("V (2018)", {"authority_text": "snippet"}, RetrievalStatus.FOUND, None, "snippet"),
    ],
)
def test_fetch_sources_override_status(make_citation, normalized, overrides, expected_status, expected_error, expected_text):
    citations = [make_citation("c1", normalized)]
    override_map = {normalized: overrides}
    results = fetch_sources(citations, True, override_map)
    assert len(results) == 1
    assert results[0].retrieval_status == expected_status
    assert results[0].error == expected_error
    assert results[0].authority_text == expected_text


def test_fetch_sources_multiple_citations_mixed_override_and_disabled(make_citation):
    key = "Privette v. Superior Court, 5 Cal.4th 689, 695 (1993)"
    citations = [
        make_citation("c1", key),
        make_citation("c2", "No Override (2020)"),
    ]
    overrides = {
        key: {"retrieval_status": "found", "authority_text": "Privette."},
    }
    results = fetch_sources(citations, False, overrides)
    assert len(results) == 2
    assert results[0].retrieval_status == RetrievalStatus.FOUND
    assert results[0].authority_text == "Privette."
    assert results[1].retrieval_status == RetrievalStatus.DISABLED
    assert results[1].authority_text is None
